"""BasedDoor — Response Mode Helpers."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant

from .const import MODE_CLIP, MODE_MAX, MODE_BASED, MODE_POLITE

_LOGGER = logging.getLogger(__name__)

# Default clip directory — users drop their own WAV files here
DEFAULT_CLIP_DIR = "/config/baseddoor_clips"

# Time-of-day derivation
def get_time_of_day() -> str:
    hour = datetime.now(tz=timezone.utc).hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def mode_label(mode: str) -> str:
    """Human-readable mode label for notifications."""
    return {
        MODE_POLITE: "Polite Canadian",
        MODE_BASED:  "Grok-Based",
        MODE_MAX:    "Maximum Refusal",
        MODE_CLIP:   "User Clip",
    }.get(mode, mode)


def should_escalate_mode(current_mode: str, knock_count: int, is_likely_leo: bool) -> str:
    """
    Auto-escalate mode based on context.
    Rules:
      - Night + police + knock >= 2 → MAX
      - Police detected on any mode below MAX → at least BASED
      - 3+ knocks on POLITE → escalate to BASED
    Returns the (possibly escalated) mode string.
    """
    if is_likely_leo and current_mode == MODE_POLITE:
        _LOGGER.debug("BasedDoor Modes: escalating POLITE → BASED (officer detected)")
        return MODE_BASED

    if knock_count >= 3 and current_mode == MODE_POLITE:
        _LOGGER.debug("BasedDoor Modes: escalating POLITE → BASED (knock_count=%d)", knock_count)
        return MODE_BASED

    time_of_day = get_time_of_day()
    if time_of_day == "night" and is_likely_leo and current_mode != MODE_MAX:
        _LOGGER.debug("BasedDoor Modes: escalating → MAX (night + officer)")
        return MODE_MAX

    return current_mode


class ClipPlayer:
    """
    Plays a user-supplied audio clip through HA media_player.
    Falls back to a built-in WAV if no user clip is found.
    """

    BUILTIN_CLIP_NAME = "baseddoor_default.wav"

    def __init__(self, hass: HomeAssistant, speaker_entity: str, clip_dir: str = DEFAULT_CLIP_DIR) -> None:
        self._hass = hass
        self._speaker = speaker_entity
        self._clip_dir = clip_dir

    def _find_clip(self) -> str | None:
        """Return path to first WAV/MP3 in clip_dir, or None."""
        if not os.path.isdir(self._clip_dir):
            return None
        for fname in sorted(os.listdir(self._clip_dir)):
            if fname.lower().endswith((".wav", ".mp3", ".ogg")):
                return os.path.join(self._clip_dir, fname)
        return None

    async def play(self) -> bool:
        """Play user clip or log a warning if none found."""
        clip_path = self._find_clip()

        if not clip_path:
            _LOGGER.warning(
                "BasedDoor Clip: no clip found in %s. "
                "Drop a WAV/MP3 there to use USER_CLIP mode.",
                self._clip_dir,
            )
            return False

        # Serve from HA www if the clip is inside config/www
        if "/www/" in clip_path:
            relative = clip_path.split("/www/", 1)[1]
            media_url = f"/local/{relative}"
        else:
            # Copy to www/baseddoor/ so it's serveable
            www_dir = self._hass.config.path("www", "baseddoor")
            os.makedirs(www_dir, exist_ok=True)
            dest = os.path.join(www_dir, os.path.basename(clip_path))
            if not os.path.exists(dest):
                import shutil
                shutil.copy2(clip_path, dest)
            media_url = f"/local/baseddoor/{os.path.basename(clip_path)}"

        try:
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
            _LOGGER.info("BasedDoor Clip: playing '%s' via %s", os.path.basename(clip_path), self._speaker)
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor Clip: playback failed: %s", exc)
            return False
