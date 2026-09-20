"""Read-only aggregation of privacy-safe Jev audit metadata."""

from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import median
from typing import Any


def report(path: str | Path | None = None) -> dict[str, Any]:
    audit_path = Path(path or Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "logs" / "jev-gate.jsonl")
    events: list[dict[str, Any]] = []
    if audit_path.exists():
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                events.append(value)
    latencies = sorted(float(item["latency_ms"]) for item in events if isinstance(item.get("latency_ms"), (int, float)))
    p95_index = max(0, min(len(latencies) - 1, round(len(latencies) * 0.95) - 1)) if latencies else None
    return {
        "events": len(events),
        "decisions": sum(item.get("outcome") == "evaluated" for item in events),
        "errors": sum(item.get("outcome") in {"jev_unavailable", "fallback"} for item in events),
        "cache_hits": sum(bool(item.get("cache_hit")) for item in events),
        "latency_p50_ms": median(latencies) if latencies else None,
        "latency_p95_ms": latencies[p95_index] if p95_index is not None else None,
    }


__all__ = ["report"]
