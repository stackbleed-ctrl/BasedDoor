"""BasedDoor — Main Pipeline Coordinator."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_CAMERA_ENTITY,
    CONF_ENABLE_VISION,
    CONF_ENCRYPT_LOGS,
    CONF_ENCRYPTION_KEY,
    CONF_LLAVA_MODEL,
    CONF_LOG_DIR,
    CONF_MODE,
    CONF_NOTIFY_TARGET,
    CONF_OLLAMA_ENDPOINT,
    CONF_OLLAMA_MODEL,
    CONF_PIPER_ENDPOINT,
    CONF_SPEAKER_ENTITY,
    CONF_WHISPER_ENDPOINT,
    COORDINATOR_UPDATE_INTERVAL,
    DEFAULT_LOG_DIR,
    DEFAULT_MODE,
    DOMAIN,
    EVENT_LOG_WRITTEN,
    EVENT_RESPONSE_SPOKEN,
    EVENT_VISITOR_DETECTED,
    MODE_CLIP,
)
from .llm_engine import LLMContext, OllamaEngine
from .logger import InteractionLogger
from .modes import ClipPlayer, get_time_of_day, mode_label, should_escalate_mode
from .tts_engine import PiperTTSEngine
from .vision import VisionEngine
from .warrant_scanner import WarrantScanner

_LOGGER = logging.getLogger(__name__)


class BasedDoorCoordinator(DataUpdateCoordinator):
    """
    Orchestrates the full BasedDoor pipeline:
      Trigger → [Vision] → [STT] → LLM → TTS → Log → Notify
    """

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=COORDINATOR_UPDATE_INTERVAL),
        )
        self._config = config
        self._knock_count: dict[str, int] = {}  # keyed by trigger_source
        self._active = False  # debounce flag

        # Instantiate engines
        self.llm = OllamaEngine(
            endpoint=config.get(CONF_OLLAMA_ENDPOINT, "http://localhost:11434"),
            model=config.get(CONF_OLLAMA_MODEL, "llama3.2:3b"),
        )
        self.tts = PiperTTSEngine(
            hass=hass,
            piper_endpoint=config.get(CONF_PIPER_ENDPOINT, "http://localhost:5000"),
            speaker_entity=config.get(CONF_SPEAKER_ENTITY, ""),
        )
        self.vision: Optional[VisionEngine] = None
        if config.get(CONF_ENABLE_VISION):
            self.vision = VisionEngine(
                endpoint=config.get(CONF_OLLAMA_ENDPOINT, "http://localhost:11434"),
                model=config.get(CONF_LLAVA_MODEL, "llava:7b"),
            )

        self.log = InteractionLogger(
            log_dir=config.get(CONF_LOG_DIR, DEFAULT_LOG_DIR),
            encrypt=config.get(CONF_ENCRYPT_LOGS, True),
            key=config.get(CONF_ENCRYPTION_KEY),
        )

        self.clip_player = ClipPlayer(
            hass=hass,
            speaker_entity=config.get(CONF_SPEAKER_ENTITY, ""),
        )

    # ── HA DataUpdateCoordinator heartbeat ───────────────────────────────────

    async def _async_update_data(self) -> dict:
        """Heartbeat — returns coordinator status for diagnostics."""
        return {
            "active": self._active,
            "knock_counts": dict(self._knock_count),
        }

    # ── Main public entry point ───────────────────────────────────────────────

    async def handle_trigger(
        self,
        trigger_source: str = "unknown",
        camera_entity: Optional[str] = None,
        mode_override: Optional[str] = None,
    ) -> None:
        """
        Full pipeline entry point. Called by automations or the service handler.
        Non-blocking — runs the pipeline in the background.
        """
        if self._active:
            _LOGGER.debug("BasedDoor: trigger ignored — pipeline already active")
            return

        # Increment knock counter for this source
        self._knock_count[trigger_source] = self._knock_count.get(trigger_source, 0) + 1
        knock_count = self._knock_count[trigger_source]

        _LOGGER.info(
            "BasedDoor: trigger from '%s' (knock #%d)", trigger_source, knock_count
        )

        # Fire visitor detected event
        self.hass.bus.async_fire(
            EVENT_VISITOR_DETECTED,
            {"trigger_source": trigger_source, "knock_count": knock_count},
        )

        self.hass.async_create_task(
            self._run_pipeline(
                trigger_source=trigger_source,
                camera_entity=camera_entity or self._config.get(CONF_CAMERA_ENTITY),
                mode_override=mode_override,
                knock_count=knock_count,
            )
        )

    # ── Pipeline ─────────────────────────────────────────────────────────────

    async def _run_pipeline(
        self,
        trigger_source: str,
        camera_entity: Optional[str],
        mode_override: Optional[str],
        knock_count: int,
    ) -> None:
        self._active = True
        try:
            await self._pipeline(trigger_source, camera_entity, mode_override, knock_count)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor: pipeline error: %s", exc)
        finally:
            self._active = False

    async def _pipeline(
        self,
        trigger_source: str,
        camera_entity: Optional[str],
        mode_override: Optional[str],
        knock_count: int,
    ) -> None:
        mode = mode_override or self._config.get(CONF_MODE, DEFAULT_MODE)
        time_of_day = get_time_of_day()

        # ── Step 1: Grab camera snapshot ─────────────────────────────────────
        image_bytes: Optional[bytes] = None
        if camera_entity:
            image_bytes = await self._get_snapshot(camera_entity)

        # ── Step 2: Vision analysis (optional) ───────────────────────────────
        vision_result = "unidentified"
        if self.vision and image_bytes:
            _LOGGER.debug("BasedDoor: running LLaVA vision analysis")
            vision_result = await self.vision.classify_visitor(image_bytes)
            _LOGGER.info("BasedDoor: vision result = '%s'", vision_result)

        # ── Step 3: Build LLM context + possible mode escalation ─────────────
        ctx = LLMContext(
            mode=mode,
            vision_result=vision_result,
            visitor_speech="",   # STT is async — we generate response first
            time_of_day=time_of_day,
            knock_count=knock_count,
            recording_active=True,
        )

        effective_mode = should_escalate_mode(mode, knock_count, ctx.is_likely_leo)
        if effective_mode != mode:
            _LOGGER.info("BasedDoor: mode escalated %s → %s", mode, effective_mode)
            ctx.mode = effective_mode

        # ── Step 4: Generate and speak response ──────────────────────────────
        response_text = ""

        if effective_mode == MODE_CLIP:
            await self.clip_player.play()
            response_text = "[user clip played]"
        else:
            response_text = await self.llm.generate_response(ctx)
            _LOGGER.info("BasedDoor: response='%s'", response_text[:80])
            await self.tts.speak(response_text)

        self.hass.bus.async_fire(
            EVENT_RESPONSE_SPOKEN,
            {
                "mode": effective_mode,
                "response": response_text,
                "vision_result": vision_result,
            },
        )

        # ── Step 5: Log interaction ───────────────────────────────────────────
        ts = self.log.log_interaction(
            mode=effective_mode,
            vision_result=vision_result,
            visitor_speech=ctx.visitor_speech,
            response_text=response_text,
            knock_count=knock_count,
            trigger_source=trigger_source,
        )
        if image_bytes:
            self.log.log_snapshot(ts, image_bytes)

        self.hass.bus.async_fire(EVENT_LOG_WRITTEN, {"timestamp": ts})

        # ── Step 6: Push notification ─────────────────────────────────────────
        notify_target = self._config.get(CONF_NOTIFY_TARGET, "")
        if notify_target:
            await self._notify(
                target=notify_target,
                mode=effective_mode,
                vision_result=vision_result,
                response_text=response_text,
                knock_count=knock_count,
            )

        _LOGGER.info("BasedDoor: pipeline complete for trigger '%s'", trigger_source)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_snapshot(self, camera_entity: str) -> Optional[bytes]:
        """Get a camera snapshot from HA."""
        try:
            image = await self.hass.components.camera.async_get_image(camera_entity)
            return image.content
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("BasedDoor: could not get snapshot from %s: %s", camera_entity, exc)
            return None

    async def _notify(
        self,
        target: str,
        mode: str,
        vision_result: str,
        response_text: str,
        knock_count: int,
    ) -> None:
        """Send a silent push notification to the configured mobile target."""
        vision_str = vision_result.replace("_", " ").title()
        try:
            await self.hass.services.async_call(
                "notify",
                target,
                {
                    "title": "🚨 BasedDoor — Visitor Detected",
                    "message": (
                        f"Mode: {mode_label(mode)} | Vision: {vision_str} | "
                        f"Knock #{knock_count}\n\n{response_text[:120]}"
                    ),
                    "data": {
                        "push": {"sound": None},
                        "tag": "baseddoor_visitor",
                    },
                },
                blocking=False,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("BasedDoor: notification failed: %s", exc)

    def reset_knock_count(self, trigger_source: str = "all") -> None:
        """Reset knock counter — call when visitor leaves."""
        if trigger_source == "all":
            self._knock_count.clear()
        else:
            self._knock_count.pop(trigger_source, None)

    # ── Warrant scan ──────────────────────────────────────────────────────────

    async def handle_warrant_scan(
        self,
        camera_entity: Optional[str] = None,
        speaker_entity: Optional[str] = None,
    ) -> None:
        """
        Warrant document scan pipeline:
          camera snapshot → LLaVA OCR → LLM sanity check → TTS result → log
        Requires LLaVA vision model enabled in config.
        """
        _LOGGER.info("BasedDoor Warrant: scan requested")

        if not self.vision:
            msg = (
                "Warrant scan requires LLaVA vision to be enabled. "
                "Enable it in BasedDoor settings and ensure llava model is pulled in Ollama."
            )
            _LOGGER.warning("BasedDoor Warrant: %s", msg)
            await self.tts.speak(
                "Warrant scan unavailable. Vision model is not enabled. "
                "Please enable it in BasedDoor settings."
            )
            return

        # Announce to officer that scan is starting
        await self.tts.speak(
            "Warrant scan initiated. "
            "Please hold the document flat and steady facing the camera. "
            "Scanning now."
        )

        # Grab snapshot
        cam = camera_entity or self._config.get(CONF_CAMERA_ENTITY)
        image_bytes = await self._get_snapshot(cam) if cam else None

        if not image_bytes:
            await self.tts.speak(
                "Warrant scan failed — could not capture camera image. "
                "Please check camera connection and try again."
            )
            return

        # Run scanner
        scanner = WarrantScanner(
            ollama_endpoint=self._config.get(CONF_OLLAMA_ENDPOINT, "http://localhost:11434"),
            llava_model=self._config.get(CONF_LLAVA_MODEL, "llava:7b"),
            llm_model=self._config.get(CONF_OLLAMA_MODEL, "llama3.2:3b"),
        )
        result = await scanner.scan(image_bytes)

        # Speak spoken summary
        spoken = result.spoken_summary or "Warrant scan complete. Review result in the BasedDoor log."
        await self.tts.speak(spoken)

        # Always append disclaimer
        await self.tts.speak(
            "This is an automated extraction only — not legal validation. "
            "Consult legal counsel before taking any action."
        )

        # Log full result
        import json as _json
        log_record = {
            "type": "warrant_scan",
            "overall_status":  result.overall_status,
            "red_flags":       result.red_flags,
            "green_flags":     result.green_flags,
            "summary":         result.summary,
            "spoken_summary":  result.spoken_summary,
            "disclaimer":      result.disclaimer,
        }
        ts = self.log.log_interaction(
            mode="warrant_scan",
            vision_result=result.overall_status,
            visitor_speech="",
            response_text=_json.dumps(log_record),
            knock_count=0,
            trigger_source="warrant_scan",
        )
        self.log.log_snapshot(ts, image_bytes)

        # Notify mobile
        notify_target = self._config.get(CONF_NOTIFY_TARGET, "")
        if notify_target:
            flag_count = len(result.red_flags)
            flag_str = f"🔴 {flag_count} red flag(s)" if flag_count else "✅ No red flags"
            try:
                await self.hass.services.async_call(
                    "notify",
                    notify_target,
                    {
                        "title": "📄 BasedDoor — Warrant Scan Complete",
                        "message": f"{flag_str}\n{result.summary[:200]}",
                        "data": {
                            "push": {"sound": None},
                            "tag": "baseddoor_warrant",
                        },
                    },
                    blocking=False,
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("BasedDoor Warrant: notification failed: %s", exc)

        self.hass.bus.async_fire(
            "baseddoor_warrant_scan_complete",
            {
                "overall_status": result.overall_status,
                "red_flag_count": len(result.red_flags),
                "timestamp":      ts,
            },
        )
        _LOGGER.info("BasedDoor Warrant: pipeline complete — status=%s", result.overall_status)
