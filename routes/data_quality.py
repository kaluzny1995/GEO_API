"""Data quality metrics router."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from model.data_quality import DataQuality
from provider.supabase_postgres.supabase_postgres_data_quality_provider import SupabasePostgresDbDataQualityProvider

router = APIRouter()


def get_data_quality_provider() -> SupabasePostgresDbDataQualityProvider:
    """Return the data quality provider used by the endpoints (FastAPI dependency)."""
    return SupabasePostgresDbDataQualityProvider()


DataQualityProviderDep = Annotated[SupabasePostgresDbDataQualityProvider, Depends(get_data_quality_provider)]


@router.get("/data-quality/{table_name}", response_model=list[DataQuality], tags=["data-quality"])
async def get_data_quality(
    table_name: str,
    provider: DataQualityProviderDep,
) -> list[DataQuality]:
    """Return the overall quality snapshot (``file_date = "overall"``) for a table."""
    return await provider.get_data_quality(table_name)


@router.get("/data-quality/{table_name}/file-dates", response_model=list[DataQuality], tags=["data-quality"])
async def get_data_quality_for_file_dates(
    table_name: str,
    file_dates: Annotated[list[str], Query(min_length=1, description="Snapshot dates (YYYY-MM-DD).")],
    provider: DataQualityProviderDep,
) -> list[DataQuality]:
    """Return the quality metrics of several ``file_date`` snapshots for a table.

    Pass the dates as repeated (``?file_dates=2026-09-19&file_dates=2026-09-20``)
    or comma-separated (``?file_dates=2026-09-19,2026-09-20``) query parameters.
    """
    dates = [date.strip() for item in file_dates for date in item.split(",") if date.strip()]
    if not dates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one non-empty file_date is required.",
        )
    return await provider.get_data_quality_for_file_dates(table_name, dates)


@router.get("/data-quality/{table_name}/{file_date}", response_model=list[DataQuality], tags=["data-quality"])
async def get_data_quality_for_file_date(
    table_name: str,
    file_date: str,
    provider: DataQualityProviderDep,
) -> list[DataQuality]:
    """Return the quality metrics of one ``file_date`` for a table."""
    return await provider.get_data_quality(table_name, file_date)
