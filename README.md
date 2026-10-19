# GEO_API

Python 3.11 REST API for sharing geographic data from the GEO pipeline.

## Overview

GEO_API is the data-sharing layer of the GIS data pipeline, sitting alongside [GEO_Download](../GEO_Download), [GEO_ETL](../GEO_ETL) and [GEO_E2E](../GEO_E2E). It serves the clean, analysis-ready datasets loaded into Supabase (PostgreSQL) by GEO_ETL through a FastAPI REST interface, so dashboards, notebooks and other services can consume geographic data over HTTP.

> Status: data endpoints live — `GET /data-quality/...` serves GEO_ETL's `geo.data_quality` metrics and `GET /event-counts/...` serves aggregates over GEO_ETL's `geo.union_etl`; more dataset endpoints to come.

## Features

- **Runnable FastAPI app** — `run.py` entry point, Swagger UI at `/docs`, `/health` check, CORS
- **Data quality metrics** — read-only `GET /data-quality/{table_name}[/{file_date}]` over GEO_ETL's `geo.data_quality` (ETLReddit-style provider layer)
- **Event counts** — read-only `GET /event-counts/category` and `GET /event-counts/location`, `COUNT(*)` aggregates over GEO_ETL's `geo.union_etl` grouped by five columns
- **Supabase connector** — SQLModel + SQLAlchemy 2.0 async engine (asyncpg), credentials from `.env` like GEO_ETL, PgBouncer-safe prepared statements
- **Typed contracts** — Pydantic v2 request/response models (`DataQuality`, `EventCategoryCount`, `EventLocationCount`, `ResponseMessage`)
- **Dev tooling** — ruff (lint/format), mypy (type checking), tox (isolated checks: lint, typecheck, py311, warnings)

## Tech Stack

| Component      | Technology                                    |
|----------------|-----------------------------------------------|
| Language       | Python 3.11                                   |
| Web framework  | FastAPI                                       |
| Server         | Uvicorn                                       |
| Validation     | Pydantic >= 2.0.0                             |
| DataFrames     | pandas >= 2.0                                 |
| Geospatial     | GeoPandas >= 0.14 (Shapely, pyproj, pyogrio)  |
| Database       | PostgreSQL (Supabase) via SQLModel + SQLAlchemy 2.0 async |
| DB driver      | asyncpg >= 0.29                               |
| HTTP client    | httpx >= 0.27                                 |
| Testing        | pytest >= 7.0.0                               |
| Lint / format  | ruff >= 0.6                                   |
| Type checking  | mypy >= 1.10                                  |
| Check runner   | tox >= 4.0                                    |
| Environment    | Conda — `geo_api_311`                         |

## Prerequisites

- **Conda** — for environment management
- **Supabase credentials** — same project as GEO_ETL, provided via `.env` (never committed)

## Setup

```bash
# Create the conda environment (Python 3.11)
conda env create -f environment.yml

# Activate it
conda activate geo_api_311

# Configure Supabase credentials (same project/schema as GEO_ETL writes to)
cp .env.example .env   # then fill in the values
```

Packages are resolved from conda-forge (geospatial binaries) with ruff, tox and mypy installed via pip — see [`environment.yml`](environment.yml).

### Configuration

Supabase credentials are read from `.env` in the project root (see `.env.example`) — the same
five variables as GEO_ETL: `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`, `SUPABASE_DB_HOST`,
`SUPABASE_DB_PORT` (transaction pooler, `6543`), `SUPABASE_DB_NAME`. Environment variables
override the file. The connection URL enables `ssl=require` and PgBouncer-safe prepared
statements automatically.

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

## Run the API

```bash
conda activate geo_api_311

# Entry point (host/port/reload from config.json → app_run)
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
| GET      | `/data-quality/{table_name}/file-dates`  | Quality metrics of many snapshots — `?file_dates=...` (repeated or comma-separated) |
| GET      | `/event-counts/category`                 | `geo.union_etl` row counts grouped by source, event taxonomy and danger rating      |
| GET      | `/event-counts/location`                 | `geo.union_etl` row counts grouped by source, location and danger rating            |

Data quality rows come from `geo.data_quality` (written by GEO_ETL's DATA_QUALITY job — metric
families documented in [GEO_ETL docs](../GEO_ETL/docs/data-quality-metrics.md)). The endpoint is
read-only; an empty list means no metrics for that table/date.

Event counts aggregate the stacked event table `geo.union_etl` (the canonical 21 columns of
[GEO_ETL docs](../GEO_ETL/docs/data-tables.md)) with `SELECT … COUNT(*) … GROUP BY`; no filters
are applied, so the `count` values of either endpoint always sum to the full table size:

| Endpoint                  | Grouped by (→ response fields)                                                                           | `count` field                                   |
| ------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `/event-counts/category`  | `source_name`, `subsource_name`, `event_category`, `event_subcategory`, `danger_rating`                  | `COUNT(*)` of `geo.union_etl` rows in the group |
| `/event-counts/location`  | `source_name`, `subsource_name`, `country_code`, `state_province`, `danger_rating`                       | `COUNT(*)` of `geo.union_etl` rows in the group |

Rows are ordered by the five grouping columns (NULLs last, as in PostgreSQL `ASC`); nullable
columns (`subsource_name`, `event_subcategory`, `state_province`, `danger_rating`) come back as
`null`. The severity column is named `danger_rating` because that is the `geo.union_etl` column
name — the shared scale `no_rating` / `none` / `low` / `medium` / `high` / `extreme` documented
in [GEO_ETL's single-ETL job](../GEO_ETL/docs/etl_jobs/single-etl.md).

`SupabaseServerDownError` anywhere in a request is mapped to **503 Service Unavailable**
by the global handler in `error_handlers.py`. The engine's connection pool is disposed on
shutdown via the FastAPI lifespan (`dispose_provider`).

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
tox -e typecheck       # mypy
tox -e format          # format check
tox -e warnings        # tests with warnings-as-errors
```

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
│   ├── event_count.py             # EventCategoryCount / EventLocationCount — count rows
│   ├── union_etl.py               # geo.union_etl — 21 canonical columns (Core table, no PK)
│   └── message.py                 # ResponseMessage
├── provider/
│   ├── db/
│   │   ├── i_db_data_quality_provider.py  # read-only data quality interface
│   │   ├── i_db_event_counts_provider.py  # read-only event counts interface
│   │   └── i_db_provider.py       # database provider interface (async)
│   └── supabase_postgres/
│       ├── supabase_postgres_data_quality_provider.py  # geo.data_quality reads
│       ├── supabase_postgres_event_counts_provider.py  # geo.union_etl GROUP BY counts
│       └── supabase_postgres_provider.py  # SQLModel + asyncpg provider, get_session
├── routes/
│   ├── data_quality.py            # GET /data-quality/...
│   ├── event_counts.py            # GET /event-counts/category, /event-counts/location
│   └── main.py                    # /, /hello, /health router
├── test/
│   ├── model/config/              # config tests (no network)
│   ├── provider/supabase_postgres/  # provider tests (base provider mocked)
│   └── routes/                    # endpoint tests (DB mocked)
├── main.py                        # FastAPI app (uvicorn main:app)
├── run.py                         # uvicorn entry point (config.json → app_run)
├── error_handlers.py              # SupabaseServerDownError → 503
├── error.py                       # SupabaseServerDownError
├── util.py                        # logger + batch helpers
├── metadata.json                  # FastAPI metadata (title, description, version)
├── config.json                    # app_run + cors_middleware settings
├── environment.yml                # conda environment: geo_api_311 (Python 3.11)
├── pyproject.toml                 # ruff / pytest / mypy config
├── tox.ini                        # lint, format, typecheck, py311, warnings
├── .env.example                   # Supabase credentials template
├── README.md
└── .gitignore
```
