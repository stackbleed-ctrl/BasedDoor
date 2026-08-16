"""BasedDoor — Config Flow."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CAMERA_ENTITY,
    CONF_ENABLE_LLM,
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
    DEFAULT_ENABLE_LLM,
    DEFAULT_LLAVA_MODEL,
    DEFAULT_LOG_DIR,
    DEFAULT_MODE,
    DEFAULT_OLLAMA_ENDPOINT,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_PIPER_ENDPOINT,
    DEFAULT_WHISPER_ENDPOINT,
    DOMAIN,
    MODES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CAMERA_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="camera")
        ),
        vol.Optional(CONF_SPEAKER_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="media_player")
        ),
        vol.Required(CONF_MODE, default=DEFAULT_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(options=MODES, mode=selector.SelectSelectorMode.DROPDOWN)
        ),
        vol.Optional(CONF_NOTIFY_TARGET, default=""): str,
        vol.Optional(CONF_ENABLE_LLM, default=DEFAULT_ENABLE_LLM): bool,
        vol.Optional(CONF_OLLAMA_ENDPOINT, default=DEFAULT_OLLAMA_ENDPOINT): str,
        vol.Optional(CONF_OLLAMA_MODEL, default=DEFAULT_OLLAMA_MODEL): str,
        vol.Optional(CONF_PIPER_ENDPOINT, default=DEFAULT_PIPER_ENDPOINT): str,
        vol.Optional(CONF_WHISPER_ENDPOINT, default=DEFAULT_WHISPER_ENDPOINT): str,
        vol.Optional(CONF_ENABLE_VISION, default=False): bool,
        vol.Optional(CONF_LLAVA_MODEL, default=DEFAULT_LLAVA_MODEL): str,
        vol.Optional(CONF_LOG_DIR, default=DEFAULT_LOG_DIR): str,
        vol.Optional(CONF_ENCRYPT_LOGS, default=True): bool,
        vol.Optional(CONF_ENCRYPTION_KEY, default=""): str,
    }
)


async def _test_ollama(endpoint: str, model: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{endpoint.rstrip('/')}/api/tags")
            if resp.status_code != 200:
                return "ollama_unreachable"
            names = [m.get("name", "") for m in resp.json().get("models", [])]
            base = model.split(":")[0]
            if not any(base in name for name in names):
                return "model_not_found"
    except Exception:  # noqa: BLE001
        return "ollama_unreachable"
    return None


class BasedDoorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}
        if user_input is not None:
            enable_llm = bool(user_input.get(CONF_ENABLE_LLM, False))
            enable_vision = bool(user_input.get(CONF_ENABLE_VISION, False))

            if enable_vision and not enable_llm:
                errors[CONF_ENABLE_VISION] = "vision_requires_llm"

            if enable_llm and not errors:
                err = await _test_ollama(
                    user_input.get(CONF_OLLAMA_ENDPOINT, DEFAULT_OLLAMA_ENDPOINT),
                    user_input.get(CONF_OLLAMA_MODEL, DEFAULT_OLLAMA_MODEL),
                )
                if err == "model_not_found":
                    errors[CONF_OLLAMA_MODEL] = err
                elif err:
                    errors[CONF_OLLAMA_ENDPOINT] = err

            if not errors:
                if user_input.get(CONF_ENCRYPT_LOGS) and not user_input.get(CONF_ENCRYPTION_KEY):
                    from cryptography.fernet import Fernet
                    user_input[CONF_ENCRYPTION_KEY] = Fernet.generate_key().decode()

                try:
                    os.makedirs(user_input.get(CONF_LOG_DIR, DEFAULT_LOG_DIR), exist_ok=True)
                except OSError as exc:
                    _LOGGER.warning("Could not create BasedDoor log directory: %s", exc)

                return self.async_create_entry(title="BasedDoor", data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return BasedDoorOptionsFlow(config_entry)


class BasedDoorOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._config_entry.data, **self._config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=current.get(CONF_MODE, DEFAULT_MODE)):
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(options=MODES, mode=selector.SelectSelectorMode.DROPDOWN)
                    ),
                vol.Optional(CONF_ENABLE_LLM, default=current.get(CONF_ENABLE_LLM, False)): bool,
                vol.Optional(CONF_ENABLE_VISION, default=current.get(CONF_ENABLE_VISION, False)): bool,
                vol.Optional(CONF_ENCRYPT_LOGS, default=current.get(CONF_ENCRYPT_LOGS, True)): bool,
                vol.Optional(CONF_NOTIFY_TARGET, default=current.get(CONF_NOTIFY_TARGET, "")): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
