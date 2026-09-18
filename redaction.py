"""Argument classification, redaction, and safe approval descriptions."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .config import MAX_STRING, SIDE_EFFECT_TOOLS

_SAFE_TERMINAL = re.compile(
    r"^\s*(?:pwd|date|whoami|git\s+(?:status|diff(?:\s+--stat)?|log(?:\s+-\d+)?))\s*$",
    re.IGNORECASE,
)
_SECRET_KEY = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|auth|authorization|cookie|password|passwd|secret|private[_-]?key|cvc)"
)
_SECRET_VALUE = re.compile(
    r"(?i)(?:authorization|api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s,;]+|\b(?:bearer|basic)\s+[^\s,;]+|\b(?:sk|pk|ghp|xox[baprs])-?[A-Za-z0-9_\-]{12,}\b"
)


def is_side_effecting(tool_name: str, args: dict[str, Any]) -> bool:
    if tool_name in SIDE_EFFECT_TOOLS:
        return True
    if any(word in tool_name.lower() for word in ("send", "post", "delete", "update", "create", "place", "close")):
        return True
    command = str(args.get("command", ""))
    return bool(command and re.search(r"(?i)\b(?:rm|mv|cp|chmod|chown|curl|wget|git\s+push|pip\s+install)\b", command))


def is_safe_fast_path(tool_name: str, args: dict[str, Any]) -> bool:
    return tool_name == "terminal" and bool(_SAFE_TERMINAL.fullmatch(str(args.get("command", ""))))


def redact(value: Any, key: str = "") -> Any:
    if _SECRET_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str):
            value = _SECRET_VALUE.sub("[REDACTED]", value)
            return value[:MAX_STRING] + ("…" if len(value) > MAX_STRING else "")
        return value
    return str(value)[:MAX_STRING]


def fingerprint(tool_name: str, args: dict[str, Any]) -> str:
    data = json.dumps({"tool": tool_name, "args": redact(args)}, sort_keys=True, default=str)
    return hashlib.sha256(data.encode()).hexdigest()[:24]


def action_summary(tool_name: str, args: dict[str, Any]) -> str:
    safe = redact(args)
    if tool_name == "write_file":
        return f"write file {safe.get('path', '[path unavailable]')}"
    if tool_name == "patch":
        return f"edit file {safe.get('path', '[path unavailable]')}"
    if tool_name == "terminal":
        return f"run command: {safe.get('command', '[command unavailable]')}"
    if tool_name == "ha_call_service":
        service = f"{safe.get('domain', '')}.{safe.get('service', '')}".strip(".")
        return f"call Home Assistant service {service} on {safe.get('entity_id', '[entity unavailable]')}"
    if tool_name == "image_generate":
        return "generate or edit an image"
    if tool_name == "text_to_speech":
        return "generate speech audio"
    if tool_name.startswith("browser_vault_"):
        return "use saved website credentials or payment information"
    return f"execute {tool_name}"
