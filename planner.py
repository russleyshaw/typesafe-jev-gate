"""One-call Jev planner for pre-main-LLM choices."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .client import CLIENT
from .config import MAX_CONTEXT_CHARS
from .context import decision_context
from .decisions import ROUTE_CHOICES, validate_plan_answers

SCHEMA = "hermes.turn_plan.v1"

# These are choices, not prose-generation tasks. Keep the contract stable so the
# planner can be cached and evaluated independently of Hermes' main model.
QUESTIONS = {
    "route": {
        "type": "choice",
        "instructions": "Choose the cheapest reliable execution route.",
        "criteria": {choice: choice for choice in ROUTE_CHOICES},
    },
    "toolset": {
        "type": "choice",
        "instructions": "Choose the smallest tool capability set likely to complete the request.",
        "criteria": {
            "chat_only": "No tools",
            "file_terminal": "Files or terminal",
            "web_browser": "Web or browser",
            "automation": "External services or automation",
            "full_agent": "Several tool categories or delegation",
        },
    },
    "tool_search": {
        "type": "choice",
        "instructions": "Choose the smallest tool-discovery operation needed.",
        "criteria": {
            "skip": "Known tools or no tools needed",
            "search": "Search deferred tools by intent",
            "search_and_describe": "Search then load selected schemas",
            "search_parallel": "Search independent tool categories in parallel",
        },
    },
    "context": {
        "type": "choice",
        "instructions": "Choose the context treatment before the main model call.",
        "criteria": {
            "keep": "Current context is sufficient",
            "retrieve": "Relevant older context or memory is needed",
            "compress_tools": "Old tool output can be reduced",
            "focus": "Keep only context relevant to the current topic",
        },
    },
    "compression": {
        "type": "choice",
        "instructions": "Choose whether context compression should run.",
        "criteria": {
            "none": "Do not compress",
            "tool_results": "Prune or summarize old tool results first",
            "focused": "Compress while preserving constraints and decisions",
            "full": "Run normal conversation compression",
        },
    },
    "memory": {
        "type": "choice",
        "instructions": "Choose whether memory or session search is relevant.",
        "criteria": {
            "skip": "No memory needed",
            "preferences": "Retrieve user preferences or durable facts",
            "project": "Retrieve project or prior-session facts",
            "history": "Retrieve a prior decision or conversation detail",
        },
    },
    "skills": {
        "type": "choice",
        "instructions": "Choose skill loading behavior.",
        "criteria": {
            "none": "No specialized skill",
            "one": "Load one focused skill",
            "bundle": "Load a small compatible skill bundle",
            "defer": "Defer skill loading until clarification or next turn",
        },
    },
    "delegation": {
        "type": "choice",
        "instructions": "Choose delegation behavior.",
        "criteria": {
            "none": "Do not delegate",
            "sequential": "Delegate dependent subtasks sequentially",
            "parallel": "Delegate independent subtasks in parallel",
            "review": "Delegate verification or review only",
        },
    },
    "retry": {
        "type": "choice",
        "instructions": "Choose the default recovery strategy if a tool fails.",
        "criteria": {
            "stop": "Stop and report the failure",
            "simplify": "Simplify arguments and retry once",
            "alternate": "Use an alternate eligible tool",
            "approval": "Escalate to Hermes approval",
        },
    },
    "parallelism": {
        "type": "choice",
        "instructions": "Choose safe execution ordering.",
        "criteria": {"single": "One action", "sequential": "Dependent actions", "parallel": "Independent safe actions"},
    },
    "clarification": {
        "type": "choice",
        "instructions": "Decide whether ambiguity materially blocks safe progress.",
        "criteria": {
            "none": "No clarification",
            "safe_assumption": "Proceed with an explicit safe assumption",
            "clarify_required": "Ask the user first",
        },
    },
    "completion": {
        "type": "choice",
        "instructions": "Decide whether the request likely needs more work or verification.",
        "criteria": {
            "continue": "Continue",
            "likely_complete": "Likely complete",
            "needs_verification": "Verify before finishing",
        },
    },
}


def plan_turn(user_message: str, **hook_kwargs: Any) -> dict[str, Any]:
    """Return typed preflight choices using the maximum safe available context."""
    state = decision_context(
        {
            "request": user_message,
            "policy": (
                "Make conservative, typed preflight choices. Preserve user intent, exact constraints, "
                "secrets, safety approvals, and irreversible-action safeguards."
            ),
        },
        {"user_message": user_message, **hook_kwargs},
    )
    payload = {
        "schema": SCHEMA,
        "state": json.dumps(state, sort_keys=True, default=str),
        "questions": QUESTIONS,
        "limits": {"max_state_chars": MAX_CONTEXT_CHARS, "typed_answers_only": True},
    }
    cache_key = (
        "plan:" + hashlib.sha256(json.dumps(payload["state"], sort_keys=True, default=str).encode()).hexdigest()[:24]
    )
    return validate_plan_answers(CLIENT.decide(cache_key, payload))


__all__ = ["QUESTIONS", "SCHEMA", "plan_turn"]
