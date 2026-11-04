"""Data source files router — CSV metadata published by the PySpark DATA_SOURCE_FILE job."""

from typing import Annotated

from fastapi import APIRouter, Depends

from model.data_source_file import DataSourceFileInfo, DataSourceFilesResponse
from provider.supabase_postgres.supabase_postgres_data_source_files_provider import (
    SupabasePostgresDbDataSourceFilesProvider,
)
from routes.logging_route import LoggingRoute

router = APIRouter(route_class=LoggingRoute)


def get_data_source_files_provider() -> SupabasePostgresDbDataSourceFilesProvider:
    """Return the provider used by the data-source-files endpoint.

    Returns:
        A fresh :class:`SupabasePostgresDbDataSourceFilesProvider` (reuses the
        shared engine via ``get_provider()``).
    """
    return SupabasePostgresDbDataSourceFilesProvider()


# Dependency alias injected into the data-source-files endpoint.
DataSourceFilesProviderDep = Annotated[
    SupabasePostgresDbDataSourceFilesProvider, Depends(get_data_source_files_provider)
]


@router.get("/data-source-files", response_model=DataSourceFilesResponse, tags=["data-source-files"])
async def get_data_source_files(provider: DataSourceFilesProviderDep) -> DataSourceFilesResponse:
    """Return source names and metadata of every published CSV snapshot.

    The file rows are written to ``geo.data_source_files`` and the source list
    to ``geo.data_source_sources`` by GEO_ETL's PySpark DATA_SOURCE_FILE job, so
    the API container does not need the GEO_Download data folder. Keeping the
    source registry separate means ``geo.data_source_files`` contains real CSV
    files only, while a source with no current files still appears in the
    dropdown.

    Returns:
        The configured pipeline start date, the latest snapshot date, sorted
        source names and metadata for every CSV file.
    """
    rows = await provider.get_files()
    source_rows = await provider.get_sources()
    files = [row for row in rows if row.file_name]
    snapshot_dates = sorted({row.snapshot_date for row in files if row.snapshot_date})
    pipeline_start_dates = sorted({row.pipeline_start_date for row in source_rows if row.pipeline_start_date})
    if not pipeline_start_dates:
        # Backwards compatibility for a deployment where the source table has
        # not been published yet: fall back to the file rows.
        pipeline_start_dates = sorted({row.pipeline_start_date for row in files if row.pipeline_start_date})

    source_names = sorted({row.source_name for row in source_rows})
    if not source_names:
        source_names = sorted({row.source_name for row in files})

    return DataSourceFilesResponse(
        start_date=pipeline_start_dates[0] if pipeline_start_dates else (snapshot_dates[0] if snapshot_dates else None),
        latest_date=snapshot_dates[-1] if snapshot_dates else None,
        sources=source_names,
        files=[
            DataSourceFileInfo(
                source_name=row.source_name,
                file_name=row.file_name,
                snapshot_date=row.snapshot_date,
                created_at=row.created_at,
                records=row.records,
                size_kb=row.size_kb,
            )
            for row in files
        ],
    )
