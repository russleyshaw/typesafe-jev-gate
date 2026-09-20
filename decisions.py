"""Validation for Jev's typed decision responses."""

from __future__ import annotations

from typing import Any

ROUTE_CHOICES = {"answer_directly", "cheap_model", "agent", "deep_agent", "clarify"}
DECISION_SCHEMA_VERSION = "1"

PREFLIGHT_CHOICES = {
    "eligibility": {"run", "ask_approval", "block"},
    "external_data": {"allow", "ask_approval", "block"},
    "retry": {"retry_same", "retry_simplified", "escalate", "stop"},
    "batching": {"single", "parallel_safe", "sequential_required"},
    "approval_reason": {"external_effect", "sensitive_data", "irreversible", "uncertain", "budget"},
}

LIFECYCLE_CHOICES = {
    "session": {"chat", "research", "coding", "automation", "high_impact"},
    "context": {"preserve", "prune", "compress"},
    "skills": {"none", "suggest"},
    "quality": {"complete", "needs_followup", "likely_failed", "approval_pending"},
    "sampling": {"minimum", "detailed"},
}

PLAN_CHOICES = {
    "route": ROUTE_CHOICES,
    "toolset": {"chat_only", "file_terminal", "web_browser", "automation", "full_agent"},
    "tool_search": {"skip", "search", "search_and_describe", "search_parallel"},
    "context": {"keep", "retrieve", "compress_tools", "focus"},
    "compression": {"none", "tool_results", "focused", "full"},
    "memory": {"skip", "preferences", "project", "history"},
    "skills": {"none", "one", "bundle", "defer"},
    "delegation": {"none", "sequential", "parallel", "review"},
    "parallelism": {"single", "parallel", "sequential"},
    "retry": {"stop", "simplify", "alternate", "approval"},
    "clarification": {"none", "safe_assumption", "clarify_required"},
    "completion": {"continue", "likely_complete", "needs_verification"},
}


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
    _validate_choice_answers(answers, PREFLIGHT_CHOICES)
    return answers


def validate_plan_answers(answers: Any) -> dict[str, Any]:
    """Validate the multi-choice planner while tolerating older partial replies."""
    if not isinstance(answers, dict) or not isinstance(answers.get("route"), dict):
        raise ValueError("Jev preflight plan is missing the route answer")
    for name, allowed in PLAN_CHOICES.items():
        answer = answers.get(name)
        if answer is None:
            continue
        if not isinstance(answer, dict) or answer.get("choice") not in allowed:
            raise ValueError(f"Jev returned unknown {name} choice")
    return answers


def _validate_choice_answers(
    answers: Any, choices: dict[str, set[str]], required: tuple[str, ...] = ()
) -> dict[str, Any]:
    if not isinstance(answers, dict):
        raise ValueError("Jev decision answers must be an object")
    for name in required:
        if not isinstance(answers.get(name), dict):
            raise ValueError(f"Jev decision is missing required {name} answer")
    for name, allowed in choices.items():
        answer = answers.get(name)
        if answer is not None and (not isinstance(answer, dict) or answer.get("choice") not in allowed):
            raise ValueError(f"Jev returned unknown {name} choice")
    return answers


def validate_preflight_answers(answers: Any) -> dict[str, Any]:
    return _validate_choice_answers(answers, PREFLIGHT_CHOICES, ("eligibility",))


def validate_lifecycle_answers(answers: Any) -> dict[str, Any]:
    return _validate_choice_answers(answers, LIFECYCLE_CHOICES)


def validate_route_answers(answers: Any) -> dict[str, Any]:
    return validate_plan_answers(answers)


__all__ = [
    "DECISION_SCHEMA_VERSION",
    "LIFECYCLE_CHOICES",
    "PREFLIGHT_CHOICES",
    "PLAN_CHOICES",
    "ROUTE_CHOICES",
    "validate_lifecycle_answers",
    "validate_plan_answers",
    "validate_preflight_answers",
    "validate_route_answers",
    "validate_tool_answers",
]
