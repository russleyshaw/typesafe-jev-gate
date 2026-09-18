"""Static policy and transport configuration for the Jev plugin."""

API_URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "~typesafe/jev-latest"
TIMEOUT_SECONDS = 3.0
CACHE_TTL_SECONDS = 30.0
MAX_CACHE_ENTRIES = 256
MAX_SIDE_EFFECTS_PER_TURN = 8
MAX_REPEATED_CALLS_PER_TURN = 2
MAX_STRING = 1200

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
