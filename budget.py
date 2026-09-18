"""Per-turn repetition and side-effect budgets."""

from __future__ import annotations

import threading
from typing import Any

from .config import MAX_REPEATED_CALLS_PER_TURN, MAX_SIDE_EFFECTS_PER_TURN
from .redaction import action_summary, fingerprint


class TurnBudget:
    def __init__(self) -> None:
        self._turns: dict[tuple[str, str], dict[str, Any]] = {}
        self._lock = threading.Lock()

    def check(self, tool_name: str, args: dict[str, Any], session_id: str, turn_id: str) -> dict[str, str] | None:
        if not session_id or not turn_id:
            return None
        key = (session_id, turn_id)
        call_id = fingerprint(tool_name, args)
        with self._lock:
            state = self._turns.setdefault(key, {"count": 0, "calls": {}})
            state["count"] += 1
            calls = state["calls"]
            calls[call_id] = calls.get(call_id, 0) + 1
            if len(self._turns) > 512:
                self._turns.pop(next(iter(self._turns)))
            count = state["count"]
            repeated = calls[call_id]
        action = action_summary(tool_name, args)
        if repeated > MAX_REPEATED_CALLS_PER_TURN:
            return {
                "action": "approve",
                "message": (
                    f"Requested action: {action}. Jev budget guard: this action has been repeated too many times."
                ),
            }
        if count > MAX_SIDE_EFFECTS_PER_TURN:
            return {
                "action": "approve",
                "message": (
                    f"Requested action: {action}. Jev budget guard: "
                    "this turn has exceeded its side-effecting tool budget."
                ),
            }
        return None


BUDGET = TurnBudget()

__all__ = ["BUDGET", "TurnBudget"]
