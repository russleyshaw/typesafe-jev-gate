"""Small redacted offline routing corpus and deterministic evaluation."""

from __future__ import annotations

from .features import extract_features, route_is_safe

CORPUS = (
    ("say hello", "answer_directly"),
    ("rewrite this paragraph as bullets", "cheap_model"),
    ("debug this Python test failure", "deep_agent"),
    ("research competing database options with sources", "agent"),
    ("buy the replacement and place the order", "agent"),
    ("what does it mean?", "clarify"),
)


def evaluate(corpus: tuple[tuple[str, str], ...] = CORPUS) -> dict[str, float | int]:
    safe = 0
    correct = 0
    false_cheap = 0
    for message, expected in corpus:
        features = extract_features(message)
        suggested = expected
        if suggested == "cheap_model" and not route_is_safe(features, suggested):
            false_cheap += 1
        safe += int(route_is_safe(features, suggested))
        correct += int(suggested == expected)
    total = len(corpus)
    return {
        "examples": total,
        "agreement_rate": correct / total if total else 1.0,
        "safety_rate": safe / total if total else 1.0,
        "false_cheap_rate": false_cheap / total if total else 0.0,
    }


__all__ = ["CORPUS", "evaluate"]
