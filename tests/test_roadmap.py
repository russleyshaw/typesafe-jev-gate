from __future__ import annotations

import json

import pytest


def test_extract_features_is_bounded_and_classifies_request():
    from typesafe_jev_gate.features import extract_features

    features = extract_features("Please debug the Python deployment and research the API, then write a report")
    assert features["coding"] is True
    assert features["research"] is True
    assert features["tool_likelihood"] == "high"
    assert features["requested_output"] == "report"
    assert len(json.dumps(features)) < 2000


def test_route_abstains_from_cheap_model_for_high_impact_request():
    from typesafe_jev_gate.features import route_is_safe

    assert route_is_safe("buy and place the order using my account", "cheap_model") is False
    assert route_is_safe("say hello", "cheap_model") is True


def test_decision_contracts_reject_unknown_narrow_choices():
    from typesafe_jev_gate.decisions import validate_preflight_answers

    with pytest.raises(ValueError):
        validate_preflight_answers({"eligibility": {"choice": "allow"}})
    assert validate_preflight_answers({"eligibility": {"choice": "run"}})["eligibility"]["choice"] == "run"


def test_negative_cache_prevents_retry_storms(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    from typesafe_jev_gate import client

    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        raise TimeoutError("offline")

    decision_client = client.DecisionClient(post=post)
    payload = {"schema": "test.v1", "state": "{}", "questions": {}}
    with pytest.raises(TimeoutError):
        decision_client.decide("same", payload)
    with pytest.raises(client.NegativeCacheError):
        decision_client.decide("same", payload)
    assert len(calls) == 1


def test_audit_drops_unapproved_payload_fields(tmp_path, monkeypatch):
    from typesafe_jev_gate.audit import audit

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    audit({"outcome": "evaluated", "tool": "write_file", "prompt": "secret", "arguments": {"password": "x"}})
    record = json.loads((tmp_path / "logs" / "jev-gate.jsonl").read_text())
    assert "prompt" not in record
    assert "arguments" not in record
    assert record["outcome"] == "evaluated"


def test_lifecycle_answers_are_typed():
    from typesafe_jev_gate.decisions import validate_lifecycle_answers

    answers = validate_lifecycle_answers(
        {
            "session": {"choice": "coding"},
            "context": {"choice": "preserve"},
            "skills": {"choice": "suggest"},
            "quality": {"choice": "complete"},
            "sampling": {"choice": "minimum"},
        }
    )
    assert answers["quality"]["choice"] == "complete"
