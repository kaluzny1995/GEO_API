← [README](../README.md)

# Testing

The suite is unit-focused: every database call is mocked, so tests need neither a live
Supabase connection nor network access.

```bash
conda activate geo_api_311
pytest                 # full suite
pytest -q              # quiet
pytest test/routes     # one area
```

Current suite: **120 tests**.

## Test layout

| Path | Covers |
|------|--------|
| `test/model/config/` | `config.json`, `metadata.json` and Supabase URL/property loading |
| `test/provider/supabase_postgres/` | Provider SQL and row conversion, with the base provider mocked |
| `test/routes/` | Endpoint contracts, validation, dependency overrides and error handling |
| `test/test_util.py` | Logger idempotency and chunking helpers |

`test/conftest.py` redirects endpoint log files to a per-test temporary directory, so a test
run never litters `logs/`.

## What is mocked

- The shared `SupabasePostgresProvider` is replaced with an `AsyncMock`/`MagicMock` in
  provider and route tests.
- The FastAPI dependency (`get_*_provider`) is overridden per test module.
- Starlette's `TestClient` exercises the real routes and response models.

## Code quality

See [Development](development.md) for ruff, mypy and the tox environments.
