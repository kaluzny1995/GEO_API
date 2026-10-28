"""Event count aggregation provider interface (read-only)."""

from abc import ABC, abstractmethod

from model.event_count import EventCategoryCount, EventLocationCount


class IDbEventCountsProvider(ABC):
    """Event count aggregation provider interface.

    Read-only by design: GEO_ETL owns the ``geo.union_etl`` table, the API
    only aggregates it — there are no create/update/delete methods.
    """

    @abstractmethod
    async def get_event_counts_by_category(self, limit: int = 100) -> list[EventCategoryCount]:
        """Return row counts grouped by source, event taxonomy and danger rating.

        Args:
            limit: Maximum number of groups returned (default 100).

        Returns:
            One row per distinct ``source_name`` / ``subsource_name`` /
            ``event_category`` / ``event_subcategory`` / ``danger_rating``
            combination, ordered by those five columns.
        """
        pass

    @abstractmethod
    async def get_event_counts_by_location(self, limit: int = 100) -> list[EventLocationCount]:
        """Return row counts grouped by source, location and danger rating.

        Args:
            limit: Maximum number of groups returned (default 100).

        Returns:
            One row per distinct ``source_name`` / ``subsource_name`` /
            ``country_code`` / ``state_province`` / ``danger_rating``
            combination, ordered by those five columns.
        """
        pass
