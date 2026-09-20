# Changelog

All notable changes to the TypeSafe Jev Gate plugin are documented here.

## [0.3.0] - 2026-09-20

### Added

- Added bounded, redacted runtime context assembly for Jev decisions.
- Added versioned typed decision contracts with validation for choices and scores.
- Added typed preflight planning for route, toolset, context, compression, memory, skills, delegation, and retry choices.
- Added an advisory decision brief for the main model.
- Added separate per-turn Jev, repetition, and side-effect budgets.
- Added broader preflight coverage for paid and external tools.
- Added metadata-only audit records for preflight decisions and fallback outcomes.

### Changed

- Expanded Jev decisions with bounded conversation, model, platform, user-message, tool-schema, and eligible-tool context.
- Kept Jev input budgeting independent from output-token reservation.
- Preserved fail-closed behavior: unavailable, malformed, or uncertain decisions escalate to Hermes approval.
- Updated documentation and tests for the expanded policy and preflight behavior.

### Status

- Published as an experimental plugin release.
- The remaining roadmap in `docs/jev-expansion-plan.md` is not complete; routing evaluation, additional typed preflight contracts, lifecycle decisions, and rollout measurement remain future work.
