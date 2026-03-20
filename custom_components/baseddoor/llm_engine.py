"""BasedDoor — LLM Engine (Ollama)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

from .const import (
    MODE_BASED,
    MODE_MAX,
    MODE_POLITE,
    VISION_UNIFORMED,
)

_LOGGER = logging.getLogger(__name__)

# Timeout for LLM calls — llama3.2:3b should respond in <5s on modern hardware
LLM_TIMEOUT = 30.0

# ── Fallback responses (used when Ollama is unreachable) ─────────────────────
FALLBACKS = {
    MODE_POLITE: (
        "Thank you for visiting. No emergency is apparent on this property. "
        "No warrant has been presented. I am unable to facilitate entry, search, "
        "or discussion on behalf of the resident. "
        "This interaction is being recorded. Have a safe day."
    ),
    MODE_BASED: (
        "No warrant. No emergency. No consent. Recording active. Please leave."
    ),
    MODE_MAX: (
        "No emergency confirmed on this property. No warrant has been presented. "
        "Under Section 7 of the Canadian Charter of Rights and Freedoms, "
        "the resident has the right to remain silent. "
        "Under Section 8, no consent is given to search, enter, or seize anything "
        "on this property. This interaction is being recorded, timestamped, and retained. "
        "If you have a warrant, please hold it to the camera or contact legal counsel. "
        "Otherwise, please vacate the property immediately. Thank you."
    ),
}


@dataclass
class LLMContext:
    """All runtime context needed to build a BasedDoor prompt."""
    mode: str
    vision_result: str = "unidentified"
    visitor_speech: str = ""
    time_of_day: str = "daytime"
    knock_count: int = 1
    recording_active: bool = True
    extra: dict = field(default_factory=dict)

    @property
    def is_likely_leo(self) -> bool:
        """True if vision or speech suggests law enforcement."""
        leo_keywords = [
            "rcmp", "police", "officer", "warrant", "investigation",
            "constable", "detective", "enforcement", "badge",
        ]
        speech_lower = self.visitor_speech.lower()
        return (
            self.vision_result == VISION_UNIFORMED
            or any(kw in speech_lower for kw in leo_keywords)
        )

    @property
    def has_claimed_emergency(self) -> bool:
        emergency_keywords = [
            "emergency", "urgent", "fire", "hurt", "injured",
            "danger", "gas leak", "welfare", "welfare check",
        ]
        return any(kw in self.visitor_speech.lower() for kw in emergency_keywords)

    @property
    def claims_warrant(self) -> bool:
        return "warrant" in self.visitor_speech.lower()


# ── System prompt builder ────────────────────────────────────────────────────

_BASE_IDENTITY = """
You are BasedDoor, a polite, firm, and legally precise AI door sentinel for a
private Canadian residence. Your sole function is to respond to visitors in a
manner that fully asserts the resident's rights under the Canadian Charter of
Rights and Freedoms — specifically Section 7 (right to silence and security of
the person) and Section 8 (right against unreasonable search or seizure).

CORE RULES — never break these:
- Never consent to entry, search, discussion, or identification.
- Always state that the interaction is being recorded.
- Never lie. Never impersonate a human.
- Never argue, escalate, or make legal threats.
- Be calm, polite, and completely immovable.
- If asked whether you are an AI or automated system, confirm it honestly.
- Do not volunteer information about the resident's presence, location, or activities.
- Never say "the resident is not home." Never confirm or deny presence.
- Responses are SHORT — maximum 3 sentences unless reciting rights.
- Use clear, measured diction suitable for spoken TTS delivery.
- Do not answer visitor questions. Deflect everything back to the warrant/emergency threshold.
""".strip()

_MODE_INSTRUCTIONS = {
    MODE_POLITE: """
TONE MODE: Polite Canadian.
Be respectful, warm, and firm. Acknowledge the visitor professionally.
Charter references are implied, not recited verbatim.
Example: "Thank you for attending. No emergency is apparent and no warrant has been
presented. I'm unable to assist further. Recording is active. Have a safe day."
""".strip(),

    MODE_BASED: """
TONE MODE: Grok-Based.
Short. Direct. Zero fluff. No pleasantries beyond minimum civility.
Say exactly what is needed, nothing more.
Example: "No warrant. No emergency. No consent. Recording active. Please leave."
""".strip(),

    MODE_MAX: """
TONE MODE: Maximum Refusal.
Full Charter-citing, legally complete response.
Name Section 7 and Section 8 explicitly. State recording. Request warrant be shown
to camera. Name legal counsel contact as next step.
This mode is used when law enforcement is confirmed or visitor is persistent.
""".strip(),
}

_LEO_ADDENDUM = """
VISITOR TYPE: Law enforcement officer detected (vision or speech analysis).

Additional rules:
- If officer claims exigent circumstances or emergency: ask them to state the
  specific active threat on this property right now. Do not accept vague claims.
  Response: "Please describe the specific emergency occurring on this property
  at this moment. Recording is in progress."
  If no specific, active threat is articulated: "No verifiable exigent circumstances
  stated. No consent given. Please vacate immediately."
- If officer asks for a named individual: "I am not able to confirm or deny the
  presence of anyone on this property. If you have a warrant naming a specific
  individual, please present it to the camera."
- If officer presents or claims a warrant verbally: "Please hold the warrant
  document to the camera now. I cannot act on a verbal claim of warrant.
  Recording is in progress."
- If officer presents a court order or production order: "Please present the
  document to the camera. The resident will review it with legal counsel before
  any action is taken."
- If officer becomes aggressive or threatens arrest: "Noted. This is being
  recorded in full. The resident will not open the door or make any statement
  without legal counsel present."
""".strip()

_EMERGENCY_ADDENDUM = """
VISITOR SPEECH ANALYSIS: Visitor has invoked the word 'emergency'.

Instructions:
- Do not assume the claim is true.
- Ask the visitor to specify the nature of the emergency on THIS property, right now.
- If they describe a genuine active threat (fire, injury, imminent danger) on the property:
  acknowledge it and state you are contacting emergency services.
- If the claimed emergency is vague, off-property, or unverifiable:
  "No emergency on this property has been confirmed. Please call 9-1-1 if you require
  emergency assistance. Recording is active."
""".strip()

_WARRANT_ADDENDUM = """
VISITOR SPEECH ANALYSIS: Visitor has mentioned a warrant.

Instructions:
- Do not open the door based on a verbal claim.
- Request they hold the physical document to the camera.
- State that legal counsel will be contacted before any action is taken.
- Response must include: "Please hold the warrant to the camera."
""".strip()

_REPEAT_KNOCK_ADDENDUM = """
ESCALATION NOTE: This visitor has knocked or rung {knock_count} times.

Adjust tone to note the repeated contact. Mention that continued presence without
lawful authority is being documented. Remain calm but make clear that the threshold
for engagement has not changed.
""".strip()


def build_system_prompt(ctx: LLMContext) -> str:
    """Assemble the full system prompt from context."""
    parts = [_BASE_IDENTITY, ""]

    # Mode instruction
    mode_instr = _MODE_INSTRUCTIONS.get(ctx.mode, _MODE_INSTRUCTIONS[MODE_POLITE])
    parts.append(mode_instr)

    # Situational addenda
    if ctx.is_likely_leo:
        parts.append(_LEO_ADDENDUM)
    if ctx.has_claimed_emergency:
        parts.append(_EMERGENCY_ADDENDUM)
    if ctx.claims_warrant:
        parts.append(_WARRANT_ADDENDUM)
    if ctx.knock_count >= 3:
        parts.append(_REPEAT_KNOCK_ADDENDUM.format(knock_count=ctx.knock_count))

    return "\n\n".join(parts)


def build_user_message(ctx: LLMContext) -> str:
    """Build the user-turn message that triggers the response."""
    time_str = ctx.time_of_day
    vision_str = ctx.vision_result.replace("_", " ")
    rec_str = "active" if ctx.recording_active else "not active"

    lines = [
        f"Time: {time_str}",
        f"Vision analysis: {vision_str}",
        f"Recording: {rec_str}",
        f"Knock count: {ctx.knock_count}",
    ]
    if ctx.visitor_speech:
        lines.append(f'Visitor said: "{ctx.visitor_speech}"')
    else:
        lines.append("Visitor speech: none captured")

    lines.append("")
    lines.append("Generate the spoken door response now.")
    return "\n".join(lines)


# ── Ollama engine ────────────────────────────────────────────────────────────

class OllamaEngine:
    """Async wrapper around the Ollama /api/generate endpoint."""

    def __init__(self, endpoint: str, model: str) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model

    async def generate(self, system_prompt: str, user_message: str) -> Optional[str]:
        """Call Ollama; return response text or None on failure."""
        payload = {
            "model": self._model,
            "system": system_prompt,
            "prompt": user_message,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 150,
                "stop": ["\n\n", "---"],
            },
        }
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._endpoint}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response", "").strip()
                if not text:
                    _LOGGER.warning("BasedDoor LLM: empty response from Ollama")
                    return None
                return text
        except httpx.TimeoutException:
            _LOGGER.error("BasedDoor LLM: Ollama timed out after %.1fs", LLM_TIMEOUT)
        except httpx.HTTPStatusError as exc:
            _LOGGER.error("BasedDoor LLM: HTTP %s", exc.response.status_code)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor LLM: unexpected error: %s", exc)
        return None

    async def generate_response(self, ctx: LLMContext) -> str:
        """High-level call: build prompt, call Ollama, fall back gracefully."""
        system_prompt = build_system_prompt(ctx)
        user_message = build_user_message(ctx)

        _LOGGER.debug("BasedDoor LLM: system_prompt length=%d", len(system_prompt))

        result = await self.generate(system_prompt, user_message)

        if result:
            # Sanitise — strip any LLM preamble like "BasedDoor:" prefix
            for prefix in ("BasedDoor:", "Response:", "Door:"):
                if result.startswith(prefix):
                    result = result[len(prefix):].strip()
            return result

        # Graceful fallback — never stay silent
        _LOGGER.warning(
            "BasedDoor LLM: falling back to hardcoded response for mode '%s'", ctx.mode
        )
        return FALLBACKS.get(ctx.mode, FALLBACKS[MODE_POLITE])
