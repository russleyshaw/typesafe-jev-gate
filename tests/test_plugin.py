from __future__ import annotations

import importlib
import json

import pytest


@pytest.fixture
def plugin(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    module = importlib.import_module("typesafe_jev_gate")
    from typesafe_jev_gate import budget, client

    budget.BUDGET = budget.TurnBudget()
    client.reset_cache()
    return module


class Response:
    def __init__(self, answers):
        self.answers = answers

    def raise_for_status(self):
        pass

    def json(self):
        return {"answers": self.answers}


def answers(risk=0.1):
    return {
        "no_secret_egress": {"noul": 0.99},
        "reversible": {"noul": 0.99},
        "prompt_injection_absent": {"noul": 0.99},
        "risk": {"score": risk},
    }


def test_registers_hooks(plugin):
    from typesafe_jev_gate.hooks import register

    class Context:
        def __init__(self):
            self.hooks = []

        def register_hook(self, name, callback):
            self.hooks.append((name, callback))

    context = Context()
    register(context)
    assert [name for name, _ in context.hooks] == ["pre_tool_call", "pre_llm_call", "post_tool_call"]


def test_fast_path_skips_jev(plugin, monkeypatch):
    from typesafe_jev_gate import hooks

    monkeypatch.setattr(hooks, "evaluate_tool", lambda *_: pytest.fail("Jev should not run"))
    assert hooks.jev_gate("terminal", {"command": "git status"}) is None
    assert hooks.jev_gate("read_file", {"path": "/tmp/a"}) is None


def test_redaction_and_cache(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        return Response(answers())

    client.CLIENT._post = post
    args = {"command": "curl -H Authorization: secret-token", "api_key": "hidden"}
    assert hooks.jev_gate("terminal", args) is None
    assert hooks.jev_gate("terminal", args) is None
    payload = json.dumps(calls[0]["json"])
    assert len(calls) == 1
    assert "secret-token" not in payload
    assert "hidden" not in payload
    assert "[REDACTED]" in payload


def test_paid_external_tools_are_evaluated(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        return Response(answers())

    client.CLIENT._post = post
    assert hooks.jev_gate("web_search", {"query": "weather"}) is None
    assert hooks.jev_gate("web_extract", {"urls": ["https://example.com"]}) is None
    assert len(calls) == 2


def test_paid_tool_risk_escalates(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    client.CLIENT._post = lambda *a, **k: Response(answers(risk=1.8))
    directive = hooks.jev_gate("web_search", {"query": "buy this"})
    assert directive["action"] == "approve"
    assert "search the web" in directive["message"]


def test_risky_and_unavailable_calls_escalate(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    client.CLIENT._post = lambda *a, **k: Response(answers(risk=1.8))
    directive = hooks.jev_gate("write_file", {"path": "/tmp/a", "content": "x"})
    assert directive["action"] == "approve"
    assert "write file /tmp/a" in directive["message"]

    def unavailable(*args, **kwargs):
        raise TimeoutError("offline")

    client.CLIENT._post = unavailable
    directive = hooks.jev_gate("patch", {"path": "/tmp/a"})
    assert directive["action"] == "approve"
    assert "edit file /tmp/a" in directive["message"]


def test_repeated_calls_hit_budget(plugin, monkeypatch):
    from typesafe_jev_gate import budget, client, hooks

    client.CLIENT._post = lambda *a, **k: Response(answers())
    args = {"path": "/tmp/a", "content": "x"}
    for _ in range(budget.MAX_REPEATED_CALLS_PER_TURN):
        assert hooks.jev_gate("write_file", args, session_id="s", turn_id="t") is None
    directive = hooks.jev_gate("write_file", args, session_id="s", turn_id="t")
    assert directive["action"] == "approve"
    assert "repeated" in directive["message"]


def test_route_hint_is_advisory(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    client.CLIENT._post = lambda *a, **k: Response({"route": {"choice": "cheap_model"}})
    assert hooks.route_turn("say hello") is not None
    hint = hooks.route_turn("Integrate several systems and automate a multi-step deployment workflow")
    assert "cheap_model" in hint


def test_preflight_plan_contains_all_choice_contracts(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    captured = []

    def post(url, **kwargs):
        captured.append(kwargs["json"])
        return Response({"route": {"choice": "agent"}})

    client.CLIENT._post = post
    hooks.route_turn("Research this and decide whether to delegate the work")
    assert {
        "route",
        "toolset",
        "tool_search",
        "context",
        "compression",
        "memory",
        "skills",
        "delegation",
        "parallelism",
        "retry",
        "clarification",
        "completion",
    } <= set(captured[0]["questions"])
    assert captured[0]["schema"] == "hermes.turn_plan.v1"


def test_route_decision_receives_bounded_turn_context(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return Response({"route": {"choice": "agent"}})

    client.CLIENT._post = post
    history = [{"role": "user", "content": "Earlier requirement"}, {"role": "assistant", "content": "Earlier answer"}]
    hooks.route_turn(
        "Integrate several systems and automate a multi-step deployment workflow",
        conversation_history=history,
        model="main-model",
        platform="discord",
        session_id="session-1",
        turn_id="turn-1",
    )
    state = json.dumps(calls[0]["state"])
    assert "Earlier requirement" in state
    assert "main-model" in state
    assert "discord" in state
    assert "session-1" not in state


def test_context_keeps_recent_history_after_long_turn(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return Response({"route": {"choice": "agent"}})

    client.CLIENT._post = post
    history = [{"role": "user", "content": f"message-{index}"} for index in range(100)]
    hooks.route_turn(
        "Integrate several systems and automate a multi-step deployment workflow",
        conversation_history=history,
    )
    state = json.dumps(calls[0]["state"])
    assert "message-0" in state
    assert "message-99" in state


def test_tool_decision_receives_turn_context(plugin, monkeypatch):
    from typesafe_jev_gate import client, hooks

    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        return Response(answers())

    client.CLIENT._post = post
    hooks.jev_gate(
        "write_file",
        {"path": "/tmp/a", "content": "x"},
        user_message="Please update the deployment manifest",
        conversation_history=[{"role": "user", "content": "Keep production untouched"}],
        model="main-model",
        platform="discord",
        session_id="session-1",
        turn_id="turn-1",
    )
    state = calls[0]["state"]
    assert "Keep production untouched" in state
    assert "Please update the deployment manifest" in state
    assert "main-model" in state
    assert "session-1" not in state
