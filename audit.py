"""Metadata-only local audit logging with privacy allowlisting."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

SAMPLE_RATE = 0.1


def should_sample(key: str, rate: float = SAMPLE_RATE) -> bool:
    """Deterministically sample detailed audit records without raw content."""
    digest = int(hashlib.sha256(str(key).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return digest < max(0.0, min(1.0, rate))


LOGGER = logging.getLogger("hermes.plugins.typesafe-jev-gate")
_ALLOWED = {
    "tool",
    "outcome",
    "status",
    "mode",
    "decision_type",
    "schema",
    "route",
    "cache_hit",
    "latency_bucket_ms",
    "latency_ms",
    "fallback_reason",
    "paid_tool",
    "risk",
    "choices",
    "sampled",
}


def audit(event: dict[str, Any]) -> None:
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    path = home / "logs" / "jev-gate.jsonl"
    safe = {key: value for key, value in event.items() if key in _ALLOWED}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": time.time(), **safe}, sort_keys=True) + "\n")
    except OSError:
        LOGGER.warning("Could not write Jev audit event", exc_info=True)


__all__ = ["audit", "should_sample"]
