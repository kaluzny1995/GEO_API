# GEO_API

Python 3.11 REST API for sharing geographic data from the GEO pipeline.

## Overview

GEO_API is the data-sharing layer of the GIS data pipeline, sitting alongside
[GEO_Download](../GEO_Download), [GEO_ETL](../GEO_ETL), [GEO_E2E](../GEO_E2E),
[GEO_APP](../GEO_APP) and [GEO_Visual](../GEO_Visual). It serves the clean, analysis-ready
datasets loaded into Supabase (PostgreSQL) by GEO_ETL through a FastAPI REST interface, so
dashboards, notebooks and other services can consume geographic data over HTTP.

> Status: data endpoints live — `GET /data-quality/...` serves GEO_ETL's `geo.data_quality`
> metrics, `GET /data-quantity/...` serves actual `COUNT(*)` row counts,
> `GET /event-counts/...` serves aggregates over `geo.union_etl`, and
> `GET /data-source-files` serves the CSV inventory published by GEO_ETL's `DATA_SOURCE_FILE`
> job.

## Features

- **Runnable FastAPI app** — `run.py` entry point, Swagger UI at `/docs`, `/health` check, CORS
- **Data quality metrics** — read-only `/data-quality/...` over `geo.data_quality`, plus the
  authoritative table/view list for the dashboard dropdown — see
  [Data quality endpoints](docs/endpoints/data-quality.md)
- **Data quantity counts** — actual `COUNT(*)` of all 19 tracked tables per snapshot, plus
  snapshot discovery; always matches the tables, unlike a possibly stale metric — see
  [Data quantity endpoints](docs/endpoints/data-quantity.md)
- **Data source file metadata** — `geo.data_source_files` plus the `geo.data_source_sources`
  registry, published by GEO_ETL's PySpark `DATA_SOURCE_FILE` job — see
  [Data source files endpoint](docs/endpoints/data-source-files.md)
- **Event counts** — `COUNT(*)` aggregates over `geo.union_etl` grouped by source, taxonomy
  or location and danger rating — see [Event count endpoints](docs/endpoints/event-counts.md)
- **Supabase connector** — SQLModel + SQLAlchemy 2.0 async engine (asyncpg), credentials from
  `.env`, PgBouncer-safe prepared statements
- **Typed contracts** — Pydantic v2 response models (`DataQuality`, `TableCount`,
  `DataSourceFile`, `DataSourceFilesResponse`, `EventCategoryCount`, `EventLocationCount`,
  `ResponseMessage`)
- **Predictable memory** — one materialization per stage, no duplicate result copies, lazy
  batching, idempotent logging — see [Architecture — Memory characteristics](docs/architecture.md#memory-characteristics)
- **Per-endpoint logging** — one timestamped log file per endpoint with request timing, SQL
  and row counts — see [Logging](docs/logging.md)
- **Dev tooling** — ruff, mypy and tox — see [Development](docs/development.md)

## Tech Stack

| Component      | Technology                                    |
|----------------|-----------------------------------------------|
| Language       | Python 3.11                                   |
| Web framework  | FastAPI                                       |
| Server         | Uvicorn                                       |
| Validation     | Pydantic >= 2.0.0                             |
| Database       | PostgreSQL (Supabase) via SQLModel + SQLAlchemy 2.0 async |
| DB driver      | asyncpg >= 0.29                               |
| HTTP client    | httpx >= 0.27 (via Starlette's `TestClient` in tests only) |
| Testing        | pytest >= 7.0.0, pytest-asyncio >= 0.24       |
| Lint / format  | ruff >= 0.6                                   |
| Type checking  | mypy >= 1.10                                  |
| Check runner   | tox >= 4.0                                    |
| Environment    | Conda — `geo_api_311`                         |

> **Note:** `environment.yml` still pins `pandas >= 2.0` and `geopandas >= 0.14`, but **no
> file in this repo imports either** — they are inherited from the shared `GeographicData`
> conda stack, not used by this API. `python-multipart >= 0.0.9` is likewise unused today; it
> is only required if form-data endpoints are added later.

## Documentation

| Document | Contents |
|----------|----------|
| [Architecture](docs/architecture.md) | Layers, request flow, project structure and memory characteristics. |
| [Configuration](docs/configuration.md) | Supabase `.env`, `config.json`, `metadata.json` and database access. |
| [Usage](docs/usage.md) | Setup, running the API, Swagger and quick `curl` checks. |
| [Endpoints](docs/endpoints.md) | Endpoint index, liveness/health and shared error responses. |
| [Data quality endpoints](docs/endpoints/data-quality.md) | Table list, snapshots, date discovery and the `file-dates` batch. |
| [Data quantity endpoints](docs/endpoints/data-quantity.md) | Snapshot dates and actual `COUNT(*)` per tracked table. |
| [Data source files endpoint](docs/endpoints/data-source-files.md) | CSV inventory contract, source registry and date cutoff. |
| [Event count endpoints](docs/endpoints/event-counts.md) | Category/location grouping, `limit` and ordering. |
| [Docker](docs/docker.md) | `geo_fastapi` image contents, rebuild commands and ports. |
| [Logging](docs/logging.md) | Per-endpoint log files, SQL lines and tracebacks. |
| [Testing](docs/testing.md) | Running pytest, test layout and what is mocked. |
| [Memory leaks investigation 2026-11-23](docs/memory-leaks-investigation-2026-11-23.md) | Host vs container memory attribution, the 17–23 November growth and the API pool hardening. |
| [Memory leaks investigation 2026-11-24](docs/memory-leaks-investigation-2026-11-24.md) | Follow-up after the daily run: stable API container, desktop system-monitor growth. |
| [Development](docs/development.md) | Ruff, mypy and tox environments. |

## Prerequisites

- **Conda** — for environment management
- **Supabase credentials** — same project as GEO_ETL, provided via `.env` (never committed);
  their setup lives in **GEO_E2E**

## Quick start

```bash
# Create and activate the conda environment (Python 3.11)
conda env create -f environment.yml
conda activate geo_api_311

# Configure Supabase credentials once in GEO_E2E
../GEO_E2E/setup.sh

# Run the API (host/port/reload from config.json → app_run)
python run.py
```

Swagger UI: <http://127.0.0.1:8000/docs> — the OpenAPI schema is generated automatically.
For Docker, see [Docker](docs/docker.md); for all endpoint contracts, see
[Endpoints](docs/endpoints.md).

## Related Projects

GEO_API is one layer of the GIS data pipeline. The six projects sit as siblings under
`GeographicData/`:

- **[GEO_Download](../GEO_Download)** — fetches the raw data from public geospatial APIs into
  dated CSVs.
- **[GEO_ETL](../GEO_ETL)** — PySpark ETL that loads those CSVs into Supabase and writes the
  `geo.data_quality` / `geo.union_etl` tables this API reads, plus the `geo.data_source_files`
  inventory.
- **[GEO_E2E](../GEO_E2E)** — Airflow orchestrator that schedules the download and the ETL;
  its `./setup.sh` also writes this project's `.env` with the shared `SUPABASE_DB_*`
  credentials.
- **[GEO_APP](../GEO_APP)** — React dashboard that renders what this API serves.
- **[GEO_Visual](../GEO_Visual)** — Streamlit dashboard served by the `geo_streamlit`
  container in GEO_E2E; it reads the same Supabase views directly (read-only SQL) and
  does not go through this API.
