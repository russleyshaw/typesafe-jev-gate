# Changelog

All notable changes to the TypeSafe Jev Gate plugin are documented here.

## [0.4.0] - 2026-09-20

### Added

- Added bounded deterministic request-feature extraction and route safety abstention.
- Added typed preflight choices for tool eligibility, external-data boundaries, retry strategy, batching, and approval reasons.
- Added typed lifecycle decisions for session classification, context hygiene, skill suggestions, completion quality, and audit sampling.
- Added optional `post_turn` lifecycle integration when the Hermes host exposes `register_optional_hook`.
- Added a negative provider-failure cache to prevent retry storms.
- Added privacy-safe p50/p95 telemetry aggregation from metadata-only audit records.
- Added a small redacted offline routing corpus and deterministic evaluation.

### Changed

- Added decision latency and schema metadata to audit records.
- Added deterministic fallbacks for unavailable lifecycle decisions.
- Expanded the documented architecture and development commands.
- Bumped the plugin and Python package version to `0.4.0`.

### Verification

- 18 tests pass.
- Ruff formatting and lint checks pass.
- The roadmap contracts are implemented without allowing Jev to override Hermes hardline blocks or normal approvals.
