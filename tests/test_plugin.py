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
    assert [name for name, _ in context.hooks] == [
        "pre_tool_call", "pre_llm_call", "transform_tool_result", "post_tool_call",
    ]


def test_pre_compaction_pass_removes_only_ephemeral_lines(plugin):
    from typesafe_jev_gate.hooks import compact_tool_result_hook

    result = "⠋ working\nProcessing...\nimportant result\n[####] 50%\n"
    assert compact_tool_result_hook(result) == "important result\n"
    preserved = "Processing 12 files\nreal output\n"
    assert compact_tool_result_hook(preserved) == preserved


def test_pre_compaction_pass_removes_aggressive_process_statuses(plugin):
    from typesafe_jev_gate.hooks import compact_tool_result_hook

    result = (
        "Running tests\n"
        "Process started: pid 42\n"
        "Process exited with code 0\n"
        "Exit code: 0\n"
        "✓ Done\n"
        "test_failure: expected 1, got 2\n"
    )
    assert compact_tool_result_hook(result) == "test_failure: expected 1, got 2\n"
    assert compact_tool_result_hook("Process exited with code 1\n") == "Process exited with code 1\n"


def test_pre_compaction_pass_leaves_non_text_results_untouched(plugin):
    from typesafe_jev_gate.hooks import compact_tool_result_hook

    value = {"output": "working..."}
    assert compact_tool_result_hook(value) is value


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
    assert hooks.route_turn("say hello") is None
    hint = hooks.route_turn("Integrate several systems and automate a multi-step deployment workflow")
    assert "cheap_model" in hint
