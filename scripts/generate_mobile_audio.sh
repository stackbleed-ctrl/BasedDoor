#!/usr/bin/env bash
# BasedDoor — Generate offline mobile audio responses using Piper TTS
# Run this once after installing Piper to create the pre-baked WAV files
# used by the mobile app's offline mode.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PIPER_ENDPOINT="${PIPER_ENDPOINT:-http://localhost:5000}"
OUTPUT_DIR="${OUTPUT_DIR:-$(dirname "$0")/../mobile/assets/responses}"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

mkdir -p "${OUTPUT_DIR}"

declare -A RESPONSES=(
    ["default"]="I am not answering questions. Recording in progress."
    ["detention_question"]="Am I being detained? If not, I am leaving. Recording in progress."
    ["search_request"]="I do not consent to any search. Recording in progress."
    ["identification_request"]="I am not required to identify myself in this situation. Recording in progress."
    ["arrest_situation"]="I am invoking my right to silence and my right to counsel. I have nothing further to say."
    ["traffic_stop"]="Here is my licence and registration as required by law. I have nothing further to say. Recording in progress."
    ["general_refusal"]="No consent. No comment. Recording active. Have a safe day."
    ["polite_canadian"]="I am not in a position to answer questions. Recording is in progress. Have a safe day."
    ["grok_based"]="No consent. No comment. Recording active. Have a safe day."
    ["maximum_refusal"]="I am invoking my right to silence under Section 7 of the Canadian Charter of Rights and Freedoms. I have nothing to say. Recording is in progress."
)

echo -e "${GREEN}BasedDoor — Generating mobile offline audio${NC}"
echo "Output: ${OUTPUT_DIR}"
echo "Piper:  ${PIPER_ENDPOINT}"
echo "────────────────────────────────────────"

# Check Piper is up
if ! curl -sf "${PIPER_ENDPOINT}/health" > /dev/null; then
    echo -e "${RED}✗ Piper not reachable at ${PIPER_ENDPOINT}${NC}"
    echo "  Start Piper first: bash scripts/install_piper.sh"
    exit 1
fi

for KEY in "${!RESPONSES[@]}"; do
    TEXT="${RESPONSES[$KEY]}"
    OUT="${OUTPUT_DIR}/${KEY}.wav"
    echo -n "  Generating ${KEY}.wav ... "
    HTTP_CODE=$(curl -s -o "${OUT}" -w "%{http_code}" \
        -X POST "${PIPER_ENDPOINT}/api/tts" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"${TEXT}\"}")
    if [[ "${HTTP_CODE}" == "200" ]]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ HTTP ${HTTP_CODE}${NC}"
    fi
done

echo ""
echo -e "${GREEN}────────────────────────────────────────${NC}"
echo -e "${GREEN}Mobile audio generation complete.${NC}"
echo "Files written to: ${OUTPUT_DIR}"
