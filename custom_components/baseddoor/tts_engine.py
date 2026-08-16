"""BasedDoor — optional local TTS engine."""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
TTS_TIMEOUT = 20.0


class PiperTTSEngine:
    def __init__(self, hass: HomeAssistant, piper_endpoint: str, speaker_entity: str) -> None:
        self._hass = hass
        self._endpoint = (piper_endpoint or "").rstrip("/")
        self._speaker = speaker_entity or ""

    @property
    def configured(self) -> bool:
        return bool(self._speaker and self._endpoint)

    async def speak(self, text: str) -> bool:
        if not self.configured:
            _LOGGER.info("BasedDoor TTS skipped: no compatible speaker/TTS endpoint configured")
            return False
        audio = await self._synthesise(text)
        if not audio:
            return False
        return await self._play(audio)

    async def _synthesise(self, text: str) -> Optional[bytes]:
        try:
            async with httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._endpoint}/api/tts",
                    json={"text": text},
                    headers={"Accept": "audio/wav"},
                )
                resp.raise_for_status()
                return resp.content
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("BasedDoor Piper unavailable: %s", exc)
            return None

    async def _play(self, audio_bytes: bytes) -> bool:
        try:
            www_dir = self._hass.config.path("www", "baseddoor")
            os.makedirs(www_dir, exist_ok=True)
            path = os.path.join(www_dir, "response.wav")
            with open(path, "wb") as fh:
                fh.write(audio_bytes)

            await self._hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": self._speaker,
                    "media_content_id": "/local/baseddoor/response.wav",
                    "media_content_type": "audio/wav",
                },
                blocking=False,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("BasedDoor speaker playback failed: %s", exc)
            return False
