"""Runtime capability reporting for BasedDoor.

Capabilities describe what the current installation can actually do. They are
not promises about a brand or model number.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CapabilityReport:
    camera_configured: bool
    camera_available: bool
    speaker_configured: bool
    speaker_available: bool
    notifications_configured: bool
    local_llm_enabled: bool
    vision_enabled: bool
    encrypted_logs_enabled: bool
    recording_confirmed: bool = False

    @property
    def can_capture_snapshot(self) -> bool:
        return self.camera_configured and self.camera_available

    @property
    def can_speak(self) -> bool:
        return self.speaker_configured and self.speaker_available

    @property
    def operating_mode(self) -> str:
        if self.can_speak and self.can_capture_snapshot and self.local_llm_enabled:
            return "local_ai"
        if self.can_speak:
            return "deterministic_voice"
        if self.notifications_configured or self.can_capture_snapshot:
            return "observe_notify"
        return "manual_only"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            can_capture_snapshot=self.can_capture_snapshot,
            can_speak=self.can_speak,
            operating_mode=self.operating_mode,
        )
        return data


def _entity_available(hass: Any, entity_id: str | None) -> bool:
    if not entity_id:
        return False
    state = hass.states.get(entity_id)
    if state is None:
        return False
    return state.state not in {"unavailable", "unknown"}


def build_capability_report(hass: Any, config: dict[str, Any]) -> CapabilityReport:
    camera = config.get("camera_entity") or ""
    speaker = config.get("speaker_entity") or ""
    return CapabilityReport(
        camera_configured=bool(camera),
        camera_available=_entity_available(hass, camera),
        speaker_configured=bool(speaker),
        speaker_available=_entity_available(hass, speaker),
        notifications_configured=bool(config.get("notify_target")),
        local_llm_enabled=bool(config.get("enable_llm", False)),
        vision_enabled=bool(config.get("enable_vision", False)),
        encrypted_logs_enabled=bool(config.get("encrypt_logs", True)),
        # Alpha 0.2 deliberately does not infer recording from camera presence.
        recording_confirmed=False,
    )
