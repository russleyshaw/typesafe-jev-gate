"""Hermes hook adapters for Jev policy decisions."""

from __future__ import annotations

import logging
from typing import Any

from .audit import audit
from .budget import BUDGET
from .config import PAID_TOOLS, disabled, mode
from .policy import _noul, evaluate_tool, risk, route_request
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
        answers = evaluate_tool(tool_name, args, **kwargs)
        secret_safe = _noul(answers, "no_secret_egress")
        injection_free = _noul(answers, "prompt_injection_absent")
        reversible = _noul(answers, "reversible")
        score = risk(answers)
        audit({
            "tool": tool_name,
            "outcome": "evaluated",
            "risk": score,
            "paid_tool": tool_name in PAID_TOOLS,
            "mode": mode(),
        })
        if mode() == "observe":
            return None
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
    markers = ("build", "debug", "deploy", "research", "compare", "multiple", "integrate", "automate")
    if len(text) < 160 and not any(marker in text.lower() for marker in markers):
        return None
    try:
        choice = route_request(text, **kwargs).get("route", {}).get("choice")
        if not choice:
            return None
        audit({"outcome": "route_hint", "route": choice, "mode": mode()})
        if mode() == "observe":
            return None
        return f"Jev route hint: {choice}. Advisory only; obey user and Hermes approvals."
    except Exception as exc:
        LOGGER.warning("Jev route hint unavailable: %s", exc)
        return None


def audit_tool_call(tool_name: str, status: str = "", **kwargs: Any) -> None:
    del kwargs
    if is_jev_candidate(tool_name, {}):
        audit({"tool": tool_name, "outcome": "completed", "status": status})


def register(ctx: Any) -> None:
    ctx.register_hook("pre_tool_call", jev_gate)
    ctx.register_hook("pre_llm_call", route_turn)
    ctx.register_hook("post_tool_call", audit_tool_call)


__all__ = ["audit_tool_call", "jev_gate", "register", "route_turn"]
