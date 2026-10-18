#!/usr/bin/env python3
"""
WhatsApp Webhook Receiver + Intent Router
Handles incoming WhatsApp messages, routes to helpdesk agent,
and manages the human takeover flow.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("whatsapp-webhook")

# ═══════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════

HELPDESK_AGENT_URL = os.getenv("HELPDESK_AGENT_URL", "http://helpdesk-agent:8080")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
WHATSAPP_WEBHOOK_SECRET = os.getenv("WHATSAPP_WEBHOOK_SECRET", "change_me")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
ADMIN_PHONE_NUMBER = os.getenv("ADMIN_PHONE_NUMBER", "")  # Your personal WhatsApp number
RATE_LIMIT_PER_MINUTE = int(os.getenv("WHATSAPP_RATE_LIMIT_PER_MINUTE", "10"))

# ═══════════════════════════════════════════════════
# Intent Detection Patterns
# ═══════════════════════════════════════════════════

INTENT_PATTERNS = {
    "check_tickets": [
        "my ticket", "my tickets", "ticket status", "check ticket", "track ticket",
        "where is my ticket", "ticket #", "status of", "view tickets", "see tickets",
        "list tickets", "my issue", "my problem", "ticket progress",
    ],
    "talk_to_human": [
        "human", "agent", "person", "real person", "talk to someone",
        "speak to", "representative", "operator", "escalate", "manager",
        "don't want bot", "not helpful", "live chat", "live agent",
        "wait for someone", "can I talk", "I want help", "help please",
        "I need help", "urgent", "asap", "emergency",
    ],
    "create_ticket": [
        "create ticket", "new ticket", "open ticket", "report issue",
        "file complaint", "submit issue", "new problem", "new issue",
        "start ticket", "help with", "problem with", "issue with",
        "something broken", "not working", "broken", "bug", "error",
    ],
    "greeting": [
        "hi", "hello", "hey", "good morning", "good afternoon",
        "good evening", "howdy", "yo", "sup",
    ],
    "thanks": [
        "thanks", "thank you", "thx", "appreciate", "great", "awesome",
        "perfect", "ok", "okay", "cool",
    ],
}

# ═══════════════════════════════════════════════════
# Response Templates (WhatsApp formatted)
# ═══════════════════════════════════════════════════

RESPONSES = {
    "greeting": (
        "👋 Welcome to cmdesk Support!\n\n"
        "I can help you with:\n"
        "🎫 Check your existing tickets\n"
        "📝 Create a new ticket\n"
        "👤 Talk to a human agent\n\n"
        "What would you like to do? Just type your question!"
    ),
    "menu": (
        "📋 *How can I help you?*\n\n"
        "1️⃣ Check my tickets\n"
        "2️⃣ Create a new ticket\n"
        "3️⃣ Talk to a human\n\n"
        "Reply with a number or just describe your issue!"
    ),
    "ask_email": (
        "To check your tickets, I need your email address.\n"
        "Please reply with the email associated with your account 📧"
    ),
    "human_queue": (
        "⏳ *Connecting you to a human agent...*\n\n"
        "I've notified the team. Someone will be with you shortly.\n\n"
        "⏱️ Average wait time: ~5 minutes\n"
        "💬 Feel free to describe your issue while you wait."
    ),
    "human_takeover": (
        "🔄 *You're now chatting with a human agent.*\n\n"
        "The AI assistant has been paused. A support agent will take it from here."
    ),
    "ticket_created": (
        "✅ *Ticket Created Successfully!*\n\n"
        "📋 Ticket ID: `{ticket_id}`\n"
        "📧 You'll receive updates via email\n"
        "⏱️ Response time: ~4 hours\n\n"
        "Is there anything else I can help with?"
    ),
    "ticket_not_found": (
        "🔍 I couldn't find any tickets associated with `{identifier}`.\n\n"
        "Would you like to:\n"
        "1️⃣ Try a different email\n"
        "2️⃣ Create a new ticket\n"
        "3️⃣ Talk to a human agent"
    ),
    "ticket_list": (
        "🎫 *Your Tickets ({count} total):*\n\n"
        "{ticket_list}\n\n"
        "Reply with a ticket ID for more details, or:"
    ),
    "ticket_details": (
        "📋 *Ticket #{ticket_id}*\n\n"
        "📝 Subject: {subject}\n"
        "📊 Status: {status}\n"
        "⚡ Priority: {priority}\n"
        "📅 Created: {created_at}\n"
        "🔄 Updated: {updated_at}\n\n"
        "💬 Last reply:\n{last_reply}"
    ),
    "create_ticket_prompt": (
        "📝 *Let's create a new ticket!*\n\n"
        "Please describe your issue in detail. Include:\n"
        "• What happened?\n"
        "• When did it happen?\n"
        "• Any error messages?\n\n"
        "The more detail, the faster we can help! 🚀"
    ),
    "rate_limited": (
        "⚠️ You've sent too many messages.\n"
        "Please wait a minute before trying again."
    ),
    "goodbye": (
        "👋 Thanks for contacting cmdesk Support!\n\n"
        "If you need help again, just message us anytime.\n"
        "Have a great day! 🌟"
    ),
    "fallback": (
        "I'm not sure I understood that. Let me help you with one of these:\n\n"
        "1️⃣ Check my tickets\n"
        "2️⃣ Create a new ticket\n"
        "3️⃣ Talk to a human\n\n"
        "Or just describe your issue and I'll do my best to help!"
    ),
}

# ═══════════════════════════════════════════════════
# App
# ═══════════════════════════════════════════════════

app = FastAPI(title="WhatsApp Helpdesk Webhook", version="1.0.0")
redis_client: redis.Redis | None = None


@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info("WhatsApp webhook started")


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()


# ═══════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════

class WhatsAppMessage(BaseModel):
    from_: str = Field(..., alias="from")
    text: str
    timestamp: str
    message_id: str


class WebhookPayload(BaseModel):
    entry: list


# ═══════════════════════════════════════════════════
# Intent Detection
# ═══════════════════════════════════════════════════

def detect_intent(message: str, session_data: dict) -> str:
    """Detect user intent from message text."""
    text = message.lower().strip()

    # Check if we're waiting for a specific response
    if session_data.get("awaiting") == "email":
        # Try to extract email from message
        import re
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        if email_match:
            return "email_provided"
        return "ask_email"

    if session_data.get("awaiting") == "ticket_details":
        return "create_ticket_message"

    if session_data.get("awaiting") == "menu_selection":
        if text in ["1", "1️⃣", "ticket", "tickets", "check"]:
            return "check_tickets"
        if text in ["2", "2️⃣", "create", "new"]:
            return "create_ticket"
        if text in ["3", "3️⃣", "human", "person", "agent"]:
            return "talk_to_human"

    # Pattern matching
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if pattern in text:
                if intent == "greeting":
                    return "greeting"
                if intent == "thanks":
                    return "thanks"
                return intent

    # If user is in human queue, keep them there
    if session_data.get("in_human_queue"):
        return "human_queue_message"

    return "fallback"


# ═══════════════════════════════════════════════════
# Session Management
# ═══════════════════════════════════════════════════

async def get_session(phone_number: str) -> dict:
    """Get or create session for a WhatsApp user."""
    key = f"wa_session:{phone_number}"
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return {
        "phone": phone_number,
        "user_id": None,
        "awaiting": None,
        "in_human_queue": False,
        "messages_count": 0,
        "started_at": time.time(),
        "last_message": None,
    }


async def save_session(phone_number: str, session: dict):
    """Save session data."""
    key = f"wa_session:{phone_number}"
    session["last_message"] = time.time()
    await redis_client.setex(key, 7200, json.dumps(session))  # 2hr TTL


# ═══════════════════════════════════════════════════
# Rate Limiting
# ═══════════════════════════════════════════════════

async def check_rate_limit(phone_number: str) -> bool:
    """Check if user is rate limited."""
    key = f"wa_ratelimit:{phone_number}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 60)
    return count > RATE_LIMIT_PER_MINUTE


# ═══════════════════════════════════════════════════
# WhatsApp API Helpers
# ═══════════════════════════════════════════════════

async def send_whatsapp_message(phone_number: str, message: str):
    """Send a message via WhatsApp Business API."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning(f"WhatsApp credentials not set. Would send to {phone_number}: {message[:100]}")
        return

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message},
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.error(f"WhatsApp send failed: {resp.status_code} {resp.text[:200]}")
        else:
            logger.info(f"Message sent to {phone_number}")


async def send_whatsapp_buttons(phone_number: str, body: str, buttons: list):
    """Send interactive buttons via WhatsApp."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning(f"WhatsApp credentials not set. Would send buttons to {phone_number}")
        return

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": btn[0], "title": btn[1]}}
                    for btn in buttons
                ],
            },
        },
    }

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload, headers=headers)


# ═══════════════════════════════════════════════════
# Human Queue Management
# ═══════════════════════════════════════════════════

async def add_to_human_queue(phone_number: str, session: dict):
    """Add user to human agent queue and notify admin."""
    queue_key = "human_queue:pending"
    await redis_client.lpush(queue_key, json.dumps({
        "phone": phone_number,
        "user_id": session.get("user_id"),
        "started_at": time.time(),
        "message": session.get("last_customer_message", ""),
    }))
    # Keep queue for 1 hour
    await redis_client.expire(queue_key, 3600)

    # Notify admin
    if ADMIN_PHONE_NUMBER:
        await send_whatsapp_message(
            ADMIN_PHONE_NUMBER,
            f"🔔 *Human Support Request*\n\n"
            f"📱 Customer: {phone_number}\n"
            f"⏰ Waiting since: Just now\n\n"
            f"Reply to take over this conversation.",
        )
    logger.info(f"Added {phone_number} to human queue, notified admin")


async def check_human_queue(phone_number: str) -> dict:
    """Check user's position in human queue."""
    queue_key = "human_queue:pending"
    items = await redis_client.lrange(queue_key, 0, -1)
    for i, item in enumerate(items):
        data = json.loads(item)
        if data["phone"] == phone_number:
            return {"position": i + 1, "in_queue": True}
    return {"position": 0, "in_queue": False}


# ═══════════════════════════════════════════════════
# Webhook Endpoints
# ═══════════════════════════════════════════════════

@app.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = "",
    hub_challenge: int = 0,
    hub_verify_token: str = "",
):
    """WhatsApp webhook verification (GET)."""
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_WEBHOOK_SECRET:
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook/whatsapp")
async def receive_message(request: Request):
    """Handle incoming WhatsApp messages."""
    payload = await request.json()

    # Verify signature if provided
    signature = request.headers.get("X-Hub-Signature-256", "")
    if signature and WHATSAPP_WEBHOOK_SECRET != "change_me":
        body = await request.body()
        expected = "sha256=" + hmac.new(
            WHATSAPP_WEBHOOK_SECRET.encode(), body, hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse message
    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                messages = change.get("value", {}).get("messages", [])
                for msg in messages:
                    from_number = msg.get("from", "")
                    text = msg.get("text", {}).get("body", "")
                    _ = msg.get("msg_id", "")

                    if not from_number or not text:
                        continue

                    # Rate limit check
                    if await check_rate_limit(from_number):
                        await send_whatsapp_message(from_number, RESPONSES["rate_limited"])
                        continue

                    # Get session
                    session = await get_session(from_number)
                    session["messages_count"] += 1

                    # Detect intent
                    intent = detect_intent(text, session)

                    # Route based on intent
                    response = await route_intent(intent, from_number, text, session)

                    # Save session
                    await save_session(from_number, session)

                    # Send response
                    await send_whatsapp_message(from_number, response)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)

    return {"status": "ok"}


# ═══════════════════════════════════════════════════
# Intent Router
# ═══════════════════════════════════════════════════

async def route_intent(intent: str, phone: str, text: str, session: dict) -> str:
    """Route detected intent to appropriate handler."""

    if intent == "greeting":
        session["awaiting"] = "menu_selection"
        return RESPONSES["greeting"]

    if intent == "menu_selection" or intent in ["check_tickets", "create_ticket", "talk_to_human"]:
        if intent == "check_tickets" or intent == "1":
            session["awaiting"] = "email"
            return RESPONSES["ask_email"]

        if intent == "create_ticket" or intent == "2":
            session["awaiting"] = "ticket_details"
            return RESPONSES["create_ticket_prompt"]

        if intent == "talk_to_human" or intent == "3":
            session["in_human_queue"] = True
            session["awaiting"] = None
            session["last_customer_message"] = text
            await add_to_human_queue(phone, session)
            return RESPONSES["human_queue"]

    if intent == "email_provided":
        import re
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        if email_match:
            email = email_match.group()
            session["user_id"] = email
            session["awaiting"] = None
            # Search tickets for this email
            tickets = await search_tickets(email)
            if tickets:
                session["tickets"] = tickets
                return format_ticket_list(tickets)
            else:
                return RESPONSES["ticket_not_found"].format(identifier=email)

    if intent == "create_ticket_message":
        session["awaiting"] = None
        # Forward to helpdesk agent for ticket creation
        result = await forward_to_agent(
            user_id=session.get("user_id", phone),
            message=text,
            platform="whatsapp",
        )
        if result.get("ticket_id"):
            return RESPONSES["ticket_created"].format(**result)
        return "I've received your issue and will create a ticket shortly. You'll receive a confirmation via WhatsApp."

    if intent == "human_queue_message":
        queue_status = await check_human_queue(phone)
        if queue_status["in_queue"]:
            return f"⏳ You're #{queue_status['position']} in queue. An agent will be with you soon!"
        return "🔔 A human agent has been notified. You'll be connected shortly."

    if intent == "thanks":
        session["awaiting"] = None
        return RESPONSES["goodbye"]

    # Fallback: forward to helpdesk agent for general questions
    result = await forward_to_agent(
        user_id=session.get("user_id", phone),
        message=text,
        platform="whatsapp",
    )
    return result.get("response", RESPONSES["fallback"])


async def search_tickets(email: str) -> list:
    """Search tickets via helpdesk agent API."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{HELPDESK_AGENT_URL}/chat",
                json={
                    "user_id": email,
                    "message": f"Search my tickets for: {email}",
                    "platform": "whatsapp",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                # Parse ticket results from response
                return data.get("tickets", [])
    except Exception as e:
        logger.error(f"Error searching tickets: {e}")
    return []


async def forward_to_agent(user_id: str, message: str, platform: str) -> dict:
    """Forward message to helpdesk agent."""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{HELPDESK_AGENT_URL}/chat",
                json={
                    "user_id": user_id,
                    "message": message,
                    "platform": platform,
                },
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Error forwarding to agent: {e}")
    return {}


def format_ticket_list(tickets: list) -> str:
    """Format ticket list for WhatsApp."""
    if not tickets:
        return RESPONSES["ticket_not_found"].format(identifier="")

    lines = []
    for t in tickets[:5]:
        status_emoji = {"open": "🟢", "pending": "🟡", "closed": "✅"}.get(t.get("status", ""), "⚪")
        lines.append(f"{status_emoji} *{t.get('ticket_id', 'N/A')}* — {t.get('subject', 'No subject')}")

    ticket_list = "\n".join(lines)
    return RESPONSES["ticket_list"].format(count=len(tickets), ticket_list=ticket_list)


# ═══════════════════════════════════════════════════
# Admin Endpoints (for taking over conversations)
# ─────────────────────────────────────────────────────
# POST /admin/takeover/{phone}
#   - Pauses the bot for this user
#   - You (admin) take over the WhatsApp conversation
# POST /admin/resume/{phone}
#   - Re-enables the bot after manual intervention
# ═══════════════════════════════════════════════════

@app.post("/admin/takeover/{phone}")
async def admin_takeover(phone: str):
    """Admin takes over conversation with a customer."""
    session = await get_session(phone)
    session["in_human_queue"] = False
    session["awaiting"] = None
    session["taken_over"] = True
    await save_session(phone, session)

    # Notify customer
    await send_whatsapp_message(phone, RESPONSES["human_takeover"])

    # Remove from queue
    queue_key = "human_queue:pending"
    items = await redis_client.lrange(queue_key, 0, -1)
    for item in items:
        data = json.loads(item)
        if data["phone"] == phone:
            await redis_client.lrem(queue_key, 1, item)
            break

    return {"status": "taken_over", "phone": phone}


@app.post("/admin/resume/{phone}")
async def admin_resume(phone: str):
    """Re-enable bot after manual intervention."""
    session = await get_session(phone)
    session["taken_over"] = False
    session["awaiting"] = "menu_selection"
    await save_session(phone, session)

    await send_whatsapp_message(phone, "🤖 Bot re-enabled. How else can I help you?")
    return {"status": "resumed", "phone": phone}


@app.get("/admin/queue")
async def view_queue():
    """View human support queue."""
    queue_key = "human_queue:pending"
    items = await redis_client.lrange(queue_key, 0, -1)
    queue = []
    for item in items:
        data = json.loads(item)
        wait_minutes = int((time.time() - data.get("started_at", time.time())) / 60)
        queue.append({
            "phone": data["phone"],
            "waiting_minutes": wait_minutes,
            "message": data.get("message", "")[:100],
        })
    return {"queue": queue, "total": len(queue)}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "9090"))
    uvicorn.run(app, host="0.0.0.0", port=port)
