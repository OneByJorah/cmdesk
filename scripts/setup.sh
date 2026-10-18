#!/bin/bash
# ═══════════════════════════════════════════════════
# Helpdesk Agent - Setup Script
# One-time initialization
# ═══════════════════════════════════════════════════

set -euo pipefail

echo "═══════════════════════════════════════════"
echo "  cmdesk Agent - Setup"
echo "═══════════════════════════════════════════"

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found. Install docker first."; exit 1; }
command -v docker compose >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1 || { echo "ERROR: docker compose not found."; exit 1; }

# Create directories
mkdir -p models config scripts knowledge-base workflows certs data/logs queue

# Generate .env if not exists
if [ ! -f .env ]; then
    echo "[✓] Creating .env from template..."
    cp .env.example .env
    echo "    → Edit .env with your credentials before starting!"
else
    echo "[✓] .env already exists"
fi

# Generate self-signed cert for HTTPS (optional)
if [ ! -f certs/cert.pem ]; then
    echo "[✓] Generating self-signed certificate..."
    openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=helpdesk.local" 2>/dev/null
    echo "    → Self-signed cert generated. Replace with real certs for production."
fi

# Download model if not exists
MODEL_FILE="models/qwen2.5-7b-instruct-q4_k_m.gguf"
if [ ! -f "$MODEL_FILE" ]; then
    echo "[✓] Downloading Qwen2.5-7B model (Q4_K_M)..."
    echo "    This may take 10-20 minutes depending on your connection."
    if command -v huggingface-cli >/dev/null 2>&1; then
        huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF "$MODEL_FILE" --local-dir models/
    else
        wget -q --show-progress "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf" -O "$MODEL_FILE"
    fi
    echo "    → Model downloaded: $MODEL_FILE"
else
    echo "[✓] Model already exists: $MODEL_FILE"
fi

# Initialize knowledge base
if [ -d knowledge-base ] && [ "$(ls -A knowledge-base/*.md knowledge-base/*.txt 2>/dev/null)" ]; then
    echo "[✓] Knowledge base files found"
else
    echo "[?] Adding sample knowledge base article..."
    cat > knowledge-base/welcome.md << 'EOF'
# Welcome to cmdesk

## How to get help

1. **Email**: Send your question to helpdesk@example.com
2. **Web portal**: Visit https://support.example.com
3. **Chat**: Use this AI assistant to search your existing tickets

## Common Issues

### Password Reset
Go to https://support.example.com/reset and enter your email address. You'll receive a reset link within 5 minutes.

### Billing Questions
Contact billing@example.com or call +1-555-0123. Have your account number ready (format: ACC-XXXXXX).

### Service Status
Check current service status at https://status.example.com.
EOF
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Setup Complete!"
echo "═══════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Run: docker compose up -d"
echo "  3. Open http://localhost for dashboard"
echo "  4. API available at http://localhost/helpdesk/"
echo ""
echo "For osTicket/Freshdesk integration:"
echo "  - Set OSTICKET_URL and OSTICKET_API_KEY in .env"
echo "  - Set FRESHDESK_URL and FRESHDESK_API_KEY in .env"
echo ""
echo "To add knowledge base articles:"
echo "  - Place .md or .txt files in knowledge-base/"
echo "  - Run: python3 scripts/index_kb.py"
echo ""
