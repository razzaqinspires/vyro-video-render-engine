# Contributing

1. Open an issue describing the change and its operational impact.
2. Create a focused branch from `main`.
3. Add or update tests for contract and behavior changes.
4. Run `ruff check .`, `ruff format --check .`, `pytest`, and `python -m compileall -q src tests`.
5. Update API, schema and migration documentation when behavior changes.
6. Submit a pull request with rationale, compatibility notes and test evidence.

Avoid committing rendered media, private datasets, credentials, generated caches, user data or copyrighted source assets without permission.
