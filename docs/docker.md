← [README](../README.md)

# Docker

GEO_API is built as the **`geo_fastapi`** image by the Compose stack in
[GEO_E2E](../../GEO_E2E):

- Anaconda + the `geo_api_311` conda environment are inside the image.
- Runtime files only are copied to `/opt/geo/GEO_API` (no docs, tests, tox/mypy/lint
  tooling).
- `/opt/geo/GEO_API/.env` is written at container start from the Compose `environment:`
  section — no Supabase password is baked into the image.
- The API reads the CSV inventory from Supabase; it does **not** mount
  `GEO_Download/data`. GEO_ETL's PySpark `DATA_SOURCE_FILE` job runs on the Spark side and
  publishes the metadata to `geo.data_source_files`.
- The API listens on **<http://localhost:8000>** (`/docs` for Swagger, `/health` for the
  Supabase connectivity check).

Before starting the stack, provide the five `SUPABASE_DB_*` values in `GEO_E2E/.env` (see
[GEO_E2E — Dockerizing the solution](../../GEO_E2E/README.md#dockerizing-the-solution-recommended)).
Airflow credentials are not needed for this service.

```bash
cd ../GEO_E2E
./up.sh -d --build geo_fastapi   # preflight (six repos + Supabase .env), then compose up
```

After changing GEO_API, rebuild the image — the source is copied at build time, not
bind-mounted:

```bash
docker compose build geo_fastapi
./up.sh -d geo_fastapi
```

The React dashboard (`geo_react_app`) starts only after this service is healthy.
