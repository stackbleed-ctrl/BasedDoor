"""BasedDoor — Main Pipeline Coordinator."""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .capabilities import build_capability_report
from .const import (
    CONF_CAMERA_ENTITY, CONF_ENABLE_LLM, CONF_ENABLE_VISION, CONF_ENCRYPT_LOGS,
    CONF_ENCRYPTION_KEY, CONF_LLAVA_MODEL, CONF_LOG_DIR, CONF_MODE,
    CONF_NOTIFY_TARGET, CONF_OLLAMA_ENDPOINT, CONF_OLLAMA_MODEL,
    CONF_PIPER_ENDPOINT, CONF_SPEAKER_ENTITY, COORDINATOR_UPDATE_INTERVAL,
    DEFAULT_LOG_DIR, DEFAULT_MODE, DOMAIN, EVENT_LOG_WRITTEN,
    EVENT_RESPONSE_SPOKEN, EVENT_VISITOR_DETECTED, MODE_CLIP,
)
from .llm_engine import LLMContext, OllamaEngine, deterministic_response
from .logger import InteractionLogger
from .modes import ClipPlayer, get_time_of_day, mode_label, should_escalate_mode
from .tts_engine import PiperTTSEngine
from .vision import VisionEngine
from .warrant_scanner import WarrantScanner

_LOGGER = logging.getLogger(__name__)


class BasedDoorCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=COORDINATOR_UPDATE_INTERVAL),
        )
        self._config = config
        self._knock_count: dict[str, int] = {}
        self._active = False

        self.llm: OllamaEngine | None = None
        if config.get(CONF_ENABLE_LLM, False):
            self.llm = OllamaEngine(
                endpoint=config.get(CONF_OLLAMA_ENDPOINT, "http://localhost:11434"),
                model=config.get(CONF_OLLAMA_MODEL, "llama3.2:3b"),
            )

        self.tts = PiperTTSEngine(
            hass=hass,
            piper_endpoint=config.get(CONF_PIPER_ENDPOINT, ""),
            speaker_entity=config.get(CONF_SPEAKER_ENTITY, ""),
        )

        self.vision: VisionEngine | None = None
        if config.get(CONF_ENABLE_LLM, False) and config.get(CONF_ENABLE_VISION, False):
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
            hass=hass, speaker_entity=config.get(CONF_SPEAKER_ENTITY, "")
        )

    async def _async_update_data(self) -> dict:
        caps = build_capability_report(self.hass, self._config)
        return {
            "active": self._active,
            "knock_counts": dict(self._knock_count),
            "capabilities": caps.as_dict(),
        }

    async def handle_trigger(
        self,
        trigger_source: str = "unknown",
        camera_entity: Optional[str] = None,
        mode_override: Optional[str] = None,
    ) -> None:
        if self._active:
            _LOGGER.debug("BasedDoor trigger ignored: pipeline already active")
            return

        self._knock_count[trigger_source] = self._knock_count.get(trigger_source, 0) + 1
        count = self._knock_count[trigger_source]
        self.hass.bus.async_fire(
            EVENT_VISITOR_DETECTED,
            {"trigger_source": trigger_source, "knock_count": count},
        )
        self.hass.async_create_task(
            self._run_pipeline(
                trigger_source,
                camera_entity or self._config.get(CONF_CAMERA_ENTITY),
                mode_override,
                count,
            )
        )

    async def _run_pipeline(self, trigger_source, camera_entity, mode_override, knock_count):
        self._active = True
        try:
            await self._pipeline(trigger_source, camera_entity, mode_override, knock_count)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("BasedDoor pipeline failed: %s", exc)
        finally:
            self._active = False

    async def _pipeline(self, trigger_source, camera_entity, mode_override, knock_count):
        mode = mode_override or self._config.get(CONF_MODE, DEFAULT_MODE)
        caps = build_capability_report(self.hass, self._config)

        image_bytes = None
        if camera_entity and caps.camera_available:
            image_bytes = await self._get_snapshot(camera_entity)

        vision_result = "unidentified"
        if self.vision and image_bytes:
            vision_result = await self.vision.classify_visitor(image_bytes)

        ctx = LLMContext(
            mode=mode,
            vision_result=vision_result,
            visitor_speech="",
            time_of_day=get_time_of_day(),
            knock_count=knock_count,
            recording_active=caps.recording_confirmed,
        )

        effective_mode = should_escalate_mode(mode, knock_count, ctx.is_likely_leo)
        ctx.mode = effective_mode

        if effective_mode == MODE_CLIP and caps.can_speak:
            await self.clip_player.play()
            response_text = "[configured user clip played]"
        else:
            response_text = (
                await self.llm.generate_response(ctx)
                if self.llm is not None
                else deterministic_response(ctx)
            )
            if caps.can_speak:
                await self.tts.speak(response_text)

        self.hass.bus.async_fire(
            EVENT_RESPONSE_SPOKEN,
            {
                "mode": effective_mode,
                "response": response_text,
                "vision_result": vision_result,
                "spoken": caps.can_speak,
            },
        )

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

        target = self._config.get(CONF_NOTIFY_TARGET, "")
        if target:
            await self._notify(target, effective_mode, vision_result, response_text, knock_count)

    async def _get_snapshot(self, camera_entity: str):
        try:
            image = await self.hass.components.camera.async_get_image(camera_entity)
            return image.content
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Snapshot unavailable from %s: %s", camera_entity, exc)
            return None

    async def _notify(self, target, mode, vision_result, response_text, knock_count):
        try:
            await self.hass.services.async_call(
                "notify",
                target,
                {
                    "title": "BasedDoor — visitor event",
                    "message": (
                        f"Mode: {mode_label(mode)} | Classification: "
                        f"{vision_result.replace('_', ' ')} | Contact #{knock_count}\n\n"
                        f"{response_text[:160]}"
                    ),
                    "data": {"push": {"sound": None}, "tag": "baseddoor_visitor"},
                },
                blocking=False,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("BasedDoor notification failed: %s", exc)

    def reset_knock_count(self, trigger_source: str = "all") -> None:
        if trigger_source == "all":
            self._knock_count.clear()
        else:
            self._knock_count.pop(trigger_source, None)

    async def handle_warrant_scan(
        self,
        camera_entity: Optional[str] = None,
        speaker_entity: Optional[str] = None,
    ) -> None:
        """Capture and extract a legal document; never determine legal validity."""
        if not self.vision or not self.llm:
            _LOGGER.warning("Document extraction requires local LLM + vision")
            if self.tts.configured:
                await self.tts.speak(
                    "Document extraction is unavailable because local vision is not enabled."
                )
            return

        cam = camera_entity or self._config.get(CONF_CAMERA_ENTITY)
        image_bytes = await self._get_snapshot(cam) if cam else None
        if not image_bytes:
            if self.tts.configured:
                await self.tts.speak("Document image could not be captured.")
            return

        scanner = WarrantScanner(
            ollama_endpoint=self._config.get(CONF_OLLAMA_ENDPOINT, "http://localhost:11434"),
            llava_model=self._config.get(CONF_LLAVA_MODEL, "llava:7b"),
            llm_model=self._config.get(CONF_OLLAMA_MODEL, "llama3.2:3b"),
        )
        result = await scanner.scan(image_bytes)

        if self.tts.configured:
            await self.tts.speak(result.spoken_summary)

        record = {
            "type": "legal_document_extraction",
            "read_status": result.overall_status,
            "review_flags": result.red_flags,
            "observed_fields": result.green_flags,
            "summary": result.summary,
            "disclaimer": result.disclaimer,
        }
        ts = self.log.log_interaction(
            mode="document_scan",
            vision_result=result.overall_status,
            visitor_speech="",
            response_text=json.dumps(record),
            knock_count=0,
            trigger_source="document_scan",
        )
        self.log.log_snapshot(ts, image_bytes)

        target = self._config.get(CONF_NOTIFY_TARGET, "")
        if target:
            await self.hass.services.async_call(
                "notify",
                target,
                {
                    "title": "BasedDoor — document captured",
                    "message": result.summary[:220],
                    "data": {"push": {"sound": None}, "tag": "baseddoor_document"},
                },
                blocking=False,
            )

        self.hass.bus.async_fire(
            "baseddoor_document_scan_complete",
            {
                "read_status": result.overall_status,
                "review_flag_count": len(result.red_flags),
                "timestamp": ts,
            },
        )
