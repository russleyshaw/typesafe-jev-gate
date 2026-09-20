"""Bounded, redacted runtime context for Jev decisions."""

from __future__ import annotations

import json
from typing import Any

from .config import MAX_CONTEXT_CHARS
from .redaction import redact

# Correlation IDs are useful for local audit logs but do not improve a decision.
_PRIVATE_HOOK_FIELDS = {
    "session_id",
    "turn_id",
    "task_id",
    "agent_id",
    "request_id",
    "correlation_id",
}
_CONTEXT_FIELDS = {
    "conversation_history",
    "is_first_turn",
    "model",
    "platform",
    "sender_id",
    "user_message",
    "tool_schema",
    "available_tools",
}


def _fit(value: Any, limit: int = MAX_CONTEXT_CHARS, already_redacted: bool = False) -> Any:
    """Keep the most useful context within Jev's large context window."""
    safe = value if already_redacted else redact(value)
    encoded = json.dumps(safe, sort_keys=True, default=str)
    if len(encoded) <= limit:
        return safe
    if isinstance(safe, list):
        # Preserve both system/setup context and the newest turn context.
        head = safe[:10]
        tail = safe[-40:]
        while len(json.dumps(head + [{"context_truncated": True}] + tail, default=str)) > limit and tail:
            tail.pop(0)
        return head + [{"context_truncated": True}] + tail
    if isinstance(safe, str):
        return safe[:limit] + "…"
    return {"context_truncated": True, "preview": encoded[: max(0, limit - 64)]}


def _history(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    safe = [redact(item) for item in value]
    if len(safe) <= 100:
        return safe
    return safe[:20] + [{"context_truncated": True}] + safe[-79:]


def decision_context(base: dict[str, Any], hook_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Merge decision state with safe runtime context, excluding correlation IDs."""
    context = {
        key: (_history(value) if key == "conversation_history" else redact(value))
        for key, value in hook_kwargs.items()
        if key in _CONTEXT_FIELDS and key not in _PRIVATE_HOOK_FIELDS and value not in (None, "", [], {})
    }
    merged = redact(base)
    if context:
        merged["runtime_context"] = _fit(context, already_redacted=True)
    return merged


__all__ = ["decision_context"]
