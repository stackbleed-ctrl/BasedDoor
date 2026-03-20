#!/usr/bin/env bash
# BasedDoor — Install Ollama + pull required models
# Run once on your Home Assistant host or dedicated local AI server.
# Tested on Ubuntu 22.04/24.04 and Debian 12.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

OLLAMA_HOST="${OLLAMA_HOST:-0.0.0.0}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
LLM_MODEL="${LLM_MODEL:-llama3.2:3b}"
VISION_MODEL="${VISION_MODEL:-llava:7b}"
INSTALL_VISION="${INSTALL_VISION:-false}"

GREEN='\033[0;32m'
AMBER='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}BasedDoor — Ollama Installer${NC}"
echo "────────────────────────────────────────"

# ── Check / install Ollama ────────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
    echo -e "${GREEN}✓ Ollama already installed:${NC} $(ollama --version)"
else
    echo "Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo -e "${GREEN}✓ Ollama installed${NC}"
fi

# ── Start Ollama service ──────────────────────────────────────────────────────
if systemctl is-active --quiet ollama 2>/dev/null; then
    echo -e "${GREEN}✓ Ollama service already running${NC}"
else
    echo "Starting Ollama service..."
    if systemctl is-enabled --quiet ollama 2>/dev/null; then
        systemctl start ollama
    else
        # Run in background if systemd not available (e.g. HA OS addon)
        OLLAMA_HOST="${OLLAMA_HOST}" ollama serve &
        sleep 3
    fi
fi

# ── Pull LLM model ────────────────────────────────────────────────────────────
echo ""
echo "Pulling LLM model: ${LLM_MODEL}"
echo -e "${AMBER}This may take a few minutes on first run...${NC}"
ollama pull "${LLM_MODEL}"
echo -e "${GREEN}✓ ${LLM_MODEL} ready${NC}"

# ── Pull Vision model (optional) ─────────────────────────────────────────────
if [[ "${INSTALL_VISION}" == "true" ]]; then
    echo ""
    echo "Pulling vision model: ${VISION_MODEL}"
    echo -e "${AMBER}LLaVA 7b is ~4.7GB — grab a coffee...${NC}"
    ollama pull "${VISION_MODEL}"
    echo -e "${GREEN}✓ ${VISION_MODEL} ready${NC}"
else
    echo ""
    echo -e "${AMBER}Vision model skipped. To install LLaVA:${NC}"
    echo "  INSTALL_VISION=true bash scripts/install_ollama.sh"
    echo "  OR: ollama pull ${VISION_MODEL}"
fi

# ── Verify endpoint ───────────────────────────────────────────────────────────
echo ""
echo "Verifying Ollama API endpoint..."
if curl -sf "http://localhost:${OLLAMA_PORT}/api/tags" > /dev/null; then
    echo -e "${GREEN}✓ Ollama API responding on port ${OLLAMA_PORT}${NC}"
else
    echo -e "${RED}✗ Ollama API not responding — check logs: journalctl -u ollama${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}────────────────────────────────────────${NC}"
echo -e "${GREEN}Ollama setup complete.${NC}"
echo "Endpoint: http://localhost:${OLLAMA_PORT}"
echo "LLM model: ${LLM_MODEL}"
[[ "${INSTALL_VISION}" == "true" ]] && echo "Vision model: ${VISION_MODEL}"
echo ""
echo "Add this to your BasedDoor config:"
echo "  ollama_endpoint: http://localhost:${OLLAMA_PORT}"
echo "  ollama_model: ${LLM_MODEL}"
