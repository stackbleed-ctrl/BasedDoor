"""BasedDoor — local response engine."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from .const import MODE_BASED, MODE_MAX, MODE_POLITE, VISION_UNIFORMED

_LOGGER = logging.getLogger(__name__)
LLM_TIMEOUT = 30.0

FALLBACKS = {
    MODE_POLITE: (
        "Thank you for visiting. I am an automated doorstep assistant and I am "
        "not able to answer questions or provide access on behalf of the resident. "
        "Please leave any lawful notice or contact information. Have a safe day."
    ),
    MODE_BASED: (
        "Automated doorstep assistant. No consent is being provided for entry or "
        "search. Please leave any lawful notice or contact information."
    ),
    MODE_MAX: (
        "This is an automated doorstep assistant. The resident is not providing "
        "consent for entry, search, or questioning through this system. If you are "
        "acting under lawful authority, follow the authority available to you and "
        "provide any document or notice required by law."
    ),
}


@dataclass
class LLMContext:
    mode: str
    vision_result: str = "unidentified"
    visitor_speech: str = ""
    time_of_day: str = "daytime"
    knock_count: int = 1
    recording_active: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def is_likely_leo(self) -> bool:
        keywords = (
            "rcmp", "police", "officer", "warrant", "investigation",
            "constable", "detective", "enforcement", "badge",
        )
        speech = self.visitor_speech.lower()
        return self.vision_result == VISION_UNIFORMED or any(k in speech for k in keywords)

    @property
    def has_claimed_emergency(self) -> bool:
        return any(
            k in self.visitor_speech.lower()
            for k in ("emergency", "fire", "injured", "danger", "gas leak", "welfare")
        )

    @property
    def claims_warrant(self) -> bool:
        return "warrant" in self.visitor_speech.lower()


_BASE_IDENTITY = """
You are BasedDoor, an automated local-first doorstep assistant for a Canadian
residence. You communicate the resident's configured response calmly and
truthfully. You are not a lawyer, police detector, emergency dispatcher, or
authority on whether a warrant is valid.

Rules:
- Never impersonate a human.
- Never claim recording is active unless runtime context explicitly confirms it.
- Never claim a visitor is a police officer based on computer vision.
- Never provide consent for entry, search, questioning, or disclosure.
- Never tell a visitor that lawful authority is invalid or instruct anyone to
  physically obstruct emergency or warrant execution.
- Never disclose whether the resident is home, their location, or activities.
- Prefer short, non-escalatory responses.
- If a legal document is presented, request that it be left/provided or shown
  clearly for capture; do not pronounce it valid or invalid.
""".strip()

_MODE_INSTRUCTIONS = {
    MODE_POLITE: "Tone: respectful, calm, brief, Canadian English.",
    MODE_BASED: "Tone: direct, calm, minimal words, no insults or provocation.",
    MODE_MAX: (
        "Tone: formal and firm. State only that no consent is provided through "
        "the automated system and that lawful documents may be provided for review."
    ),
}

_LEO_ADDENDUM = """
Context suggests the visitor may be law enforcement. Treat that as uncertain.
Do not announce that the system has identified police. If lawful authority or
an emergency is asserted, do not argue about whether that authority exists.
The system may state that it cannot assess legal authority and that no consent
is being provided through the automated assistant.
""".strip()

_WARRANT_ADDENDUM = """
A warrant or other legal document was mentioned. Ask for the document to be
shown clearly or provided as required by law. Do not state that compliance is
conditional on AI review and do not characterize the document as valid/invalid.
""".strip()


def deterministic_response(ctx: LLMContext) -> str:
    text = FALLBACKS.get(ctx.mode, FALLBACKS[MODE_POLITE])
    if ctx.recording_active:
        text += " Recording has been confirmed active."
    return text


def build_system_prompt(ctx: LLMContext) -> str:
    parts = [_BASE_IDENTITY, _MODE_INSTRUCTIONS.get(ctx.mode, _MODE_INSTRUCTIONS[MODE_POLITE])]
    if ctx.is_likely_leo:
        parts.append(_LEO_ADDENDUM)
    if ctx.claims_warrant:
        parts.append(_WARRANT_ADDENDUM)
    if ctx.has_claimed_emergency:
        parts.append(
            "An emergency was mentioned. Do not delay or obstruct emergency action. "
            "State that the automated assistant cannot assess emergency authority."
        )
    return "\n\n".join(parts)


def build_user_message(ctx: LLMContext) -> str:
    lines = [
        f"Time: {ctx.time_of_day}",
        f"Vision classification (unverified): {ctx.vision_result}",
        f"Recording confirmed: {'yes' if ctx.recording_active else 'no'}",
        f"Contact count: {ctx.knock_count}",
    ]
    if ctx.visitor_speech:
        lines.append(f"Visitor speech transcript (unverified): {ctx.visitor_speech}")
    lines.append("Generate the configured spoken response, maximum three sentences.")
    return "\n".join(lines)


class OllamaEngine:
    def __init__(self, endpoint: str, model: str) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model

    async def generate(self, system_prompt: str, user_message: str) -> Optional[str]:
        payload = {
            "model": self._model,
            "system": system_prompt,
            "prompt": user_message,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 120},
        }
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(f"{self._endpoint}/api/generate", json=payload)
                resp.raise_for_status()
                text = resp.json().get("response", "").strip()
                return text or None
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("BasedDoor LLM unavailable; deterministic fallback: %s", exc)
            return None

    async def generate_response(self, ctx: LLMContext) -> str:
        result = await self.generate(build_system_prompt(ctx), build_user_message(ctx))
        if not result:
            return deterministic_response(ctx)

        for prefix in ("BasedDoor:", "Response:", "Door:"):
            if result.startswith(prefix):
                result = result[len(prefix):].strip()

        if not ctx.recording_active:
            lowered = result.lower()
            recording_claims = (
                "recording active",
                "recording is active",
                "being recorded",
                "recording is in progress",
                "this is being recorded",
            )
            if any(claim in lowered for claim in recording_claims):
                _LOGGER.warning("LLM invented recording state; replacing with deterministic response")
                return deterministic_response(ctx)
        return result
