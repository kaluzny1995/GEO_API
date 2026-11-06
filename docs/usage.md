← [README](../README.md)

# Usage

## Setup

```bash
# Create the conda environment (Python 3.11)
conda env create -f environment.yml

# Activate it
conda activate geo_api_311

# Configure Supabase credentials — do this once in GEO_E2E (see Configuration):
# ../GEO_E2E/setup.sh writes this project's ./.env with the five SUPABASE_DB_* values
../GEO_E2E/setup.sh

# Manual fallback only:
cp .env.example .env   # then fill in the values
```

Packages are resolved from conda-forge (geospatial binaries) with ruff, tox and mypy
installed via pip — see [`environment.yml`](../environment.yml) and
[Configuration](configuration.md).

## Run the API

```bash
conda activate geo_api_311

# Entry point (host/port/reload/log_level from config.json → app_run)
python run.py

# Or directly:
uvicorn main:app --host 127.0.0.1 --port 8000
```

Swagger UI: <http://127.0.0.1:8000/docs> — the OpenAPI schema is generated automatically.

## Quick checks

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/data-quality/tables
curl -sS http://127.0.0.1:8000/data-quality/usgs_earthquake/overall
curl -sS http://127.0.0.1:8000/data-quantity/dates
curl -sS http://127.0.0.1:8000/data-quantity/2026-10-26
curl -sS http://127.0.0.1:8000/data-source-files
curl -sS "http://127.0.0.1:8000/event-counts/category?limit=10000"
curl -sS "http://127.0.0.1:8000/event-counts/location?limit=10000"
```

See [Endpoints](endpoints.md) for the full contract, or the per-domain pages:

- [Data quality](endpoints/data-quality.md)
- [Data quantity](endpoints/data-quantity.md)
- [Data source files](endpoints/data-source-files.md)
- [Event counts](endpoints/event-counts.md)

If the API is unreachable or times out, GEO_APP shows the red API-down alert with a Retry
button; HTTP errors are shown as a plain error card. GEO_Visual is unaffected by API outages
because it reads Supabase views directly. The endpoint-level error contract is in
[Endpoints — Error responses](endpoints.md#error-responses).

## Docker

The `geo_fastapi` image is built by the GEO_E2E Compose stack. See [Docker](docker.md) for
the image contents, rebuild commands and the container environment.
