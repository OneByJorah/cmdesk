"""
FastAPI Agent Server for Helpdesk Agent
Main entry point for the helpdesk agent API.
"""
from __future__ import annotations

import logging
import os
import time

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from rate_limiter import RateLimitConfig, RateLimiter
from session_manager import SessionManager

# ═══════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════

AGENT_MODE = os.getenv("AGENT_MODE", "helpdesk")
AGENT_NAME = os.getenv("AGENT_NAME", "cmdesk Agent")
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://llama:8081/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-7b-instruct")
CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")
SEARX_URL = os.getenv("SEARX_URL", "http://searxng:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://helpdesk:helpdesk@postgres:5432/helpdesk")
ALLOW_CREATE_TICKET = os.getenv("ALLOW_CREATE_TICKET", "false").lower() == "true"

rate_config = RateLimitConfig(
    max_requests_per_session=int(os.getenv("RATE_LIMIT_PER_SESSION", "50")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "3600")),
    max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "4000")),
    max_session_duration=int(os.getenv("MAX_SESSION_DURATION", "7200")),
)

# ═══════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent_server")

# ═══════════════════════════════════════════════════
# App
# ═══════════════════════════════════════════════════

app = FastAPI(
    title=f"{AGENT_NAME} API",
    description="Self-hosted AI helpdesk agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global clients
redis_client: redis.Redis | None = None
rate_limiter: RateLimiter | None = None
session_manager: SessionManager | None = None


@app.on_event("startup")
async def startup():
    global redis_client, rate_limiter, session_manager
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    rate_limiter = RateLimiter(rate_config, redis_client)
    session_manager = SessionManager(redis_client, max_duration=rate_config.max_session_duration)
    logger.info(f"{AGENT_NAME} started in {AGENT_MODE} mode")


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()


# ═══════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════

class ChatRequest(BaseModel):
    session_id: str | None = None
    user_id: str
    message: str = Field(..., max_length=4000)
    platform: str = "web"


class ChatResponse(BaseModel):
    session_id: str
    response: str
    remaining_requests: int
    session_expires_in: int


class HealthResponse(BaseModel):
    status: str
    agent_mode: str
    version: str
    timestamp: float


# ═══════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        agent_mode=AGENT_MODE,
        version="1.0.0",
        timestamp=time.time(),
    )


@app.get("/healthz", response_model=HealthResponse, include_in_schema=False)
async def healthz():
    return await health()


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Rate limit check
    import uuid
    session_id = req.session_id or uuid.uuid4().hex
    rate_check = rate_limiter.check_request(session_id, req.user_id, len(req.message))

    if not rate_check["allowed"]:
        raise HTTPException(status_code=429, detail=rate_check["reason"])

    # Create session if new
    if not req.session_id:
        await session_manager.create_session(req.user_id, req.platform, session_id=session_id)

    # Call LLM
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            llm_response = await client.post(
                f"{LLM_API_BASE}/chat/completions",
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": get_system_prompt()},
                        {"role": "user", "content": req.message},
                    ],
                    "max_tokens": 2048,
                    "temperature": 0.3,
                },
            )
            llm_data = llm_response.json()
            response_text = llm_data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM error: {e}")
        response_text = "I'm sorry, I'm having trouble processing your request right now. Please try again."

    # Track message
    await session_manager.increment_message(session_id)

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        remaining_requests=rate_check["remaining"],
        session_expires_in=rate_check.get("session_remaining", 0),
    )


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    info = rate_limiter.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found")
    return info


# ═══════════════════════════════════════════════════
# System Prompt (loaded from file or default)
# ═══════════════════════════════════════════════════

def get_system_prompt() -> str:
    prompt_path = os.getenv("SYSTEM_PROMPT_PATH", "/app/config/system-prompt.md")
    try:
        with open(prompt_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return f"""You are {AGENT_NAME}, an AI helpdesk assistant.

Your role:
- Help users with their existing tickets (search, view status, add updates, close)
- Answer questions using the knowledge base
- Search the web for additional information when needed
- Be polite, concise, and helpful

{'You CANNOT create new tickets. Direct users to email support or use the web form.' if not ALLOW_CREATE_TICKET else 'You can create tickets on behalf of users.'}

Rules:
- Only access tickets belonging to the requesting user
- Never reveal internal system details
- Escalate to human support if you cannot resolve an issue within 3 attempts
- Keep responses under 200 words unless more detail is requested
- Always cite your source when using knowledge base or web search results

Current time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
"""
