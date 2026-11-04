← [README](../README.md)

# Development and code quality

```bash
conda activate geo_api_311

ruff check .           # lint
ruff format --check .  # format check (tox -e format-fix to apply)
mypy                   # type check
pytest                 # tests — see Testing
```

## Tox environments

Run the same checks in isolated virtualenvs (like GEO_ETL):

```bash
tox                    # lint + py311 (default envlist)
tox -e lint            # ruff check
tox -e typecheck       # mypy
tox -e format          # ruff format --check
tox -e format-fix      # ruff format (writes the changes)
tox -e warnings        # tests with warnings-as-errors
```

`py311` runs the full pytest suite (120 tests) in an isolated virtualenv.

## Conventions

- Keep provider methods read-only; GEO_ETL owns the database tables.
- Add a new endpoint as a router module in `routes/`, an interface in `provider/db/` and a
  Supabase implementation in `provider/supabase_postgres/`.
- Use the shared provider and `LoggingRoute` patterns rather than adding ad-hoc logging or
  database access.
- Keep `TABLE_NAMES` in `model/data_quantity.py` in sync with GEO_APP's `src/config.js`.
- Update the matching page under `docs/endpoints/` when an endpoint contract changes.
