← [Endpoints](../endpoints.md)

# Data quality endpoints

Data quality rows come from `geo.data_quality`, written by GEO_ETL's `DATA_QUALITY` job.
The API is read-only; an empty list means no metrics for that table/date. Metric families
and rules are documented in [GEO_ETL — Data quality metrics](../../../GEO_ETL/docs/data-quality-metrics.md).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/data-quality/tables` | Tables/views available in `geo` for the dashboard dropdown |
| GET | `/data-quality/{table_name}` | Overall quality snapshot (`file_date = "overall"`) |
| GET | `/data-quality/{table_name}/dates` | Every snapshot date recorded for a table |
| GET | `/data-quality/{table_name}/file-dates` | Metrics for many snapshots — required `?file_dates=...` |
| GET | `/data-quality/{table_name}/{file_date}` | Metrics for one `YYYY-MM-DD` snapshot |

## Response contract

Each row is a `DataQuality` model (`model/data_quality.py`):

| Field | Type | Meaning |
|-------|------|---------|
| `table_name` | string | Measured table (e.g. `usgs_earthquake`) |
| `file_date` | string | `YYYY-MM-DD` snapshot or `overall` |
| `metric` | string | Metric name (e.g. `bad_row_pct`, `null_pct__mag`) |
| `value` | float | Metric value |
| `computed_at` | datetime | When the metric was computed |

The composite primary key is `(table_name, file_date, metric)`. The special
`file_date = "overall"` value carries the cross-date aggregate snapshot.

## Table discovery

`GET /data-quality/tables` introspects the `geo` schema and returns user-facing table and
view names in ascending order. The internal `data_quality` metrics table is excluded, so
newly added source/ETL tables and `*_vw` views appear without a frontend release.

## Snapshot dates

`GET /data-quality/{table_name}/dates` returns the distinct `file_date` values recorded for
that table in ascending order. `overall` sorts last because it is not a date. This is the
authoritative date list — clients do not need to probe a rolling window.

`GET /data-quality/{table_name}/file-dates` returns the metric rows for many snapshots. Pass
the dates either repeated or comma-separated:

```bash
curl -sS "http://127.0.0.1:8000/data-quality/usgs_earthquake/file-dates?file_dates=2026-10-25&file_dates=2026-10-26"
curl -sS "http://127.0.0.1:8000/data-quality/usgs_earthquake/file-dates?file_dates=2026-10-25,2026-10-26"
```

The endpoint accepts at most **100** dates per request. An empty request fails with 422
`"At least one non-empty file_date is required."`; more than 100 dates fails with 422
`"At most 100 file_dates may be requested."`.

## Overall and dated snapshots

- `GET /data-quality/{table_name}` is shorthand for the `overall` snapshot.
- `GET /data-quality/{table_name}/{file_date}` returns one dated snapshot; an unknown date
  returns an empty list.

```bash
curl -sS http://127.0.0.1:8000/data-quality/avalanche_org
curl -sS http://127.0.0.1:8000/data-quality/avalanche_org/2026-10-26
```
