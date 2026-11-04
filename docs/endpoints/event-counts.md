← [Endpoints](../endpoints.md)

# Event count endpoints

Both endpoints aggregate the stacked event table `geo.union_etl` (the canonical 21 columns
documented in [GEO_ETL — Data tables](../../../GEO_ETL/docs/data-tables.md)) with
`SELECT … COUNT(*) … GROUP BY`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/event-counts/category` | Counts grouped by source, event taxonomy and danger rating |
| GET | `/event-counts/location` | Counts grouped by source, location and danger rating |

## Grouping

| Endpoint | Grouped by (→ response fields) | `count` field |
|----------|--------------------------------|---------------|
| `/event-counts/category` | `source_name`, `subsource_name`, `event_category`, `event_subcategory`, `danger_rating` | `COUNT(*)` of `geo.union_etl` rows in the group |
| `/event-counts/location` | `source_name`, `subsource_name`, `country_code`, `state_province`, `danger_rating` | `COUNT(*)` of `geo.union_etl` rows in the group |

Rows are ordered by the five grouping columns (NULLs last, as in PostgreSQL `ASC`); nullable
columns (`subsource_name`, `event_subcategory`, `state_province`, `danger_rating`) come back
as `null`. The severity column is named `danger_rating` because that is the `geo.union_etl`
column name — the shared scale `no_rating` / `none` / `low` / `medium` / `high` / `extreme`
is documented in [GEO_ETL's single-ETL job](../../../GEO_ETL/docs/etl_jobs/single-etl.md).

## `limit`

The optional `limit` query parameter (`int`, 1–10,000, default **10,000**) is applied to the
**number of groups returned**, not to rows before aggregation — each `count` is always the
full size of its group. The default returns every group today (about 150 for categories and
1,127 for locations); GEO_APP requests `?limit=10000` explicitly. The earlier default of 100
truncated the alphabetically-later sources, which is why `NIFC`, `OpenMeteo` and the `USGS_*`
sources were missing from the category/location views.

```bash
curl -sS "http://127.0.0.1:8000/event-counts/category?limit=10000"
curl -sS "http://127.0.0.1:8000/event-counts/location?limit=10000"
```

A `limit` outside 1–10,000 fails with a FastAPI/Pydantic 422 validation error.
