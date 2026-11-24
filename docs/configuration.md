← [README](../README.md)

# Configuration

## Supabase credentials (`.env`)

**Do the Supabase setup in [GEO_E2E](../../GEO_E2E) first**: run `../GEO_E2E/setup.sh`,
which detects the credentials (or re-uses an existing `GEO_E2E/.env`) and mirrors the five
`SUPABASE_DB_*` values into this project's gitignored `.env` — configure them once, there,
and never copy them between projects (full walkthrough in
[GEO_E2E — Supabase metadata DB](../../GEO_E2E/docs/configuration.md#supabase-metadata-db-env)).

Credentials are read from `.env` in the project root (see `.env.example`) — the same five
variables as GEO_ETL:

| Variable | Purpose |
|----------|---------|
| `SUPABASE_DB_USER` | Database user |
| `SUPABASE_DB_PASSWORD` | Database password |
| `SUPABASE_DB_HOST` | Supabase pooler hostname |
| `SUPABASE_DB_PORT` | Pooler port (transaction pooler, `6543`) |
| `SUPABASE_DB_NAME` | Database name (`postgres`) |

Environment variables override the file. `SupabaseConnectionConfig.get_connection_url()`
builds the asyncpg URL with `ssl=require` and `prepared_statement_cache_size=0` (the
PgBouncer-safe setting — see [Architecture](architecture.md)).

## `config.json`

`config.json` feeds three Pydantic models:

| Key | Model | Purpose |
| --- | ----- | ------- |
| `app_run.host` / `.port` / `.reload` | `AppRunConfig` (`model/config/app_run_config.py`) | uvicorn binding — used by `run.py` |
| `app_run.log_level` | `AppRunConfig` | uvicorn log level (`"info"`) |
| `database.pool_size` | `DatabaseConfig` (`model/config/database_config.py`) | pooled async connections kept by the shared engine (`5`) |
| `database.max_overflow` | `DatabaseConfig` | extra connections above `pool_size` (`5`) |
| `database.pool_recycle_seconds` | `DatabaseConfig` | recycle pooled connections after this many seconds (`300`) |
| `cors_middleware.allow_origins` | `CORSMiddlewareConfig` (`model/config/cors_middleware_config.py`) | allowed origins (`["*"]`) |
| `cors_middleware.allow_credentials` | `CORSMiddlewareConfig` | credentials flag (`false`) |
| `cors_middleware.allow_methods` | `CORSMiddlewareConfig` | allowed methods (`["*"]`) |
| `cors_middleware.allow_headers` | `CORSMiddlewareConfig` | allowed headers (`["*"]`) |

## `metadata.json`

`metadata.json` is parsed by `AppMetadataConfig` (`model/config/app_metadata_config.py`) into
FastAPI's OpenAPI kwargs: `title`, `description` (a **list** of strings joined into one),
`summary` and `version`.

## Database access

```python
from provider import get_provider, get_session  # get_session: FastAPI Depends
from sqlmodel import select

# One-off:
provider = get_provider()
await provider.connect()  # SELECT 1 health check
rows = await provider.run_select_statement(select(MyTable).where(...))


# In a FastAPI endpoint:
@app.get("/events")
async def list_events(session: AsyncSession = Depends(get_session)): ...
```

The provider pattern (interface + Supabase implementation) mirrors
[ETLReddit](https://github.com/kaluzny1995/ETLReddit), upgraded to an async engine so it
will not block FastAPI's event loop.
