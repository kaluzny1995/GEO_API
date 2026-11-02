"""Event count aggregation router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from model.event_count import EventCategoryCount, EventLocationCount
from provider.supabase_postgres.supabase_postgres_event_counts_provider import (
    SupabasePostgresDbEventCountsProvider,
)
from routes.logging_route import LoggingRoute

router = APIRouter(route_class=LoggingRoute)

# The grouped result set is small (currently ~150 category groups and ~1,100
# location groups) but the old default of 100 truncated sources alphabetically
# before USGS/NIFC/OpenMeteo. 10,000 keeps the response bounded while returning
# every group for the full pipeline.
DEFAULT_EVENT_COUNTS_LIMIT = 10_000
MAX_EVENT_COUNTS_LIMIT = 10_000


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
async def get_event_counts_by_category(
    provider: EventCountsProviderDep,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_EVENT_COUNTS_LIMIT,
            description="Maximum number of groups to return (default: all groups).",
        ),
    ] = DEFAULT_EVENT_COUNTS_LIMIT,
) -> list[EventCategoryCount]:
    """Return ``geo.union_etl`` row counts grouped by event taxonomy.

    Every row of the stacked event table is grouped by ``source_name``,
    ``subsource_name``, ``event_category``, ``event_subcategory`` and
    ``danger_rating``; ``count`` is the number of rows in the group.

    Args:
        limit: Maximum number of groups returned (1-10,000, default 10,000).

    Returns:
        One row per distinct group ordered by the five grouping columns;
        empty when the table has no rows.
    """
    return await provider.get_event_counts_by_category(limit=limit)


@router.get("/event-counts/location", response_model=list[EventLocationCount], tags=["event-counts"])
async def get_event_counts_by_location(
    provider: EventCountsProviderDep,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_EVENT_COUNTS_LIMIT,
            description="Maximum number of groups to return (default: all groups).",
        ),
    ] = DEFAULT_EVENT_COUNTS_LIMIT,
) -> list[EventLocationCount]:
    """Return ``geo.union_etl`` row counts grouped by location.

    Every row of the stacked event table is grouped by ``source_name``,
    ``subsource_name``, ``country_code``, ``state_province`` and
    ``danger_rating``; ``count`` is the number of rows in the group.

    Args:
        limit: Maximum number of groups returned (1-10,000, default 10,000).

    Returns:
        One row per distinct group ordered by the five grouping columns;
        empty when the table has no rows.
    """
    return await provider.get_event_counts_by_location(limit=limit)
