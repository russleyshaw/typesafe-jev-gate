"""Deterministic, bounded request features for advisory routing."""

from __future__ import annotations

import re
from typing import Any

from .redaction import redact

_WORDS = re.compile(r"\b[\w'-]+\b")
_CODING = re.compile(r"\b(code|coding|debug|bug|python|javascript|sql|api|deploy|repository|git|test)\b", re.I)
_RESEARCH = re.compile(r"\b(research|compare|sources|cite|citation|investigate|literature|web)\b", re.I)
_HIGH_IMPACT = re.compile(
    r"\b(buy|purchase|place|send|delete|transfer|publish|deploy|production|credential|password|payment|order)\b", re.I
)
_AMBIGUOUS = re.compile(r"\b(it|that|this|something|somehow|etc)\b", re.I)
_OUTPUTS = (
    ("report", re.compile(r"\b(report|memo|document|write-up)\b", re.I)),
    ("code", re.compile(r"\b(code|script|patch|implementation)\b", re.I)),
    ("list", re.compile(r"\b(list|steps|bullets)\b", re.I)),
)


def extract_features(user_message: str) -> dict[str, Any]:
    text = str(user_message or "")[:1200]
    words = _WORDS.findall(text)
    complexity = min(5, max(1, len(words) // 18 + text.count(" and ") + text.count(",")))
    tool_likelihood = (
        "high" if _HIGH_IMPACT.search(text) or _CODING.search(text) else ("medium" if _RESEARCH.search(text) else "low")
    )
    requested_output = next((name for name, pattern in _OUTPUTS if pattern.search(text)), "answer")
    return {
        "word_count": min(len(words), 240),
        "estimated_complexity": complexity,
        "tool_likelihood": tool_likelihood,
        "ambiguity": "high" if _AMBIGUOUS.search(text) and len(words) < 12 else "low",
        "coding": bool(_CODING.search(text)),
        "research": bool(_RESEARCH.search(text)),
        "high_impact": bool(_HIGH_IMPACT.search(text)),
        "requested_output": requested_output,
        "has_multiple_steps": bool(re.search(r"\b(then|after|first|finally|multi-step)\b", text, re.I)),
    }


def route_is_safe(features_or_message: Any, route: str) -> bool:
    features = (
        features_or_message if isinstance(features_or_message, dict) else extract_features(str(features_or_message))
    )
    if route == "cheap_model":
        return not (features.get("high_impact") or features.get("coding") or features.get("ambiguity") == "high")
    return True


def safe_features(user_message: str) -> dict[str, Any]:
    return {"features": extract_features(redact(str(user_message or "")))}


__all__ = ["extract_features", "route_is_safe", "safe_features"]
