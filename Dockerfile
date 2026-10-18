FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.12 \
    curl=8.14.1-2+deb13u7 \
    libpq-dev=17.11-0+deb13u1 \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY ticket_platforms /app/ticket_platforms
COPY scripts/*.py /app/scripts/
COPY config/ /app/config/

# Create data dirs
RUN mkdir -p /app/data/logs /app/data/kb

EXPOSE 8080
CMD ["python", "-m", "uvicorn", "agent_server:app", "--host", "<ip-address>", "--port", "8080", "--workers", "2"]
