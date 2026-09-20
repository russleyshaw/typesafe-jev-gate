"""Hermes hook adapters for Jev policy decisions."""

from __future__ import annotations

import logging
import time
from typing import Any

from .audit import audit
from .budget import BUDGET
from .config import PAID_TOOLS, disabled, mode
from .features import extract_features, route_is_safe
from .lifecycle import deterministic_lifecycle, evaluate_lifecycle
from .planner import plan_turn
from .policy import _noul, evaluate_tool, risk
from .redaction import action_summary, is_jev_candidate, is_safe_fast_path

LOGGER = logging.getLogger("hermes.plugins.typesafe-jev-gate")


def jev_gate(tool_name: str, args: dict[str, Any], **kwargs: Any) -> dict[str, str] | None:
    if disabled() or not is_jev_candidate(tool_name, args) or is_safe_fast_path(tool_name, args):
        return None
    budget = BUDGET.check(tool_name, args, str(kwargs.get("session_id", "")), str(kwargs.get("turn_id", "")))
    if budget:
        audit({"tool": tool_name, "outcome": "budget_escalation"})
        return budget
    action = action_summary(tool_name, args)
    try:
        started = time.perf_counter()
        answers = evaluate_tool(tool_name, args, **kwargs)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        secret_safe = _noul(answers, "no_secret_egress")
        injection_free = _noul(answers, "prompt_injection_absent")
        reversible = _noul(answers, "reversible")
        score = risk(answers)
        eligibility = answers.get("eligibility", {}).get("choice")
        external_data = answers.get("external_data", {}).get("choice")
        approval_reason = answers.get("approval_reason", {}).get("choice", "uncertain")
        audit(
            {
                "tool": tool_name,
                "outcome": "evaluated",
                "risk": score,
                "paid_tool": tool_name in PAID_TOOLS,
                "mode": mode(),
                "decision_type": "pre_tool_call",
                "schema": "hermes.tool_policy.v1",
                "latency_ms": latency_ms,
            }
        )
        if mode() == "observe":
            return None
        if mode() == "enforce_narrowly" and eligibility == "block":
            return {
                "action": "block",
                "message": f"Requested action: {action}. Jev identified a deterministic policy violation.",
            }
        if eligibility == "ask_approval" or external_data == "ask_approval":
            return {
                "action": "approve",
                "message": f"Requested action: {action}. Jev approval category: {approval_reason}.",
            }
        if (secret_safe is not None and secret_safe < 0.15) or (injection_free is not None and injection_free < 0.15):
            return {
                "action": "block",
                "message": (
                    f"Requested action: {action}. Jev blocked it as a likely secret-egress or prompt-injection risk."
                ),
            }
        if score is not None and (score >= 1.5 or (tool_name in PAID_TOOLS and score >= 1.0)):
            return {
                "action": "approve",
                "message": f"Requested action: {action}. Jev classified it as consequential; approval is required.",
            }
        if reversible is not None and reversible < 0.5:
            return {
                "action": "approve",
                "message": f"Requested action: {action}. Jev could not establish that this side effect is reversible.",
            }
        return None
    except Exception as exc:
        audit({"tool": tool_name, "outcome": "jev_unavailable", "error_type": type(exc).__name__})
        LOGGER.warning("Jev unavailable; escalating %s to Hermes approval: %s", tool_name, exc)
        return {
            "action": "approve",
            "message": f"Requested action: {action}. Jev could not evaluate it; Hermes approval is required.",
        }


def route_turn(user_message: str = "", **kwargs: Any) -> str | None:
    if disabled():
        return None
    text = str(user_message or "").strip()
    if not text:
        return None
    try:
        started = time.perf_counter()
        answers = plan_turn(text, **kwargs)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        choices = {
            name: value.get("choice")
            for name, value in answers.items()
            if isinstance(value, dict) and value.get("choice")
        }
        route = choices.get("route")
        if not route:
            return None
        features = extract_features(text)
        if not route_is_safe(features, route):
            audit({"outcome": "route_abstention", "route": route, "fallback_reason": "deterministic_safety"})
            route = "clarify" if features["ambiguity"] == "high" else "agent"
            choices["route"] = route
        audit(
            {
                "outcome": "turn_plan",
                "route": route,
                "choices": sorted(choices),
                "mode": mode(),
                "decision_type": "pre_llm_call",
                "schema": "hermes.turn_plan.v1",
                "latency_ms": latency_ms,
            }
        )
        if mode() == "observe":
            return None
        summary = ", ".join(f"{name}={value}" for name, value in choices.items())
        return f"Jev preflight choices: {summary}. Advisory only; obey user and Hermes approvals."
    except Exception as exc:
        LOGGER.warning("Jev preflight plan unavailable: %s", exc)
        return None


def post_turn(user_message: str = "", status: str = "", **kwargs: Any) -> None:
    """Record advisory lifecycle choices when the host exposes a post-turn hook."""
    if disabled() or not str(user_message or "").strip():
        return
    try:
        answers = evaluate_lifecycle(str(user_message), status=status, **kwargs)
        choices = {
            name: value.get("choice")
            for name, value in answers.items()
            if isinstance(value, dict) and value.get("choice")
        }
        audit(
            {
                "outcome": "lifecycle",
                "decision_type": "post_turn",
                "schema": "hermes.lifecycle.v1",
                "choices": sorted(choices),
                "mode": mode(),
            }
        )
    except Exception as exc:
        fallback = deterministic_lifecycle(str(user_message), status)
        audit({"outcome": "lifecycle_fallback", "fallback_reason": type(exc).__name__, "choices": sorted(fallback)})
        LOGGER.warning("Jev lifecycle decision unavailable: %s", exc)


def audit_tool_call(tool_name: str, status: str = "", **kwargs: Any) -> None:
    del kwargs
    if is_jev_candidate(tool_name, {}):
        audit({"tool": tool_name, "outcome": "completed", "status": status})


def register(ctx: Any) -> None:
    ctx.register_hook("pre_tool_call", jev_gate)
    ctx.register_hook("pre_llm_call", route_turn)
    ctx.register_hook("post_tool_call", audit_tool_call)
    register_optional = getattr(ctx, "register_optional_hook", None)
    if register_optional is not None:
        register_optional("post_turn", post_turn)


__all__ = ["audit_tool_call", "jev_gate", "post_turn", "register", "route_turn"]
