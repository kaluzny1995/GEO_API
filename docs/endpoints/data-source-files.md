← [Endpoints](../endpoints.md)

# Data source files endpoint

`GET /data-source-files` serves the CSV inventory published by GEO_ETL's
`DATA_SOURCE_FILE` job. The job runs on the Spark side, where `GEO_Download/data` is mounted,
and writes:

- `geo.data_source_sources` — one row per source folder (the dropdown's source list);
- `geo.data_source_files` — one row per real CSV file only.

The API only selects from those tables, so the API container never needs the data folder.

## Endpoint

| Method | Path | Description |
|--------|------|-------------|
| GET | `/data-source-files` | Source names, pipeline start date, latest snapshot date and file metadata |

## Response contract

```json
{
  "start_date": "2026-09-01",
  "latest_date": "2026-11-02",
  "sources": ["Avalanche_ORG", "EONET", "GDACS"],
  "files": [
    {
      "source_name": "EONET",
      "file_name": "eonet_events_2026-09-01.csv",
      "snapshot_date": "2026-09-01",
      "created_at": "2026-10-04T02:14:50Z",
      "records": 12,
      "size_kb": 0.7
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `start_date` | Earliest enabled source `start_date` from GEO_Download's `config.json` |
| `latest_date` | Latest snapshot date found across all file rows |
| `sources` | Source folder names, sorted alphabetically |
| `files[].source_name` | Source folder name |
| `files[].file_name` | CSV file name |
| `files[].snapshot_date` | `YYYY-MM-DD` parsed from the file name, or `null` |
| `files[].created_at` | Filesystem modification time as ISO-8601 UTC text |
| `files[].records` | Data rows excluding the header and blank lines |
| `files[].size_kb` | File size in 1024-byte kilobytes, one decimal |

`geo.data_source_files` contains real CSV rows only; the source list comes from
`geo.data_source_sources`, so a source with no current files still appears in `sources`
with an empty `files` list. Root-level lookup CSVs (for example `reverse_geocode.csv`) are
excluded by the publisher, and files dated today or later are skipped until they are part
of the finished daily inventory. A missing table or an empty result returns empty lists
rather than an error.

```bash
curl -sS http://127.0.0.1:8000/data-source-files
```

See [GEO_ETL — DATA_SOURCE_FILE job](../../../GEO_ETL/docs/etl_jobs/data-source-file.md) for the
HISTORICAL/INCREMENTAL publication rules and [GEO_APP — Data Source Files](../../../GEO_APP/README.md#features)
for the consumer view.
