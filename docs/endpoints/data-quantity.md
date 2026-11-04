← [Endpoints](../endpoints.md)

# Data quantity endpoints

The data-quantity view needs the **database** row count of every tracked table for a
snapshot, not the `total_records` metric stored in `geo.data_quality` (that metric is
computed by GEO_ETL and can lag behind later backfills). The provider runs a `COUNT(*)` per
table, so the response always matches the table's current contents.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/data-quantity/dates` | Every snapshot date present in `geo.union_etl`, then `overall` |
| GET | `/data-quantity/{file_date}` | Actual `COUNT(*)` of all 19 tracked tables for a snapshot or `overall` |

## Response contract

Each row is a `TableCount` model (`model/data_quantity.py`):

| Field | Type | Meaning |
|-------|------|---------|
| `table_name` | string | Tracked table (e.g. `usgs_earthquake`, `usgs_earthquake_etl`, `union_etl`) |
| `file_date` | string | Snapshot date or `overall` |
| `count` | integer | Number of rows in that table for the snapshot |

For a dated snapshot the query adds `WHERE file_date = :file_date`; `overall` counts every
row. The response contains one row per tracked table in the configured `TABLE_NAMES` order.

## Snapshot discovery

`GET /data-quantity/dates` returns the distinct `file_date` values in `geo.union_etl` in
ascending order, followed by `overall`. The view uses this authoritative list instead of a
metric snapshot.

## Tracked tables

`TABLE_NAMES` contains the nine plain source tables, their nine `*_etl` tables and
`union_etl` — 19 tables total. It mirrors `TABLE_NAMES` in GEO_APP's `src/config.js`; keep
the two lists in sync when a dataset is added.

```bash
curl -sS http://127.0.0.1:8000/data-quantity/dates
curl -sS http://127.0.0.1:8000/data-quantity/2026-10-26
curl -sS http://127.0.0.1:8000/data-quantity/overall
```

A value that is not `overall` or a real `YYYY-MM-DD` date fails with 422
`"file_date must be 'overall' or a valid YYYY-MM-DD date."`.
