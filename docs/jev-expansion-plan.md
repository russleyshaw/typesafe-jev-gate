# Jev Expansion Plan for Hermes

## Goal

Use Jev (`cheap_model`, `~typesafe/jev-latest`) more broadly as a fast, typed decision layer inside Hermes without turning it into the conversational model or an authorization bypass.

## Current baseline

- Plugin version: `0.4.0`; enabled in the active Hermes profile.
- Transport: OpenRouter Decisions API at `https://openrouter.ai/api/alpha/decisions`.
- Existing decisions:
  - `pre_tool_call`: redacted risk, secret-egress, prompt-injection, reversibility, paid-tool, repetition, and side-effect checks.
  - `pre_llm_call`: advisory route hint for some long or multi-step requests.
- Existing safeguards:
  - Hermes hardline blocks and normal approval remain authoritative.
  - Unavailable, malformed, or uncertain Jev responses escalate to Hermes approval.
  - Inputs are redacted and bounded; decisions are cached briefly; metadata-only audit records are written.
- Important constraint: Jev is a System One decision model, not a normal chat-completion model. Do not configure it as the main model or blindly point every Hermes auxiliary slot at it. Use the Decisions API and typed choices/scores for decision-shaped work.

## Priority roadmap

### P0 — Make the current gate reliable and measurable

1. **Centralize typed schemas and decision parsing.**
   - Give every decision a versioned schema name/version and explicit allowed choices.
   - Reject unknown choices, missing required answers, out-of-range scores, and stale response shapes.
   - Keep the current fail-closed behavior: uncertain results become Hermes approval, never allow.
2. **Add decision budgets and latency controls.**
   - Separate per-turn Jev call budget from side-effect budget.
   - Keep a short timeout for pre-tool checks; cache only deterministic, redacted fingerprints.
   - Add bounded negative caching for repeated unavailable responses to avoid retry storms.
3. **Improve telemetry.**
   - Record decision type, schema version, route, latency bucket, cache hit, outcome, and fallback reason.
   - Never record raw prompts, tool arguments, API keys, or decision payloads.
4. **Add contract tests.**
   - Test malformed answers, unknown choices, timeout/HTTP errors, cache isolation, redaction regressions, and hook compatibility against the documented Hermes hook signatures.

**Exit criteria:** no Jev response can produce an unvalidated allow path; p95 added pre-tool latency is measured; all failure modes are covered by tests.

### P1 — Expand routing decisions in the plugin

1. **Replace marker-only route activation with a bounded request-feature extractor.**
   - Derive local features such as estimated complexity, tool likelihood, ambiguity, coding/research indicators, and requested output type.
   - Send only the bounded/redacted user message plus features to Jev.
2. **Use a typed route contract.**
   - Choices: `answer_directly`, `cheap_model`, `agent`, `deep_agent`, `clarify`.
   - Treat the result as an advisory hint consumed by Hermes routing, not as a model switch or approval.
   - If the hook cannot affect routing in the current runtime, retain the hint as audit/context metadata rather than injecting noisy text into the user-facing prompt.
3. **Add route confidence and abstention.**
   - Prefer `clarify` or current Hermes behavior when confidence is low, the request is ambiguous, or Jev disagrees with deterministic safety rules.
   - Do not route coding/debugging, destructive actions, credential use, or high-impact external changes to a cheap conversational model solely because Jev says `cheap_model`.
4. **Evaluate routing against a labeled corpus.**
   - Build a small redacted set from real request classes and synthetic edge cases.
   - Measure false-cheap rate, unnecessary-deep-agent rate, latency, and estimated cost savings.

**Exit criteria:** route hints are advisory, validated, observable, and demonstrably reduce cost/latency without increasing unsafe or low-quality routing.

### P1 — Add typed preflight decisions for expensive or high-volume operations

Extend the current `pre_tool_call` path with narrow decision contracts rather than one increasingly broad risk prompt:

- **Tool eligibility:** `run`, `ask_approval`, or `block` for paid/external tools.
- **External-data boundary:** whether the call is allowed to send the supplied data outside the machine.
- **Retry decision:** `retry_same`, `retry_simplified`, `escalate`, or `stop` after transient tool/provider failures.
- **Tool-call batching:** `single`, `parallel_safe`, or `sequential_required` for independent read-only calls.
- **Approval explanation category:** a stable typed reason code that Hermes can render to the user.

These decisions must remain advisory or approval-escalating unless the policy is a deterministic, explicitly reviewed hard block. Preserve Hermes's existing interactive approval and hardline checks.

**Exit criteria:** each contract has a narrow schema, a deterministic fallback, tests for disagreement with Hermes policy, and audit metrics.

### P2 — Use Jev for background and lifecycle decisions

Candidate plugin integrations, in descending value:

1. **Session/turn classification:** classify simple chat, research, coding, automation, or high-impact work for analytics and default policy selection.
2. **Context hygiene trigger:** decide whether a large tool result is worth pruning, preserving, or sending to normal compression. Jev should not summarize content; Hermes's configured auxiliary compression model remains responsible for prose summaries.
3. **Skill/tool suggestion:** choose among already-eligible skill/tool categories. Never invent tool names or bypass tool availability.
4. **Post-turn quality signal:** typed labels such as `complete`, `needs_followup`, `likely_failed`, or `approval_pending` for telemetry and optional follow-up suggestions.
5. **Audit sampling:** decide which low-risk calls need deeper audit retention, with deterministic minimum sampling and privacy bounds.

Start with observation-only mode for each feature. Promote to advisory mode only after offline evaluation and a rollback switch.

## Recommended plugin architecture

- `decisions.py`: versioned schemas, validation, and typed result objects.
- `features.py`: local bounded feature extraction; no secrets or unbounded history.
- `policy.py`: decision-specific payload builders and deterministic fallback policies.
- `client.py`: transport, timeout, cache, retry/negative-cache behavior, and response size limits.
- `hooks.py`: thin Hermes adapters; no policy logic hidden in hook wiring.
- `audit.py`: privacy-preserving metrics and correlation IDs.
- `config.py`: feature flags, per-decision budgets, timeouts, and rollout modes.

Suggested rollout modes:

```yaml
jev:
  mode: observe       # observe | advise | enforce_narrowly
  route_hints: true
  tool_preflight: true
  retry_decisions: false
  max_decisions_per_turn: 4
```

`enforce_narrowly` must be limited to reviewed deterministic blocks such as confirmed secret egress or confirmed prompt injection. Risk scores alone should escalate to Hermes approval, not autonomously deny or allow.

## Safety and privacy constraints

- Redact keys by name and recognizable secret values before every request.
- Bound strings, lists, conversation history, and response size.
- Hash cache keys from redacted inputs; never cache on raw secrets.
- Treat user text, tool output, web content, and model output as untrusted data.
- Never allow Jev to approve password, payment, verification-code, irreversible, or destructive actions by itself.
- Keep plugin and Hermes approvals authoritative; plugin configuration must not use `allow_tool_override: true` for this gate.
- Provide an environment/config kill switch that disables network decisions and returns to Hermes's normal approval behavior.
- Keep audit logs metadata-only and define retention/rotation limits.

## Measurement plan

Track by decision type and rollout mode:

- Jev calls per turn, cache-hit rate, error/timeout rate, and p50/p95 latency.
- Advisory agreement with deterministic rules and eventual human approval outcomes.
- False-cheap routing, unnecessary escalation, and approval deflection rate.
- Estimated spend avoided versus Jev spend.
- User-visible interruption rate and tool-loop completion rate.
- Secret-egress/prompt-injection test detection rate.

Run in `observe` mode first, compare Jev recommendations with the existing Hermes outcome, then enable `advise` for a small percentage or selected profile. Keep a one-change rollback path.

## Implementation order

1. Add schema validation, decision types, metrics, and failure-mode tests.
2. Add feature flags and observe-only telemetry.
3. Expand route classification and evaluate it offline.
4. Add one preflight contract at a time, starting with retry decisions or paid-tool eligibility.
5. Add lifecycle/context decisions only after the first two stages show acceptable latency and privacy behavior.
6. Revisit native `ctx.llm.complete_structured()` only for prose/JSON side jobs. It is useful for ordinary auxiliary LLM work, but it does not replace the Jev Decisions API for System One typed decisions.

## Definition of done

- All new decisions have typed schemas, bounded/redacted inputs, explicit fallbacks, and tests.
- Jev outages never reduce Hermes safety.
- Routing is advisory and measurable; safety gates still fail closed into Hermes approval.
- The plugin can be disabled without changing normal Hermes behavior.
- A report from observe/advise rollout shows latency, reliability, quality, and cost impact before broader enablement.

## Implementation status — 0.4.0

The plugin now implements the roadmap contracts and local verification path:

- Typed validation covers tool safety, route planning, preflight, and lifecycle decisions.
- Request features, route abstention, offline routing evaluation, negative caching, privacy allowlisting, deterministic audit sampling, and p50/p95 telemetry are implemented.
- Tool eligibility, external-data boundary, retry, batching, and approval-category fields are accepted and enforced only as advisory/escalation decisions, except reviewed narrow blocks.
- Lifecycle decisions are available through `post_turn` when the host exposes `register_optional_hook`; deterministic local fallbacks remain available on Jev failure.
- The remaining operational step is deployment in `observe`/`advise` mode to collect real human-approval, completion-quality, interruption, and spend-impact measurements. Those measurements cannot be fabricated by an offline test run.

The repository's automated acceptance checks are the test suite, Ruff, and the offline routing corpus. Production rollout must retain the kill switch and review the resulting telemetry before enabling narrow enforcement.

## 0.4.0 verification commands

```bash
uv run pytest
uv run --with 'ruff>=0.16,<0.17' ruff check .
uv run python scripts/jev_report.py
```

Expected local test result at release: `18 passed` and Ruff reports `All checks passed!`.

### Rollout acceptance report

The offline corpus verifies deterministic route safety and is not a substitute for a live rollout. Before production enforcement, collect the metrics listed above from metadata-only audit logs and compare Jev recommendations with Hermes's eventual approval and completion outcomes.
