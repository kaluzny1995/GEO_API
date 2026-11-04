← [README](../README.md)

# Endpoints

All data endpoints are read-only and return JSON. The OpenAPI schema is available at
`/docs`; this page is the human-readable contract.

## Endpoint index

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Liveness message (`ResponseMessage`) |
| GET | `/hello` | Liveness message (`ResponseMessage`) |
| GET | `/health` | Verifies the Supabase Postgres connection — 200 or 503 |
| GET | `/data-quality/tables` | Tables/views available in `geo` — names for the dashboard dropdown |
| GET | `/data-quality/{table_name}` | Overall quality snapshot (`file_date = "overall"`) |
| GET | `/data-quality/{table_name}/dates` | Every snapshot date recorded for a table |
| GET | `/data-quality/{table_name}/file-dates` | Quality metrics of many snapshots — required `?file_dates=...`, max 100 |
| GET | `/data-quality/{table_name}/{file_date}` | Quality metrics of one `YYYY-MM-DD` snapshot |
| GET | `/data-quantity/dates` | Snapshot dates present in `geo.union_etl` (ascending, then `overall`) |
| GET | `/data-quantity/{file_date}` | Actual `COUNT(*)` of all 19 tracked tables for a snapshot or `overall` |
| GET | `/data-source-files` | CSV inventory published to `geo.data_source_files` by GEO_ETL |
| GET | `/event-counts/category` | `geo.union_etl` counts grouped by source, taxonomy and danger rating |
| GET | `/event-counts/location` | `geo.union_etl` counts grouped by source, location and danger rating |

Per-domain details:

- [Data quality](endpoints/data-quality.md)
- [Data quantity](endpoints/data-quantity.md)
- [Data source files](endpoints/data-source-files.md)
- [Event counts](endpoints/event-counts.md)

## Liveness and health

- `GET /` and `GET /hello` return a small `ResponseMessage` without touching the database.
- `GET /health` runs `SELECT 1` through the shared Supabase provider. It returns 200 when
  the database is reachable and 503 when it is not.

## Error responses

| Status | When | Body |
|--------|------|------|
| 422 | `GET /data-quality/{table_name}/file-dates` called with no `file_dates`, or only empty values | `"At least one non-empty file_date is required."` |
| 422 | `GET /data-quality/{table_name}/file-dates` with more than 100 dates | `"At most 100 file_dates may be requested."` |
| 422 | `GET /data-quantity/{file_date}` with a value that is not `overall` or a real `YYYY-MM-DD` date | `"file_date must be 'overall' or a valid YYYY-MM-DD date."` |
| 422 | `GET /event-counts/*` with `limit` outside 1–10,000 | FastAPI/Pydantic validation error |
| 503 | `SupabaseServerDownError` (connection/interface/OSError from asyncpg) anywhere in the request | `ResponseMessage` — `title`, `description`, `code` |

`SupabaseServerDownError` is raised by the shared provider and mapped by the global handler
in `error_handlers.py`. The engine's connection pool is disposed on shutdown via the FastAPI
lifespan (`dispose_provider`).
