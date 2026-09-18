# TypeSafe Jev Gate for Hermes

A Hermes plugin that uses TypeSafe Jev as an additional policy signal before side-effecting tool calls.

## Behavior

- Read-only tools and obvious safe terminal commands pass without a network call.
- Side-effecting tools are evaluated with redacted, bounded arguments.
- Repeated calls and excessive side effects in one turn are escalated to approval.
- Jev decisions are cached briefly to avoid duplicate spend.
- Paid tools receive stricter preflight treatment.
- Ambiguous multi-step requests receive an advisory route hint through `pre_llm_call`.
- Clear secret-egress or prompt-injection risks are blocked.
- Irreversible or uncertain calls are escalated to Hermes's normal approval gate.
- Jev outages fail closed into Hermes approval; they never silently allow a call.
- Audit logs contain metadata only at `$HERMES_HOME/logs/jev-gate.jsonl`.

Hermes hardline blocks and its existing authorization remain authoritative. Jev is not a replacement for either.

## Enable

1. Use the existing OpenRouter API key or create one at <https://openrouter.ai/keys>.
2. Store it as the secret `OPENROUTER_API_KEY` in the active Hermes profile.
The plugin calls OpenRouter's Decisions API at `https://openrouter.ai/api/alpha/decisions` using the `~typesafe/jev-latest` model slug. This is not the normal chat-completions endpoint.

3. Enable the plugin:

```bash
hermes plugins enable typesafe-jev-gate
```

4. Restart Hermes or its gateway.

The plugin does not make Jev the chat model. Jev is a typed decision model, not a conversational model.
