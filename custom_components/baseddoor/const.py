"""BasedDoor — Constants."""
from __future__ import annotations

DOMAIN = "baseddoor"
VERSION = "1.0.0"

# Config entry keys
CONF_OLLAMA_ENDPOINT   = "ollama_endpoint"
CONF_OLLAMA_MODEL      = "ollama_model"
CONF_PIPER_ENDPOINT    = "piper_endpoint"
CONF_WHISPER_ENDPOINT  = "whisper_endpoint"
CONF_CAMERA_ENTITY     = "camera_entity"
CONF_SPEAKER_ENTITY    = "speaker_entity"
CONF_MIC_ENTITY        = "mic_entity"
CONF_MODE              = "response_mode"
CONF_ENABLE_VISION     = "enable_vision"
CONF_LLAVA_MODEL       = "llava_model"
CONF_LOG_DIR           = "log_dir"
CONF_ENCRYPT_LOGS      = "encrypt_logs"
CONF_ENCRYPTION_KEY    = "encryption_key"
CONF_NOTIFY_TARGET     = "notify_target"
CONF_PROMPT_DIR        = "prompt_dir"

# Defaults
DEFAULT_OLLAMA_ENDPOINT  = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL     = "llama3.2:3b"
DEFAULT_LLAVA_MODEL      = "llava:7b"
DEFAULT_PIPER_ENDPOINT   = "http://localhost:5000"
DEFAULT_WHISPER_ENDPOINT = "http://localhost:9000"
DEFAULT_LOG_DIR          = "/config/baseddoor_logs"
DEFAULT_MODE             = "polite_canadian"

# Response modes
MODE_POLITE    = "polite_canadian"
MODE_BASED     = "grok_based"
MODE_MAX       = "maximum_refusal"
MODE_CLIP      = "user_clip"

MODES = [MODE_POLITE, MODE_BASED, MODE_MAX, MODE_CLIP]

# Vision labels returned by LLaVA
VISION_UNIFORMED   = "uniformed_officer"
VISION_PLAIN       = "plain_clothes"
VISION_DELIVERY    = "delivery_person"
VISION_UNIDENTIFIED = "unidentified"

# Service names
SERVICE_TRIGGER      = "trigger_response"
SERVICE_SET_MODE     = "set_mode"
SERVICE_TEST_SPEAK   = "test_speak"
SERVICE_EXPORT_LOGS  = "export_logs"

# Event names fired on HA event bus
EVENT_VISITOR_DETECTED  = f"{DOMAIN}_visitor_detected"
EVENT_RESPONSE_SPOKEN   = f"{DOMAIN}_response_spoken"
EVENT_LOG_WRITTEN       = f"{DOMAIN}_log_written"

# Coordinator update interval (seconds) — heartbeat only; real triggers are event-driven
COORDINATOR_UPDATE_INTERVAL = 60

# Log file naming
LOG_DATE_FORMAT = "%Y%m%d_%H%M%S"
