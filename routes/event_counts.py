"""Event count aggregation router."""

from typing import Annotated

from fastapi import APIRouter, Depends

from model.event_count import EventCategoryCount, EventLocationCount
from provider.supabase_postgres.supabase_postgres_event_counts_provider import (
    SupabasePostgresDbEventCountsProvider,
)
from routes.logging_route import LoggingRoute

router = APIRouter(route_class=LoggingRoute)


def get_event_counts_provider() -> SupabasePostgresDbEventCountsProvider:
    """Return the event counts provider used by the endpoints (FastAPI dependency).

    Returns:
        A fresh :class:`SupabasePostgresDbEventCountsProvider` (reuses the shared
        engine via ``get_provider()``).
    """
    return SupabasePostgresDbEventCountsProvider()


# Dependency alias injected into every event-counts endpoint.
EventCountsProviderDep = Annotated[SupabasePostgresDbEventCountsProvider, Depends(get_event_counts_provider)]


@router.get("/event-counts/category", response_model=list[EventCategoryCount], tags=["event-counts"])
async def get_event_counts_by_category(provider: EventCountsProviderDep) -> list[EventCategoryCount]:
    """Return ``geo.union_etl`` row counts grouped by event taxonomy.

    Every row of the stacked event table is grouped by ``source_name``,
    ``subsource_name``, ``event_category``, ``event_subcategory`` and
    ``danger_rating``; ``count`` is the number of rows in the group.

    Returns:
        One row per distinct group ordered by the five grouping columns;
        empty when the table has no rows.
    """
    return await provider.get_event_counts_by_category()


@router.get("/event-counts/location", response_model=list[EventLocationCount], tags=["event-counts"])
async def get_event_counts_by_location(provider: EventCountsProviderDep) -> list[EventLocationCount]:
    """Return ``geo.union_etl`` row counts grouped by location.

    Every row of the stacked event table is grouped by ``source_name``,
    ``subsource_name``, ``country_code``, ``state_province`` and
    ``danger_rating``; ``count`` is the number of rows in the group.

    Returns:
        One row per distinct group ordered by the five grouping columns;
        empty when the table has no rows.
    """
    return await provider.get_event_counts_by_location()
