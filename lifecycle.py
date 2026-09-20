"""Typed lifecycle signals kept advisory and bounded."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .client import CLIENT
from .context import decision_context
from .decisions import LIFECYCLE_CHOICES, validate_lifecycle_answers
from .features import extract_features

SCHEMA = "hermes.lifecycle.v1"
QUESTIONS = {
    "session": {"type": "choice", "criteria": {choice: choice for choice in LIFECYCLE_CHOICES["session"]}},
    "context": {
        "type": "choice",
        "criteria": {"preserve": "Keep", "prune": "Prune old tool output", "compress": "Use normal compression"},
    },
    "skills": {"type": "choice", "criteria": {"none": "No suggestion", "suggest": "Suggest eligible categories"}},
    "quality": {"type": "choice", "criteria": {choice: choice for choice in LIFECYCLE_CHOICES["quality"]}},
    "sampling": {"type": "choice", "criteria": {"minimum": "Metadata minimum", "detailed": "Detailed audit"}},
}


def evaluate_lifecycle(user_message: str, **hook_kwargs: Any) -> dict[str, Any]:
    state = decision_context(
        {"request": user_message, "features": extract_features(user_message)},
        {"user_message": user_message, **hook_kwargs},
    )
    payload = {
        "schema": SCHEMA,
        "state": json.dumps(state, sort_keys=True, default=str),
        "questions": QUESTIONS,
        "limits": {"typed_answers_only": True},
    }
    key = "lifecycle:" + hashlib.sha256(payload["state"].encode()).hexdigest()[:24]
    return validate_lifecycle_answers(CLIENT.decide(key, payload))


def deterministic_lifecycle(user_message: str, status: str = "") -> dict[str, str]:
    features = extract_features(user_message)
    session = (
        "high_impact"
        if features["high_impact"]
        else ("coding" if features["coding"] else ("research" if features["research"] else "chat"))
    )
    quality = (
        "likely_failed"
        if status.lower() in {"error", "failed"}
        else ("approval_pending" if status.lower() == "approval" else "complete")
    )
    return {"session": session, "quality": quality}


__all__ = ["QUESTIONS", "SCHEMA", "deterministic_lifecycle", "evaluate_lifecycle"]
