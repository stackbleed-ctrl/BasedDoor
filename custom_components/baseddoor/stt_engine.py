"""BasedDoor — STT Engine (Whisper)."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

_LOGGER = logging.getLogger(__name__)

STT_TIMEOUT = 30.0


class WhisperSTTEngine:
    """
    Sends audio bytes to a Whisper STT HTTP server and returns a transcript.

    Compatible with:
      - faster-whisper-server  (https://github.com/fedirz/faster-whisper-server)
      - whisper.cpp server     (https://github.com/ggerganov/whisper.cpp)
      - Wyoming Whisper HA add-on
      - OpenAI-compatible /v1/audio/transcriptions endpoint (local only)

    All three accept multipart/form-data with an "audio_file" or "file" field.
    BasedDoor tries the faster-whisper-server format first, then falls back to
    the OpenAI-compatible format.
    """

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint.rstrip("/")

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.wav") -> Optional[str]:
        """
        Transcribe audio_bytes (WAV/MP3/OGG).
        Returns transcript string or None on failure.
        """
        # Try faster-whisper-server style first
        result = await self._try_faster_whisper(audio_bytes, filename)
        if result:
            return result

        # Fall back to OpenAI-compatible endpoint
        result = await self._try_openai_compat(audio_bytes, filename)
        if result:
            return result

        _LOGGER.warning("BasedDoor STT: all transcription attempts failed")
        return None

    async def _try_faster_whisper(self, audio_bytes: bytes, filename: str) -> Optional[str]:
        """faster-whisper-server: POST /v1/audio/transcriptions."""
        try:
            async with httpx.AsyncClient(timeout=STT_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._endpoint}/v1/audio/transcriptions",
                    files={"file": (filename, audio_bytes, "audio/wav")},
                    data={"model": "Systran/faster-whisper-small"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("text", "").strip()
                    if text:
                        _LOGGER.debug("BasedDoor STT: transcript='%s'", text[:80])
                        return text
        except Exception:  # noqa: BLE001
            pass
        return None

    async def _try_openai_compat(self, audio_bytes: bytes, filename: str) -> Optional[str]:
        """OpenAI-compatible endpoint: POST /v1/audio/transcriptions."""
        try:
            async with httpx.AsyncClient(timeout=STT_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._endpoint}/v1/audio/transcriptions",
                    files={"file": (filename, audio_bytes, "audio/wav")},
                    data={"model": "whisper-1", "response_format": "json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("text", "").strip()
                    if text:
                        return text
        except Exception:  # noqa: BLE001
            pass
        return None
