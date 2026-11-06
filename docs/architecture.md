← [README](../README.md)

# Architecture

GEO_API is the read-only HTTP layer between the GEO pipeline's Supabase database and its
clients (GEO_APP, notebooks, other services). The sibling GEO_Visual dashboard runs in the
`geo_streamlit` container and reads the same Supabase views directly (read-only SQL)
instead of through this API. It owns no data:
every endpoint selects from tables written by [GEO_ETL](../../GEO_ETL) or, for
`/data-source-files`, from the CSV metadata table published by GEO_ETL's `DATA_SOURCE_FILE`
job.

## Layers

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Routes | `routes/` | FastAPI endpoints, query validation, dependency injection and per-endpoint logging |
| Providers | `provider/` | Read-only interfaces plus the Supabase/PostgreSQL implementation |
| Models | `model/` | Pydantic response contracts and SQLModel table layouts |
| Configuration | `model/config/` | `config.json`, `metadata.json` and `.env` loading |
| Utilities | `util.py` | logger setup, chunking helper and the HTTP 422 compatibility constant |

The provider pattern mirrors [ETLReddit](https://github.com/kaluzny1995/ETLReddit): each
domain has a small interface in `provider/db/` and a Supabase implementation in
`provider/supabase_postgres/`. The async SQLAlchemy engine keeps database I/O off the
FastAPI event loop.

## Request flow

1. `main.py` creates the FastAPI app, adds CORS and registers the routers.
2. A router resolves its provider through a FastAPI dependency.
3. The provider compiles a SQLModel `select` and runs it through the shared
   `SupabasePostgresProvider`.
4. The route converts rows into the response model (or returns them directly when the
   SQLModel is also the response contract).
5. `LoggingRoute` writes the request start/finish, SQL and row count to the endpoint's own
   log file — see [Logging](logging.md).

`SupabaseServerDownError` is mapped to **503 Service Unavailable** by the global handler in
`error_handlers.py`. The connection pool is disposed on shutdown through the FastAPI lifespan.

## Project structure

```text
GEO_API/
├── model/
│   ├── config/                    # app metadata, run, CORS and Supabase configs
│   │   ├── app_metadata_config.py # metadata.json → FastAPI kwargs
│   │   ├── app_run_config.py      # config.json → uvicorn kwargs
│   │   ├── cors_middleware_config.py
│   │   └── supabase_config.py     # .env → asyncpg URL
│   ├── data_quality.py            # DataQuality — geo.data_quality row layout
│   ├── data_quantity.py           # TableCount + TABLE_NAMES — actual row counts
│   ├── data_source_file.py        # DataSourceFile / DataSourceSource — file + source rows
│   ├── event_count.py             # EventCategoryCount / EventLocationCount — count rows
│   ├── union_etl.py               # geo.union_etl — 21 canonical columns (Core table, no PK)
│   └── message.py                 # ResponseMessage
├── provider/
│   ├── db/
│   │   ├── i_db_data_quality_provider.py  # read-only data quality interface
│   │   ├── i_db_data_quantity_provider.py # read-only row-count interface
│   │   ├── i_db_data_source_files_provider.py # read-only CSV metadata interface
│   │   ├── i_db_event_counts_provider.py  # read-only event counts interface
│   │   └── i_db_provider.py       # database provider interface (async)
│   └── supabase_postgres/
│       ├── supabase_postgres_data_quality_provider.py  # geo.data_quality reads
│       ├── supabase_postgres_data_quantity_provider.py # COUNT(*) over the tracked tables
│       ├── supabase_postgres_data_source_files_provider.py # geo.data_source_files reads
│       ├── supabase_postgres_event_counts_provider.py  # geo.union_etl GROUP BY counts
│       └── supabase_postgres_provider.py  # SQLModel + asyncpg provider, get_session
├── routes/
│   ├── data_quality.py            # GET /data-quality/...
│   ├── data_quantity.py           # GET /data-quantity/dates, /data-quantity/{file_date}
│   ├── data_source_files.py       # GET /data-source-files
│   ├── event_counts.py            # GET /event-counts/category, /event-counts/location
│   ├── logging_route.py           # LoggingRoute — per-endpoint log files
│   └── main.py                    # /, /hello, /health router
├── test/
│   ├── conftest.py                # autouse fixture: endpoint logs → tmp_path
│   ├── model/config/              # config tests (no network)
│   ├── provider/supabase_postgres/  # provider tests (base provider mocked)
│   ├── routes/                    # endpoint tests (DB mocked)
│   └── test_util.py               # util.py tests — logger idempotency, chunking
├── docs/                          # this documentation
├── main.py                        # FastAPI app (uvicorn main:app)
├── run.py                         # uvicorn entry point (config.json → app_run)
├── error_handlers.py              # SupabaseServerDownError → 503
├── error.py                       # SupabaseServerDownError
├── util.py                        # logger + batch helpers + HTTP_422_UNPROCESSABLE compat constant
├── metadata.json                  # FastAPI metadata (title, description, summary, version)
├── config.json                    # app_run + cors_middleware
├── environment.yml                # conda environment: geo_api_311 (Python 3.11)
├── pyproject.toml                 # ruff / pytest / mypy config
├── tox.ini                        # lint, format, typecheck, py311, warnings
├── .env.example                   # Supabase credentials template
├── README.md
└── .gitignore
```

## Memory characteristics

Every stage materializes its rows exactly once — DB fetch (`Result.all()`), row →
response-model conversion, JSON serialization — and keeps no duplicate copy between stages.
Measured with `tracemalloc` against the live schema (35,799 `geo.union_etl` rows, warm
process; repeated runs vary by a few percent):

| Endpoint | Rows out | Peak allocation |
|----------|----------|-----------------|
| `GET /event-counts/category` | all groups (~150) | ~0.45 MiB |
| `GET /event-counts/location` | all groups (~1,127) | ~1.7 MiB |
| `GET /data-quality/{table_name}` | 175 metrics | ~0.53 MiB |
| `GET /data-quality/tables` | 36 relations | <0.1 MiB |

The event-count rows above are the complete grouped results; the previous `?limit=100`
default truncated the alphabetically-later sources and the `?limit=1000` maximum still cut
`USGS_*` out of the location result. The endpoints now default to 10,000 groups and GEO_APP
requests `?limit=10000` — see [Event counts](endpoints/event-counts.md).

Three per-stage optimizations — their impact grows with data volume and process lifetime, so
it is invisible at today's sizes:

- **`run_select_statement`** returns `Result.all()` as-is. The previous `list(result.all())`
  kept two lists of the same rows alive for every query: +7 KiB on a 905-row result (~8 bytes
  per row → ~7.6 MiB on a 1M-row result).
- **`util.setup_logger`** is idempotent per `(logger name, log file)`: rebuilding a provider
  no longer stacks a second `FileHandler` — 100 rebuilds went from 100 handlers / 100 open
  files to 1 / 1 (and log lines are never duplicated).
- **`util.chunk_list_equal_size`** yields chunks lazily: a batch insert holds only the chunk
  being written — 35,799 rows at 1,000 per batch dropped from 282 KiB to 8 KiB of chunk lists.

Streaming (`yield_per` / server-side cursors) is deliberately **not** used: asyncpg buffers
the whole result on the wire anyway, FastAPI's `response_model` needs the full list, and the
aggregates return at most ~10³ rows. If raw `geo.union_etl` row endpoints are added later
(35,799 rows and growing), add pagination there instead.
