"""Validation for Jev's typed decision responses."""

from __future__ import annotations

from typing import Any

ROUTE_CHOICES = {"answer_directly", "cheap_model", "agent", "deep_agent", "clarify"}
DECISION_SCHEMA_VERSION = "1"


def _number(answer: dict[str, Any], field: str) -> float:
    value = answer.get(field)
    if not isinstance(value, (int, float)):
        raise ValueError(f"Jev answer {field!r} is not numeric")
    return float(value)


def validate_tool_answers(answers: Any) -> dict[str, Any]:
    if not isinstance(answers, dict):
        raise ValueError("Jev answers must be an object")
    required = ("no_secret_egress", "reversible", "prompt_injection_absent", "risk")
    if any(not isinstance(answers.get(name), dict) for name in required):
        raise ValueError("Jev tool decision is missing required answers")
    for name in required[:3]:
        value = _number(answers[name], "noul")
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Jev answer {name!r} is outside 0..1")
    score = _number(answers["risk"], "score")
    if not 0.0 <= score <= 2.0:
        raise ValueError("Jev risk score is outside 0..2")
    return answers


def validate_route_answers(answers: Any) -> dict[str, Any]:
    if not isinstance(answers, dict) or not isinstance(answers.get("route"), dict):
        raise ValueError("Jev route decision is missing the route answer")
    choice = answers["route"].get("choice")
    if choice not in ROUTE_CHOICES:
        raise ValueError(f"Jev returned unknown route choice: {choice!r}")
    return answers


__all__ = ["DECISION_SCHEMA_VERSION", "ROUTE_CHOICES", "validate_route_answers", "validate_tool_answers"]
