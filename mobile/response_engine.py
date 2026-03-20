"""
BasedDoor Mobile — Response Engine
Handles LLM calls to home Ollama server OR plays offline pre-baked audio.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

_LOGGER = logging.getLogger(__name__)

# Offline fallback responses (plain text — displayed on screen + spoken by Piper if available)
OFFLINE_RESPONSES = {
    "polite_canadian": (
        "I am not in a position to answer questions. "
        "Recording is in progress. Have a safe day."
    ),
    "grok_based": (
        "No consent. No comment. Recording active. Have a safe day."
    ),
    "maximum_refusal": (
        "I am invoking my right to silence under Section 7 of the "
        "Canadian Charter of Rights and Freedoms. "
        "I have nothing to say. Recording is in progress."
    ),
}

AUDIO_DIR = Path(__file__).parent / "assets" / "responses"


class ResponseEngine:
    """Generate or retrieve a rights-assertion response for mobile use."""

    def __init__(self, config: dict) -> None:
        self._config = config

    def respond(self, mode: str = "polite_canadian", offline: bool = True) -> str:
        """
        Return response text and attempt to play audio.
        If offline=True or Ollama unreachable, use pre-baked response.
        """
        if offline:
            return self._offline_response(mode)

        try:
            import httpx

            text = self._ollama_response(mode)
            if text:
                self._speak(text)
                return text
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("BasedDoor Mobile: Ollama unavailable (%s), using offline", exc)

        return self._offline_response(mode)

    def _offline_response(self, mode: str) -> str:
        text = OFFLINE_RESPONSES.get(mode, OFFLINE_RESPONSES["polite_canadian"])
        audio_path = AUDIO_DIR / f"{mode}.wav"
        if audio_path.exists():
            self._play_wav(str(audio_path))
        else:
            self._speak(text)
        return text

    def _ollama_response(self, mode: str) -> Optional[str]:
        import httpx

        system = (
            "You are BasedDoor Mobile, a portable Charter rights assistant. "
            "Respond in 2 sentences maximum. Calm, firm, no fluff. "
            f"Mode: {mode}."
        )
        payload = {
            "model": self._config.get("ollama_model", "llama3.2:3b"),
            "system": system,
            "prompt": "Generate the spoken rights-assertion response now.",
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 80},
        }
        endpoint = self._config.get("ollama_endpoint", "http://localhost:11434")
        resp = httpx.post(f"{endpoint}/api/generate", json=payload, timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("response", "").strip() or None

    def _speak(self, text: str) -> None:
        """TTS via Piper endpoint or Android TTS fallback."""
        try:
            import httpx
            endpoint = self._config.get("piper_endpoint", "")
            if endpoint:
                resp = httpx.post(
                    f"{endpoint.rstrip('/')}/api/tts",
                    json={"text": text},
                    timeout=8.0,
                )
                if resp.status_code == 200:
                    tmp = "/tmp/baseddoor_mobile.wav"
                    with open(tmp, "wb") as f:
                        f.write(resp.content)
                    self._play_wav(tmp)
                    return
        except Exception:
            pass

        # Android TTS fallback via plyer
        try:
            from plyer import tts
            tts.speak(text)
        except Exception as exc:
            _LOGGER.warning("BasedDoor Mobile: TTS unavailable: %s", exc)

    @staticmethod
    def _play_wav(path: str) -> None:
        """Play a WAV file via pygame or plyer."""
        try:
            from pygame import mixer
            mixer.init()
            mixer.music.load(path)
            mixer.music.play()
        except Exception:
            try:
                import subprocess
                subprocess.Popen(["aplay", path])
            except Exception as exc:
                _LOGGER.warning("BasedDoor Mobile: audio playback failed: %s", exc)
