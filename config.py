"""Static policy and transport configuration for the Jev plugin."""

API_URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "~typesafe/jev-latest"
TIMEOUT_SECONDS = 3.0
CACHE_TTL_SECONDS = 30.0
MAX_CACHE_ENTRIES = 256
MAX_SIDE_EFFECTS_PER_TURN = 8
MAX_REPEATED_CALLS_PER_TURN = 2
MAX_STRING = 1200
MAX_CONTEXT_CHARS = 96000
MAX_DECISIONS_PER_TURN = 4
MODE_ENV = "HERMES_JEV_MODE"
DISABLED_ENV = "HERMES_JEV_DISABLED"
DEFAULT_MODE = "advise"

ALLOWED_MODES = {"observe", "advise", "enforce_narrowly"}


def disabled() -> bool:
    import os

    return os.environ.get(DISABLED_ENV, "").lower() in {"1", "true", "yes"}


def mode() -> str:
    import os

    if disabled():
        return "observe"
    value = os.environ.get(MODE_ENV, DEFAULT_MODE)
    return value if value in ALLOWED_MODES else DEFAULT_MODE


SIDE_EFFECT_TOOLS = {
    "terminal",
    "write_file",
    "patch",
    "ha_call_service",
    "browser_vault_fill",
    "browser_vault_save_login",
    "browser_vault_enter_code",
    "image_generate",
    "text_to_speech",
    "tool_call",
}
PAID_TOOLS = {"image_generate", "text_to_speech", "web_extract", "web_search"}
