"""Tests for the Supabase Postgres event counts provider (base provider mocked)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from model.event_count import EventCategoryCount, EventLocationCount
from provider.supabase_postgres.supabase_postgres_event_counts_provider import (
    SupabasePostgresDbEventCountsProvider,
)

# Rows as run_select_statement returns them — tuples in the SELECT's column order.
CATEGORY_ROWS = [
    ("AVALANCHE_ORG", "Bridgeport Avalanche Center", "avalanche", None, "no_rating", 39),
    ("GDACS", None, "earthquake", "tsunami", "medium", 12),
]
LOCATION_ROWS = [
    ("AVALANCHE_ORG", "Bridgeport Avalanche Center", "US", "CA", "no_rating", 39),
    ("GDACS", None, "JP", None, "medium", 12),
]


@pytest.fixture
def mock_base_provider() -> MagicMock:
    """Base provider mock returning CATEGORY_ROWS from run_select_statement."""
    base = MagicMock()
    base.run_select_statement = AsyncMock(return_value=list(CATEGORY_ROWS))
    return base


@pytest.fixture
def provider(mock_base_provider: MagicMock) -> SupabasePostgresDbEventCountsProvider:
    """Event counts provider wired to the mocked base provider."""
    return SupabasePostgresDbEventCountsProvider(supabase_postgres_provider=mock_base_provider)


def _statement_sql(mock_base_provider: MagicMock) -> str:
    """Compile the captured select statement and return its SQL."""
    statement = mock_base_provider.run_select_statement.call_args.args[0]
    return str(statement.compile())


class TestSupabasePostgresDbEventCountsProvider:
    """Tests for :class:`SupabasePostgresDbEventCountsProvider`."""

    async def test_get_event_counts_by_category_returns_counts(
        self, provider: SupabasePostgresDbEventCountsProvider, mock_base_provider: MagicMock
    ) -> None:
        """Grouped rows are parsed into EventCategoryCount models, NULLs included."""
        result = await provider.get_event_counts_by_category()

        assert result == [
            EventCategoryCount(
                source_name="AVALANCHE_ORG",
                subsource_name="Bridgeport Avalanche Center",
                event_category="avalanche",
                event_subcategory=None,
                danger_rating="no_rating",
                count=39,
            ),
            EventCategoryCount(
                source_name="GDACS",
                subsource_name=None,
                event_category="earthquake",
                event_subcategory="tsunami",
                danger_rating="medium",
                count=12,
            ),
        ]
        mock_base_provider.run_select_statement.assert_awaited_once()

    async def test_get_event_counts_by_category_groups_by_taxonomy(
        self, provider: SupabasePostgresDbEventCountsProvider, mock_base_provider: MagicMock
    ) -> None:
        """The category statement counts union_etl rows grouped by the five taxonomy columns."""
        # Act
        await provider.get_event_counts_by_category()

        # Assert
        sql = _statement_sql(mock_base_provider)
        assert "FROM geo.union_etl" in sql
        assert "count(*) AS count" in sql
        group_by = sql.split("GROUP BY", 1)[1]
        assert "geo.union_etl.source_name" in group_by
        assert "geo.union_etl.subsource_name" in group_by
        assert "geo.union_etl.event_category" in group_by
        assert "geo.union_etl.event_subcategory" in group_by
        assert "geo.union_etl.danger_rating" in group_by
        assert "geo.union_etl.country_code" not in group_by
        assert "geo.union_etl.state_province" not in group_by

    async def test_get_event_counts_by_location_returns_counts(
        self, provider: SupabasePostgresDbEventCountsProvider, mock_base_provider: MagicMock
    ) -> None:
        """Grouped rows are parsed into EventLocationCount models, NULLs included."""
        # Arrange
        mock_base_provider.run_select_statement = AsyncMock(return_value=list(LOCATION_ROWS))

        # Act
        result = await provider.get_event_counts_by_location()

        # Assert
        assert result == [
            EventLocationCount(
                source_name="AVALANCHE_ORG",
                subsource_name="Bridgeport Avalanche Center",
                country_code="US",
                state_province="CA",
                danger_rating="no_rating",
                count=39,
            ),
            EventLocationCount(
                source_name="GDACS",
                subsource_name=None,
                country_code="JP",
                state_province=None,
                danger_rating="medium",
                count=12,
            ),
        ]
        mock_base_provider.run_select_statement.assert_awaited_once()

    async def test_get_event_counts_by_location_groups_by_location(
        self, provider: SupabasePostgresDbEventCountsProvider, mock_base_provider: MagicMock
    ) -> None:
        """The location statement counts union_etl rows grouped by the five location columns."""
        # Act
        await provider.get_event_counts_by_location()

        # Assert
        sql = _statement_sql(mock_base_provider)
        assert "FROM geo.union_etl" in sql
        assert "count(*) AS count" in sql
        group_by = sql.split("GROUP BY", 1)[1]
        assert "geo.union_etl.source_name" in group_by
        assert "geo.union_etl.subsource_name" in group_by
        assert "geo.union_etl.country_code" in group_by
        assert "geo.union_etl.state_province" in group_by
        assert "geo.union_etl.danger_rating" in group_by
        assert "geo.union_etl.event_category" not in group_by
        assert "geo.union_etl.event_subcategory" not in group_by

    async def test_get_event_counts_returns_empty_list_when_no_rows(self, mock_base_provider: MagicMock) -> None:
        """An empty table yields an empty list, not an error."""
        # Arrange
        mock_base_provider.run_select_statement = AsyncMock(return_value=[])
        provider = SupabasePostgresDbEventCountsProvider(supabase_postgres_provider=mock_base_provider)

        # Act
        category_counts = await provider.get_event_counts_by_category()
        location_counts = await provider.get_event_counts_by_location()

        # Assert
        assert category_counts == []
        assert location_counts == []

    def test_is_read_only(self) -> None:
        """The provider exposes no create/update/delete methods (read-only contract)."""
        assert not hasattr(SupabasePostgresDbEventCountsProvider, "create")
        assert not hasattr(SupabasePostgresDbEventCountsProvider, "update")
        assert not hasattr(SupabasePostgresDbEventCountsProvider, "delete")
