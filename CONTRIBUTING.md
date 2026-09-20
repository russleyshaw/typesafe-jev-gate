# Contributing

## Development checks

Run these before opening a pull request:

```bash
uv run pytest
uv run --with 'ruff>=0.16,<0.17' ruff check .
uv run hermes plugins doctor . --ci
uv run python scripts/jev_report.py
```

Do not include API keys, personal data, raw prompts, tool arguments, or audit-log contents in commits or issues.

## Releases

The package version is defined in `pyproject.toml` and must match `plugin.yaml` and the changelog. Releases use an immutable annotated `vX.Y.Z` tag. A Hermes catalog entry pins the full commit SHA, so catalog updates require a reviewed SHA-bump pull request in the Hermes repository.

## Hermes catalog submissions

Catalog submissions are made to `NousResearch/hermes-agent`, not this repository. The catalog entry must declare the exact reviewed SHA and capabilities that match this plugin's manifest and registrations.
