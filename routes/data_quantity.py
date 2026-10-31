"""Data quantity router — actual row counts of the tracked GEO tables."""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from model.data_quantity import OVERALL_FILE_DATE, TableCount
from provider.supabase_postgres.supabase_postgres_data_quantity_provider import (
    SupabasePostgresDbDataQuantityProvider,
)
from routes.logging_route import LoggingRoute
from util import HTTP_422_UNPROCESSABLE

router = APIRouter(route_class=LoggingRoute)

# A snapshot date (YYYY-MM-DD) or the whole-table aggregate sentinel.
FILE_DATE_PATTERN = r"^(?:overall|\d{4}-\d{2}-\d{2})$"


def get_data_quantity_provider() -> SupabasePostgresDbDataQuantityProvider:
    """Return the data quantity provider used by the endpoints (FastAPI dependency).

    Returns:
        A fresh :class:`SupabasePostgresDbDataQuantityProvider` (reuses the
        shared engine via ``get_provider()``).
    """
    return SupabasePostgresDbDataQuantityProvider()


# Dependency alias injected into every data-quantity endpoint.
DataQuantityProviderDep = Annotated[SupabasePostgresDbDataQuantityProvider, Depends(get_data_quantity_provider)]


@router.get("/data-quantity/dates", response_model=list[str], tags=["data-quantity"])
async def get_data_quantity_file_dates(provider: DataQuantityProviderDep) -> list[str]:
    """Return every snapshot date present in ``geo.union_etl``.

    The authoritative list for the data-quantity view: it comes from the table
    itself, so a snapshot can never be missing because a data-quality metric
    run lagged behind. The ``"overall"`` sentinel is appended last.

    Returns:
        The distinct ``file_date`` values in ascending order, then ``"overall"``.
    """
    return await provider.get_file_dates()


@router.get("/data-quantity/{file_date}", response_model=list[TableCount], tags=["data-quantity"])
async def get_data_quantity_for_file_date(
    file_date: Annotated[
        str,
        Path(
            pattern=FILE_DATE_PATTERN,
            description='Snapshot date (YYYY-MM-DD) or "overall" for the whole table.',
        ),
    ],
    provider: DataQuantityProviderDep,
) -> list[TableCount]:
    """Return the actual row count of every tracked table for one snapshot.

    Each count is a ``SELECT COUNT(*)`` against the table itself (``overall``
    counts every row), so the values always match the database rather than a
    possibly stale ``total_records`` metric in ``geo.data_quality``.

    Args:
        file_date: Snapshot date (``YYYY-MM-DD``) or ``"overall"``.

    Returns:
        One row per tracked table, in the configured table order.

    Raises:
        HTTPException: 422 when ``file_date`` is not ``"overall"`` or a real
            ISO calendar date (e.g. ``2026-13-01`` passes the path regex but is
            not a date).
    """
    if file_date != OVERALL_FILE_DATE:
        try:
            dt.date.fromisoformat(file_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail="file_date must be 'overall' or a valid YYYY-MM-DD date.",
            ) from exc
    return await provider.get_table_counts(file_date)
