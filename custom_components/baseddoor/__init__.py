"""BasedDoor — Home Assistant Integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_CAMERA_ENTITY,
    CONF_MODE,
    DOMAIN,
    MODES,
    SERVICE_EXPORT_LOGS,
    SERVICE_SET_MODE,
    SERVICE_TEST_SPEAK,
    SERVICE_TRIGGER,
)
from .coordinator import BasedDoorCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SCAN_WARRANT = "scan_warrant"

# ── Service schemas ───────────────────────────────────────────────────────────

SERVICE_TRIGGER_SCHEMA = vol.Schema({
    vol.Optional("trigger_source", default="manual"): cv.string,
    vol.Optional("camera_entity"): cv.entity_id,
    vol.Optional("mode"): vol.In(MODES),
})

SERVICE_SET_MODE_SCHEMA = vol.Schema({
    vol.Required("mode"): vol.In(MODES),
})

SERVICE_TEST_SPEAK_SCHEMA = vol.Schema({
    vol.Optional("message", default=(
        "BasedDoor is online. No consent. No cooperation. Recording active."
    )): cv.string,
})

SERVICE_EXPORT_LOGS_SCHEMA = vol.Schema({
    vol.Optional("dest_path", default="/config/baseddoor_export"): cv.string,
})

SERVICE_SCAN_WARRANT_SCHEMA = vol.Schema({
    vol.Optional("camera_entity"):  cv.entity_id,
    vol.Optional("speaker_entity"): cv.entity_id,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BasedDoor from a config entry."""
    _LOGGER.info("BasedDoor: setting up integration v%s", entry.data.get("version", "0.1.0"))

    config = {**entry.data, **entry.options}

    coordinator = BasedDoorCoordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # ── Service handlers ──────────────────────────────────────────────────────

    async def handle_trigger(call: ServiceCall) -> None:
        await coordinator.handle_trigger(
            trigger_source=call.data.get("trigger_source", "manual"),
            camera_entity=call.data.get("camera_entity"),
            mode_override=call.data.get("mode"),
        )

    async def handle_set_mode(call: ServiceCall) -> None:
        new_mode = call.data["mode"]
        updated_options = {**entry.options, CONF_MODE: new_mode}
        hass.config_entries.async_update_entry(entry, options=updated_options)
        coordinator._config[CONF_MODE] = new_mode
        _LOGGER.info("BasedDoor: mode set to '%s'", new_mode)

    async def handle_test_speak(call: ServiceCall) -> None:
        await coordinator.tts.speak(
            call.data.get("message", "BasedDoor is active.")
        )

    async def handle_export_logs(call: ServiceCall) -> None:
        dest    = call.data.get("dest_path", "/config/baseddoor_export")
        zip_path = coordinator.log.export_zip(dest)
        _LOGGER.info("BasedDoor: logs exported to %s", zip_path)

    async def handle_scan_warrant(call: ServiceCall) -> None:
        """
        Capture a camera snapshot of the document held to the door,
        run LLaVA OCR extraction + LLM sanity check, speak the result via TTS,
        and write the full log entry (image + OCR JSON + summary) locally encrypted.
        Requires enable_vision: true and llava model pulled in Ollama.
        """
        await coordinator.handle_warrant_scan(
            camera_entity=call.data.get("camera_entity", config.get(CONF_CAMERA_ENTITY)),
            speaker_entity=call.data.get("speaker_entity", config.get("speaker_entity")),
        )

    # ── Register all services ─────────────────────────────────────────────────
    hass.services.async_register(DOMAIN, SERVICE_TRIGGER,      handle_trigger,      SERVICE_TRIGGER_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_MODE,     handle_set_mode,     SERVICE_SET_MODE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_TEST_SPEAK,   handle_test_speak,   SERVICE_TEST_SPEAK_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_EXPORT_LOGS,  handle_export_logs,  SERVICE_EXPORT_LOGS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SCAN_WARRANT, handle_scan_warrant, SERVICE_SCAN_WARRANT_SCHEMA)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info("BasedDoor: integration ready — mode=%s, warrant_scan=enabled", config.get(CONF_MODE))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    for service in (
        SERVICE_TRIGGER,
        SERVICE_SET_MODE,
        SERVICE_TEST_SPEAK,
        SERVICE_EXPORT_LOGS,
        SERVICE_SCAN_WARRANT,
    ):
        hass.services.async_remove(DOMAIN, service)

    hass.data[DOMAIN].pop(entry.entry_id, None)
    _LOGGER.info("BasedDoor: integration unloaded")
    return True
