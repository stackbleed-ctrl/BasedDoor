#!/usr/bin/env bash
# BasedDoor — Install Piper TTS + start HTTP server
# Tested on Ubuntu 22.04/24.04 and Debian 12.
# Piper project: https://github.com/rhasspy/piper
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PIPER_PORT="${PIPER_PORT:-5000}"
PIPER_VOICE="${PIPER_VOICE:-en_CA-alba-medium}"  # Canadian English female voice
INSTALL_DIR="${INSTALL_DIR:-/opt/piper}"

GREEN='\033[0;32m'
AMBER='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}BasedDoor — Piper TTS Installer${NC}"
echo "────────────────────────────────────────"

ARCH=$(uname -m)
case "${ARCH}" in
    x86_64)  PIPER_ARCH="amd64" ;;
    aarch64) PIPER_ARCH="arm64" ;;
    armv7l)  PIPER_ARCH="armv7" ;;
    *)
        echo -e "${RED}Unsupported architecture: ${ARCH}${NC}"
        exit 1
        ;;
esac

PIPER_VERSION="2023.11.14-2"
PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_${PIPER_ARCH}.tar.gz"

mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

if [[ ! -f "${INSTALL_DIR}/piper" ]]; then
    echo "Downloading Piper ${PIPER_VERSION} for ${PIPER_ARCH}..."
    curl -fsSL "${PIPER_URL}" | tar xz --strip-components=1
    echo -e "${GREEN}✓ Piper binary installed to ${INSTALL_DIR}${NC}"
else
    echo -e "${GREEN}✓ Piper already installed${NC}"
fi

# ── Download voice model ──────────────────────────────────────────────────────
VOICES_DIR="${INSTALL_DIR}/voices"
mkdir -p "${VOICES_DIR}"
VOICE_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main"

if [[ ! -f "${VOICES_DIR}/${PIPER_VOICE}.onnx" ]]; then
    echo "Downloading voice: ${PIPER_VOICE}..."
    LANG_PREFIX=$(echo "${PIPER_VOICE}" | cut -d'-' -f1)
    curl -fsSL -o "${VOICES_DIR}/${PIPER_VOICE}.onnx"      "${VOICE_BASE}/${LANG_PREFIX}/${PIPER_VOICE}.onnx"
    curl -fsSL -o "${VOICES_DIR}/${PIPER_VOICE}.onnx.json" "${VOICE_BASE}/${LANG_PREFIX}/${PIPER_VOICE}.onnx.json"
    echo -e "${GREEN}✓ Voice '${PIPER_VOICE}' downloaded${NC}"
else
    echo -e "${GREEN}✓ Voice '${PIPER_VOICE}' already present${NC}"
fi

# ── Create simple HTTP wrapper ────────────────────────────────────────────────
cat > "${INSTALL_DIR}/piper_server.py" << PYEOF
#!/usr/bin/env python3
"""
Minimal Piper TTS HTTP server.
POST /api/tts {"text": "..."} -> audio/wav bytes
GET  /health                  -> {"status": "ok"}
"""
import json
import subprocess
import tempfile
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

PIPER_BIN   = "${INSTALL_DIR}/piper"
VOICE_MODEL = "${VOICES_DIR}/${PIPER_VOICE}.onnx"
PORT        = ${PIPER_PORT}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress request logging

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, b'{"status":"ok"}', "application/json")
        else:
            self._respond(404, b"Not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/tts":
            self._respond(404, b"Not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length))
        text   = body.get("text", "").strip()
        if not text:
            self._respond(400, b"No text provided", "text/plain")
            return
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.run(
                [PIPER_BIN, "--model", VOICE_MODEL, "--output_file", tmp_path],
                input=text.encode(),
                check=True,
                capture_output=True,
            )
            with open(tmp_path, "rb") as f:
                wav_bytes = f.read()
            self._respond(200, wav_bytes, "audio/wav")
        finally:
            os.unlink(tmp_path)

    def _respond(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    print(f"Piper TTS server running on port {PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
PYEOF

chmod +x "${INSTALL_DIR}/piper_server.py"

# ── Systemd service ───────────────────────────────────────────────────────────
if command -v systemctl &>/dev/null; then
    cat > /etc/systemd/system/baseddoor-piper.service << SVCEOF
[Unit]
Description=BasedDoor Piper TTS Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/piper_server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable --now baseddoor-piper
    echo -e "${GREEN}✓ Piper service enabled and started${NC}"
else
    echo -e "${AMBER}systemd not available — start manually:${NC}"
    echo "  python3 ${INSTALL_DIR}/piper_server.py &"
fi

echo ""
echo -e "${GREEN}────────────────────────────────────────${NC}"
echo -e "${GREEN}Piper TTS setup complete.${NC}"
echo "Endpoint: http://localhost:${PIPER_PORT}/api/tts"
echo "Voice:    ${PIPER_VOICE}"
echo ""
echo "Test it:"
echo "  curl -s -X POST http://localhost:${PIPER_PORT}/api/tts \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"text\": \"No warrant. No consent. Recording active.\"}' \\"
echo "    --output /tmp/test.wav && aplay /tmp/test.wav"
