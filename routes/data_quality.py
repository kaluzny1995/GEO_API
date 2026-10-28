"""Data quality metrics router."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from model.data_quality import DataQuality
from provider.supabase_postgres.supabase_postgres_data_quality_provider import SupabasePostgresDbDataQualityProvider
from routes.logging_route import LoggingRoute

router = APIRouter(route_class=LoggingRoute)


def get_data_quality_provider() -> SupabasePostgresDbDataQualityProvider:
    """Return the data quality provider used by the endpoints (FastAPI dependency).

    Returns:
        A fresh :class:`SupabasePostgresDbDataQualityProvider` (reuses the shared
        engine via ``get_provider()``).
    """
    return SupabasePostgresDbDataQualityProvider()


# Dependency alias injected into every data-quality endpoint.
DataQualityProviderDep = Annotated[SupabasePostgresDbDataQualityProvider, Depends(get_data_quality_provider)]


@router.get("/data-quality/{table_name}", response_model=list[DataQuality], tags=["data-quality"])
async def get_data_quality(
    table_name: str,
    provider: DataQualityProviderDep,
) -> list[DataQuality]:
    """Return the overall quality snapshot (``file_date = "overall"``) for a table.

    Args:
        table_name: Measured table name.

    Returns:
        The metric rows ordered by ``metric``; empty when the table has no
        ``"overall"`` snapshot.
    """
    return await provider.get_data_quality(table_name)


@router.get("/data-quality/{table_name}/file-dates", response_model=list[DataQuality], tags=["data-quality"])
async def get_data_quality_for_file_dates(
    table_name: str,
    file_dates: Annotated[list[str], Query(min_length=1, max_length=100, description="Snapshot dates (YYYY-MM-DD).")],
    provider: DataQualityProviderDep,
) -> list[DataQuality]:
    """Return the quality metrics of several ``file_date`` snapshots for a table.

    Pass the dates as repeated (``?file_dates=2026-09-19&file_dates=2026-09-20``)
    or comma-separated (``?file_dates=2026-09-19,2026-09-20``) query parameters.

    Args:
        table_name: Measured table name.
        file_dates: Snapshot dates (``YYYY-MM-DD``), repeated and/or comma-separated.

    Returns:
        The metric rows of all requested snapshots ordered by ``file_date``
        then ``metric``.

    Raises:
        HTTPException: 422 when no non-empty date remains after normalization,
            or when more than 100 dates are requested (``max_length=100`` caps
            the raw parameters; the second guard also catches the dates that
            comma-separated parameters expand into).
    """
    dates = [date.strip() for item in file_dates for date in item.split(",") if date.strip()]
    if not dates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one non-empty file_date is required.",
        )
    if len(dates) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At most 100 file_dates may be requested.",
        )
    return await provider.get_data_quality_for_file_dates(table_name, dates)


@router.get("/data-quality/{table_name}/{file_date}", response_model=list[DataQuality], tags=["data-quality"])
async def get_data_quality_for_file_date(
    table_name: str,
    file_date: str,
    provider: DataQualityProviderDep,
) -> list[DataQuality]:
    """Return the quality metrics of one ``file_date`` for a table.

    Args:
        table_name: Measured table name.
        file_date: Snapshot date (``YYYY-MM-DD``).

    Returns:
        The metric rows ordered by ``metric``; empty for unknown dates.
    """
    return await provider.get_data_quality(table_name, file_date)
