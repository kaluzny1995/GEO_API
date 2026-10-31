# GEO_API

Python 3.11 REST API for sharing geographic data from the GEO pipeline.

## Overview

GEO_API is the data-sharing layer of the GIS data pipeline, sitting alongside [GEO_Download](../GEO_Download), [GEO_ETL](../GEO_ETL) and [GEO_E2E](../GEO_E2E). It serves the clean, analysis-ready datasets loaded into Supabase (PostgreSQL) by GEO_ETL through a FastAPI REST interface, so dashboards, notebooks and other services can consume geographic data over HTTP.

> Status: data endpoints live — `GET /data-quality/...` serves GEO_ETL's `geo.data_quality` metrics, `GET /data-quantity/...` serves actual `COUNT(*)` row counts, and `GET /event-counts/...` serves aggregates over GEO_ETL's `geo.union_etl`; more dataset endpoints to come.

## Features

- **Runnable FastAPI app** — `run.py` entry point, Swagger UI at `/docs`, `/health` check, CORS
- **Data quality metrics** — read-only `GET /data-quality/{table_name}[/{file_date}]` over GEO_ETL's `geo.data_quality` (ETLReddit-style provider layer)
- **Data quantity counts** — read-only `GET /data-quantity/{file_date}` returns the actual `COUNT(*)` of all 19 tracked tables, plus `GET /data-quantity/dates` for snapshot discovery; always matches the tables, unlike a possibly stale metric
- **Event counts** — read-only `GET /event-counts/category` and `GET /event-counts/location`, `COUNT(*)` aggregates over GEO_ETL's `geo.union_etl` grouped by five columns
- **Supabase connector** — SQLModel + SQLAlchemy 2.0 async engine (asyncpg), credentials from `.env` like GEO_ETL, PgBouncer-safe prepared statements
- **Typed contracts** — Pydantic v2 request/response models (`DataQuality`, `TableCount`, `EventCategoryCount`, `EventLocationCount`, `ResponseMessage`)
- **Predictable memory** — one materialization per stage (fetch → convert → serialize), no duplicate result copies, lazy batching, idempotent logging — profiled with `tracemalloc` (see [Memory characteristics](#memory-characteristics))
- **Per-endpoint logging** — one timestamped log file per endpoint (`logs/<tag>/<handler>_<ts>.log`, file + stdout), request start/finish with status and timing, executed SQL with row counts, tracebacks at the endpoint boundary (see [Logging](#logging))
- **Dev tooling** — ruff (lint/format), mypy (type checking), tox (isolated checks: lint, format, format-fix, typecheck, py311, warnings)

## Tech Stack

| Component      | Technology                                    |
|----------------|-----------------------------------------------|
| Language       | Python 3.11                                   |
| Web framework  | FastAPI                                       |
| Server         | Uvicorn                                       |
| Validation     | Pydantic >= 2.0.0                             |
| Database       | PostgreSQL (Supabase) via SQLModel + SQLAlchemy 2.0 async |
| DB driver      | asyncpg >= 0.29                               |
| HTTP client    | httpx >= 0.27 (via Starlette's `TestClient` in tests only — no source file imports it directly) |
| Testing        | pytest >= 7.0.0, pytest-asyncio >= 0.24       |
| Lint / format  | ruff >= 0.6                                   |
| Type checking  | mypy >= 1.10                                  |
| Check runner   | tox >= 4.0                                    |
| Environment    | Conda — `geo_api_311`                         |

> **Note:** `environment.yml` still pins `pandas >= 2.0` and `geopandas >= 0.14`, but **no file in
> this repo imports either** — they are inherited from the shared `GeographicData` conda stack
> (used by GEO_Download / GEO_ETL), not by this API, and are deliberately not listed in the Tech
> Stack above. Drop them from `environment.yml` too if you want a leaner `geo_api_311` env.
> `python-multipart >= 0.0.9` is likewise unused today; it is only required if form-data
> endpoints are added later.

## Prerequisites

- **Conda** — for environment management
- **Supabase credentials** — same project as GEO_ETL, provided via `.env` (never committed); their setup lives in **GEO_E2E**

## Setup

```bash
# Create the conda environment (Python 3.11)
conda env create -f environment.yml

# Activate it
conda activate geo_api_311

# Configure Supabase credentials — do this once in GEO_E2E (see "Configuration" below):
# ../GEO_E2E/setup.sh writes this project's ./.env with the five SUPABASE_DB_* values
../GEO_E2E/setup.sh
# Manual fallback only: cp .env.example .env   # then fill in the values
```

Packages are resolved from conda-forge (geospatial binaries) with ruff, tox and mypy installed via pip — see [`environment.yml`](environment.yml).

### Configuration

**Do the Supabase setup in [GEO_E2E](../GEO_E2E) first**: run `../GEO_E2E/setup.sh`, which
detects the credentials (or re-uses an existing `GEO_E2E/.env.local`) and mirrors the five
`SUPABASE_DB_*` values into this project's gitignored `.env` — you configure them once, there,
and never copy them between projects (full walkthrough in
[GEO_E2E — Supabase metadata DB](../GEO_E2E/docs/configuration.md#supabase-metadata-db-envlocal)).

Supabase credentials are read from `.env` in the project root (see `.env.example`) — the same
five variables as GEO_ETL: `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`, `SUPABASE_DB_HOST`,
`SUPABASE_DB_PORT` (transaction pooler, `6543`), `SUPABASE_DB_NAME`. Environment variables
override the file. The connection URL enables `ssl=require` and PgBouncer-safe prepared
statements automatically.

#### `config.json` / `metadata.json`

`config.json` feeds two pydantic models:

| Key | Model | Purpose |
| --- | ----- | ------- |
| `app_run.host` / `.port` / `.reload` | `AppRunConfig` (`model/config/app_run_config.py`) | uvicorn binding — used by `run.py` |
| `app_run.log_level` | `AppRunConfig` | uvicorn log level (`"info"`) |
| `cors_middleware.allow_origins` | `CORSMiddlewareConfig` (`model/config/cors_middleware_config.py`) | allowed origins (`["*"]`) |
| `cors_middleware.allow_credentials` | `CORSMiddlewareConfig` | credentials flag (`false`) |
| `cors_middleware.allow_methods` | `CORSMiddlewareConfig` | allowed methods (`["*"]`) |
| `cors_middleware.allow_headers` | `CORSMiddlewareConfig` | allowed headers (`["*"]`) |

`metadata.json` is parsed by `AppMetadataConfig` (`model/config/app_metadata_config.py`) into
FastAPI's OpenAPI kwargs: `title`, `description` (a **list** of strings joined into one),
`summary` and `version`.

### Database access

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

The provider pattern (interface + Supabase implementation) mirrors [ETLReddit](https://github.com/kaluzny1995/ETLReddit), upgraded to an async engine so it will not block FastAPI's event loop.

### Memory characteristics

Every stage materializes its rows exactly once — DB fetch (`Result.all()`), row → response-model
conversion, JSON serialization — and keeps no duplicate copy between stages. Measured with
`tracemalloc` against the live schema (35,799 `geo.union_etl` rows, warm process; repeated runs
vary by a few percent):

| Endpoint | Rows out | Peak allocation |
|----------|----------|-----------------|
| `GET /event-counts/category` | 124 groups | ~0.36 MiB |
| `GET /event-counts/location` | 905 groups | ~1.4 MiB |
| `GET /data-quality/{table_name}` | 175 metrics | ~0.53 MiB |

The two event-count rows above were measured with `?limit=1000` (the table holds 124 and 905
groups respectively); the default `?limit=100` returns at most 100 groups and so allocates
proportionally less.

Three per-stage optimizations — their impact grows with data volume and process lifetime, so it
is invisible at today's sizes:

- **`run_select_statement`** returns `Result.all()` as-is. The previous
  `list(result.all())` kept two lists of the same rows alive for every query: +7 KiB on a
  905-row result (~8 bytes per row → ~7.6 MiB on a 1M-row result).
- **`util.setup_logger`** is idempotent per `(logger name, log file)`: rebuilding a provider no
  longer stacks a second `FileHandler` — 100 rebuilds went from 100 handlers / 100 open files
  to 1 / 1 (and log lines are never duplicated).
- **`util.chunk_list_equal_size`** yields chunks lazily: a batch insert holds only the chunk
  being written — 35,799 rows at 1,000 per batch dropped from 282 KiB to 8 KiB of chunk lists.

Streaming (`yield_per` / server-side cursors) is deliberately **not** used: asyncpg buffers the
whole result on the wire anyway, FastAPI's `response_model` needs the full list, and the
aggregates return at most ~10³ rows. If raw `geo.union_etl` row endpoints are added later
(35,799 rows and growing), add pagination there instead.

## Run the API

```bash
conda activate geo_api_311

# Entry point (host/port/reload/log_level from config.json → app_run)
python run.py

# Or directly:
uvicorn main:app --host 127.0.0.1 --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs — OpenAPI schema is generated automatically.

### Endpoints

| Method   | Path                                     | Description                                                                         |
| -------- | ---------------------------------------- | ----------------------------------------------------------------------------------- |
| GET      | `/`                                      | Liveness message (`ResponseMessage`)                                                |
| GET      | `/hello`                                 | Liveness message (`ResponseMessage`)                                                |
| GET      | `/health`                                | Verifies the Supabase Postgres connection — 200 or 503                              |
| GET      | `/data-quality/{table_name}`             | Overall quality snapshot (`file_date = "overall"`) — list of metrics                |
| GET      | `/data-quality/{table_name}/{file_date}` | Quality metrics of one `YYYY-MM-DD` snapshot — list of metrics                      |
| GET      | `/data-quality/{table_name}/file-dates`  | Quality metrics of many snapshots — required `?file_dates=...` (repeated or comma-separated), max 100 |
| GET      | `/data-quantity/dates`                   | Snapshot dates present in `geo.union_etl` (ascending, then `overall`)               |
| GET      | `/data-quantity/{file_date}`             | Actual `COUNT(*)` of all 19 tracked tables for a `YYYY-MM-DD` snapshot or `overall` |
| GET      | `/event-counts/category`                 | `geo.union_etl` row counts grouped by source, event taxonomy and danger rating — optional `?limit=1..1000` (default 100) |
| GET      | `/event-counts/location`                 | `geo.union_etl` row counts grouped by source, location and danger rating — optional `?limit=1..1000` (default 100) |

Data quality rows come from `geo.data_quality` (written by GEO_ETL's DATA_QUALITY job — metric
families documented in [GEO_ETL docs](../GEO_ETL/docs/data-quality-metrics.md)). The endpoint is
read-only; an empty list means no metrics for that table/date.

Each data-quality row is a `DataQuality` model (`model/data_quality.py`) with the fields
`table_name`, `file_date`, `metric`, `value` (float) and `computed_at` (ISO-8601 datetime);
the composite primary key is `(table_name, file_date, metric)`. On the `/{table_name}`
overall snapshot the special `file_date` value `"overall"` carries the cross-date aggregate.

Event counts aggregate the stacked event table `geo.union_etl` (the canonical 21 columns of
[GEO_ETL docs](../GEO_ETL/docs/data-tables.md)) with `SELECT … COUNT(*) … GROUP BY`. The only
filter is the optional `limit` query parameter (`int`, 1–1000, default **100**) applied to the
*number of groups returned* — it does not filter rows before aggregation, so each `count` is
always the full size of its group. With the default `limit` the groups are truncated to the
first 100 (by the ordering below), so the returned `count` values do **not** sum to the table
size unless you pass `?limit=1000` or the group count is under the limit:

| Endpoint                  | Grouped by (→ response fields)                                                                           | `count` field                                   |
| ------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `/event-counts/category`  | `source_name`, `subsource_name`, `event_category`, `event_subcategory`, `danger_rating`                  | `COUNT(*)` of `geo.union_etl` rows in the group |
| `/event-counts/location`  | `source_name`, `subsource_name`, `country_code`, `state_province`, `danger_rating`                       | `COUNT(*)` of `geo.union_etl` rows in the group |

Rows are ordered by the five grouping columns (NULLs last, as in PostgreSQL `ASC`); nullable
columns (`subsource_name`, `event_subcategory`, `state_province`, `danger_rating`) come back as
`null`. The severity column is named `danger_rating` because that is the `geo.union_etl` column
name — the shared scale `no_rating` / `none` / `low` / `medium` / `high` / `extreme` documented
in [GEO_ETL's single-ETL job](../GEO_ETL/docs/etl_jobs/single-etl.md).

Data-quantity counts are plain `SELECT COUNT(*)` queries against each tracked table
(`model/data_quantity.py` → `TABLE_NAMES`). For a dated snapshot the query adds
`WHERE file_date = :file_date`; `overall` counts every row. The response is one
`TableCount` row per table (`table_name`, `file_date`, `count`). The endpoint reads the
tables themselves, so it stays correct even when GEO_ETL's `data_quality.total_records`
metric lags behind a later backfill. `GET /data-quantity/dates` returns the distinct
`file_date` values in `geo.union_etl` followed by `overall`, so the view never depends on
a metric snapshot to discover dates. `TABLE_NAMES` mirrors `TABLE_NAMES` in GEO_APP's
`src/config.js` — keep the two lists in sync when a dataset is added.

`SupabaseServerDownError` anywhere in a request is mapped to **503 Service Unavailable**
by the global handler in `error_handlers.py`. The engine's connection pool is disposed on
shutdown via the FastAPI lifespan (`dispose_provider`).

### Error responses

| Status | When | Body |
| ------ | ---- | ---- |
| 422 | `GET /data-quality/{table_name}/file-dates` called with no `file_dates`, or only empty values | `"At least one non-empty file_date is required."` |
| 422 | `GET /data-quality/{table_name}/file-dates` with more than 100 dates | `"At most 100 file_dates may be requested."` |
| 422 | `GET /data-quantity/{file_date}` with a value that is not `overall` or a real `YYYY-MM-DD` date | `"file_date must be 'overall' or a valid YYYY-MM-DD date."` |
| 422 | `GET /event-counts/*` with `limit` outside 1–1000 | FastAPI/pydantic validation error |
| 503 | `SupabaseServerDownError` (connection/interface/OSError from asyncpg) anywhere in the request | `ResponseMessage` — `title`, `description`, `code` |

### Logging

Every endpoint writes to its own log file, following the GEO_ETL / GEO_Download conventions
(`%(asctime)s %(levelname)s %(message)s`, file + stdout mirror via `util.setup_logger`):

- **Path:** `logs/<tag>/<handler>_<first-request timestamp>.log` — e.g.
  `logs/event_counts/get_event_counts_by_category_2026-10-20T20:08:34.334520.log`, where the
  directory is the router tag (`main`, `data_quality`, `event_counts`).
- **One file per endpoint per application run**, created lazily on the endpoint's first request
  and appended to for every subsequent request — no empty files.
- **Content:** a start line and a finish line per request with status code and elapsed time;
  unhandled errors are logged with a full traceback at the endpoint boundary and re-raised (so
  the global handler can still map them, e.g. `SupabaseServerDownError` → 503); client errors
  (4xx) are logged as warnings without a traceback.
- **Database activity** (endpoints that query Supabase): each successful query adds
  `Connected to Supabase Postgres`, `Executing SQL: <compiled statement> | params={...}` and
  `Returned N records` between the start and finish lines. The Supabase provider logs through
  the calling endpoint's logger (published via a context variable, `util.endpoint_logger`), so
  the exact statement and row count of every query land in the endpoint's own file; outside a
  request the provider falls back to its module logger.
- **Namespaced, non-propagating loggers** (`geo_api.<handler>`): records never double-emit
  through the root logger, and unrelated records (e.g. httpx access lines) never pollute an
  endpoint file.
- The Supabase provider creates **no log file of its own** — its module logger is handler-less;
  connection failures surface in the calling endpoint's log file via the boundary traceback.
- Implemented by `routes/logging_route.py` (`LoggingRoute`, an `APIRoute` subclass): every
  router created with `APIRouter(route_class=LoggingRoute)` is covered automatically, including
  endpoints added later.

Example — the full life of one request in `logs/event_counts/get_event_counts_by_category_<ts>.log`:

```text
2026-10-20 20:08:34,335 INFO GET /event-counts/category started
2026-10-20 20:08:34,338 INFO Connected to Supabase Postgres
2026-10-20 20:08:34,339 INFO Executing SQL: SELECT geo.union_etl.source_name, … count(*) AS count FROM geo.union_etl GROUP BY … ORDER BY … LIMIT 100
2026-10-20 20:08:35,093 INFO Returned 100 records
2026-10-20 20:08:35,094 INFO GET /event-counts/category finished with 200 in 759.3 ms
```

## Testing & code quality

```bash
pytest                 # unit tests (no network — DB is mocked)
ruff check .           # lint
ruff format --check .  # format check (tox -e format-fix to apply)
mypy                   # type check
```

Or run everything in isolated environments (like GEO_ETL):

```bash
tox                    # lint + py311 (default envlist)
tox -e lint            # ruff check
tox -e typecheck       # mypy
tox -e format          # ruff format --check
tox -e format-fix      # ruff format (writes the changes)
tox -e warnings        # tests with warnings-as-errors
```

`py311` runs the full pytest suite (109 tests) in an isolated virtualenv.

## Related Projects

GEO_API is one layer of the GIS data pipeline. The five projects sit as siblings under `GeographicData/`:

- **[GEO_Download](../GEO_Download)** — fetches the raw data from public geospatial APIs into dated CSVs.
- **[GEO_ETL](../GEO_ETL)** — PySpark ETL that loads those CSVs into Supabase and writes the `geo.data_quality` / `geo.union_etl` tables this API reads.
- **[GEO_E2E](../GEO_E2E)** — Airflow orchestrator that schedules the download and the ETL; its `./setup.sh` also writes this project's `.env` with the shared `SUPABASE_DB_*` credentials.
- **[GEO_APP](../GEO_APP)** — React dashboard that renders what this API serves.

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
│   ├── event_count.py             # EventCategoryCount / EventLocationCount — count rows
│   ├── union_etl.py               # geo.union_etl — 21 canonical columns (Core table, no PK)
│   └── message.py                 # ResponseMessage
├── provider/
│   ├── db/
│   │   ├── i_db_data_quality_provider.py  # read-only data quality interface
│   │   ├── i_db_data_quantity_provider.py # read-only row-count interface
│   │   ├── i_db_event_counts_provider.py  # read-only event counts interface
│   │   └── i_db_provider.py       # database provider interface (async)
│   └── supabase_postgres/
│       ├── supabase_postgres_data_quality_provider.py  # geo.data_quality reads
│       ├── supabase_postgres_data_quantity_provider.py # COUNT(*) over the tracked tables
│       ├── supabase_postgres_event_counts_provider.py  # geo.union_etl GROUP BY counts
│       └── supabase_postgres_provider.py  # SQLModel + asyncpg provider, get_session
├── routes/
│   ├── data_quality.py            # GET /data-quality/...
│   ├── data_quantity.py           # GET /data-quantity/dates, /data-quantity/{file_date}
│   ├── event_counts.py            # GET /event-counts/category, /event-counts/location
│   ├── logging_route.py           # LoggingRoute — per-endpoint log files
│   └── main.py                    # /, /hello, /health router
├── test/
│   ├── conftest.py                # autouse fixture: endpoint logs → tmp_path
│   ├── model/config/              # config tests (no network)
│   ├── provider/supabase_postgres/  # provider tests (base provider mocked)
│   ├── routes/                    # endpoint tests (DB mocked)
│   └── test_util.py               # util.py tests — logger idempotency, chunking
├── main.py                        # FastAPI app (uvicorn main:app)
├── run.py                         # uvicorn entry point (config.json → app_run)
├── error_handlers.py              # SupabaseServerDownError → 503
├── error.py                       # SupabaseServerDownError
├── util.py                        # logger + batch helpers + HTTP_422_UNPROCESSABLE compat constant
├── metadata.json                  # FastAPI metadata (title, description, summary, version)
├── config.json                    # app_run (host, port, reload, log_level) + cors_middleware (allow_origins, allow_credentials, allow_methods, allow_headers)
├── environment.yml                # conda environment: geo_api_311 (Python 3.11)
├── pyproject.toml                 # ruff / pytest / mypy config
├── tox.ini                        # lint, format, typecheck, py311, warnings
├── .env.example                   # Supabase credentials template
├── README.md
└── .gitignore
```
