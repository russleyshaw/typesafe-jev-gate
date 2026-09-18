"""Metadata-only local audit logging."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("hermes.plugins.typesafe-jev-gate")


def audit(event: dict[str, Any]) -> None:
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    path = home / "logs" / "jev-gate.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": time.time(), **event}, sort_keys=True) + "\n")
    except OSError:
        LOGGER.warning("Could not write Jev audit event", exc_info=True)
