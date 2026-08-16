"""BasedDoor Mobile response engine.

Offline deterministic output is the baseline. No cloud STT fallback is used.
"""
from __future__ import annotations

import logging
from typing import Optional

_LOGGER = logging.getLogger(__name__)

OFFLINE_RESPONSES = {
    "polite_canadian": (
        "Thank you for visiting. I am an automated assistant and cannot answer "
        "questions or provide access on behalf of the resident. Please leave any "
        "lawful notice or contact information."
    ),
    "grok_based": (
        "Automated assistant. No consent is being provided for entry or search. "
        "Please leave any lawful notice or contact information."
    ),
    "maximum_refusal": (
        "This automated system is not providing consent for entry, search, or "
        "questioning. If you are acting under lawful authority, follow that "
        "authority and provide any document or notice required by law."
    ),
}


class ResponseEngine:
    def __init__(self, config: dict) -> None:
        self._config = config

    def respond(self, mode: str = "polite_canadian", offline: bool = True) -> str:
        if offline or not self._config.get("ollama_endpoint"):
            text = self._offline_response(mode)
            self._speak(text)
            return text

        try:
            text = self._ollama_response(mode)
            if text:
                forbidden = (
                    "recording active", "being recorded", "recording is in progress",
                    "this is being recorded",
                )
                if any(x in text.lower() for x in forbidden):
                    text = self._offline_response(mode)
                self._speak(text)
                return text
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Local Ollama unavailable: %s", exc)

        text = self._offline_response(mode)
        self._speak(text)
        return text

    def _offline_response(self, mode: str) -> str:
        return OFFLINE_RESPONSES.get(mode, OFFLINE_RESPONSES["polite_canadian"])

    def _ollama_response(self, mode: str) -> Optional[str]:
        import httpx
        endpoint = self._config.get("ollama_endpoint", "").rstrip("/")
        payload = {
            "model": self._config.get("ollama_model", "llama3.2:3b"),
            "system": (
                "You are a local automated doorstep assistant. Never claim recording "
                "is active. Never claim legal authority is invalid. Never disclose "
                "resident presence. Maximum two calm sentences."
            ),
            "prompt": f"Generate the configured response. Mode: {mode}.",
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 80},
        }
        resp = httpx.post(f"{endpoint}/api/generate", json=payload, timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("response", "").strip() or None

    @staticmethod
    def _speak(text: str) -> None:
        try:
            from plyer import tts
            tts.speak(text)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.info("Device TTS unavailable; showing text only: %s", exc)
