# GEO_API

Python 3.11 REST API for sharing geographic data from the GEO pipeline.

## Overview

GEO_API is the data-sharing layer of the GIS data pipeline, sitting alongside [GEO_Download](../GEO_Download), [GEO_ETL](../GEO_ETL) and [GEO_E2E](../GEO_E2E). It serves the clean, analysis-ready datasets loaded into Supabase (PostgreSQL) by GEO_ETL through a FastAPI REST interface, so dashboards, notebooks and other services can consume geographic data over HTTP.

> Status: initial scaffold — repository and environment setup only; application code comes next.

## Features

- **FastAPI** — async REST API with automatic OpenAPI/Swagger documentation
- **Geospatial handling** — GeoPandas + Shapely for geometries, GeoJSON responses
- **Typed contracts** — Pydantic v2 request/response models
- **Database access** — SQLAlchemy over Supabase PostgreSQL
- **Dev tooling** — ruff (lint/format), mypy (type checking), tox (isolated checks)

## Tech Stack

| Component      | Technology                                    |
|----------------|-----------------------------------------------|
| Language       | Python 3.11                                   |
| Web framework  | FastAPI                                       |
| Server         | Uvicorn                                       |
| Validation     | Pydantic >= 2.0.0                             |
| DataFrames     | pandas >= 2.0                                 |
| Geospatial     | GeoPandas >= 0.14 (Shapely, pyproj, pyogrio)  |
| Database       | PostgreSQL (Supabase) via SQLAlchemy >= 2.0   |
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
```

Packages are resolved from conda-forge (geospatial binaries) with ruff, tox and mypy installed via pip — see [`environment.yml`](environment.yml).

## Project structure

```text
GEO_API/
├── environment.yml   # conda environment: geo_api_311 (Python 3.11)
├── README.md
└── .gitignore
```
