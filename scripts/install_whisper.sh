#!/usr/bin/env bash
# BasedDoor — Install faster-whisper-server for local STT
# https://github.com/fedirz/faster-whisper-server
# Tested on Ubuntu 22.04/24.04 with Python 3.10+
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

WHISPER_PORT="${WHISPER_PORT:-9000}"
WHISPER_MODEL="${WHISPER_MODEL:-Systran/faster-whisper-small}"

GREEN='\033[0;32m'
AMBER='\033[0;33m'
NC='\033[0m'

echo -e "${GREEN}BasedDoor — Whisper STT Installer${NC}"
echo "────────────────────────────────────────"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "Python3 required. Install it first."
    exit 1
fi

# Install faster-whisper-server via pip
echo "Installing faster-whisper-server..."
pip3 install faster-whisper-server --break-system-packages 2>/dev/null \
    || pip3 install faster-whisper-server

echo -e "${GREEN}✓ faster-whisper-server installed${NC}"

# ── Systemd service ───────────────────────────────────────────────────────────
if command -v systemctl &>/dev/null; then
    cat > /etc/systemd/system/baseddoor-whisper.service << SVCEOF
[Unit]
Description=BasedDoor Whisper STT Server
After=network.target

[Service]
Type=simple
Environment="WHISPER_MODEL=${WHISPER_MODEL}"
ExecStart=/usr/bin/python3 -m faster_whisper_server.main --host 0.0.0.0 --port ${WHISPER_PORT}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable --now baseddoor-whisper
    echo -e "${GREEN}✓ Whisper service enabled and started${NC}"
    echo -e "${AMBER}Note: first start downloads the model (~140MB for small)${NC}"
else
    echo -e "${AMBER}systemd not available — start manually:${NC}"
    echo "  python3 -m faster_whisper_server.main --host 0.0.0.0 --port ${WHISPER_PORT} &"
fi

echo ""
echo -e "${GREEN}────────────────────────────────────────${NC}"
echo -e "${GREEN}Whisper STT setup complete.${NC}"
echo "Endpoint: http://localhost:${WHISPER_PORT}"
echo "Model:    ${WHISPER_MODEL}"
