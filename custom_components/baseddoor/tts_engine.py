"""BasedDoor — TTS Engine (Piper)."""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

import httpx
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

TTS_TIMEOUT = 20.0


class PiperTTSEngine:
    """
    Sends text to a Piper TTS HTTP server and plays the resulting
    audio through a Home Assistant media_player entity.

    Compatible with:
      - piper-tts HTTP server (https://github.com/rhasspy/piper)
      - Wyoming Piper add-on (HA Add-on store)
      - Any endpoint that accepts POST /api/tts with JSON {"text": "..."} and
        returns audio/wav bytes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        piper_endpoint: str,
        speaker_entity: str,
    ) -> None:
        self._hass = hass
        self._endpoint = piper_endpoint.rstrip("/")
        self._speaker = speaker_entity

    async def speak(self, text: str) -> bool:
        """
        Convert text → WAV via Piper, save to /tmp, play via HA media_player.
        Returns True on success.
        """
        audio_bytes = await self._synthesise(text)
        if not audio_bytes:
            return False
        return await self._play(audio_bytes, text)

    async def _synthesise(self, text: str) -> Optional[bytes]:
        """POST to Piper TTS endpoint, return WAV bytes."""
        try:
            async with httpx.AsyncClient(timeout=TTS_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._endpoint}/api/tts",
                    json={"text": text},
                    headers={"Accept": "audio/wav"},
                )
                resp.raise_for_status()
                _LOGGER.debug(
                    "BasedDoor TTS: synthesised %d bytes for '%s...'",
                    len(resp.content),
                    text[:40],
                )
                return resp.content
        except httpx.TimeoutException:
            _LOGGER.error("BasedDoor TTS: Piper timed out")
        except httpx.HTTPStatusError as exc:
            _LOGGER.error("BasedDoor TTS: HTTP %s from Piper", exc.response.status_code)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor TTS: unexpected error: %s", exc)
        return None

    async def _play(self, audio_bytes: bytes, original_text: str) -> bool:
        """
        Write WAV to a temp file in /config/www (HA static web serving) and
        call media_player.play_media.  Falls back to HA built-in TTS if needed.
        """
        try:
            # Write to HA's www folder so the internal URL works
            www_dir = self._hass.config.path("www", "baseddoor")
            os.makedirs(www_dir, exist_ok=True)

            tmp_path = os.path.join(www_dir, "response.wav")
            with open(tmp_path, "wb") as fh:
                fh.write(audio_bytes)

            media_url = "/local/baseddoor/response.wav"

            await self._hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": self._speaker,
                    "media_content_id": media_url,
                    "media_content_type": "music",
                },
                blocking=False,
            )
            _LOGGER.info("BasedDoor TTS: playing via %s", self._speaker)
            return True

        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor TTS: playback error: %s", exc)
            # Last resort — use HA's built-in TTS
            await self._fallback_tts(original_text)
            return False

    async def _fallback_tts(self, text: str) -> None:
        """Use HA's native TTS as emergency fallback."""
        try:
            await self._hass.services.async_call(
                "tts",
                "speak",
                {
                    "entity_id": self._speaker,
                    "message": text,
                    "cache": False,
                },
                blocking=False,
            )
            _LOGGER.info("BasedDoor TTS: used HA built-in TTS fallback")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor TTS: HA fallback TTS also failed: %s", exc)
