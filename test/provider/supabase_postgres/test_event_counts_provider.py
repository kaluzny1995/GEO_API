"""Tests for the Supabase Postgres event counts provider (base provider mocked)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from model.event_count import EventCategoryCount, EventLocationCount
from provider.supabase_postgres.supabase_postgres_data_quality_provider import (
    SupabasePostgresDbDataQualityProvider,
)
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

    @pytest.mark.parametrize(
        ("method", "rows", "expected"),
        [
            pytest.param(
                "get_event_counts_by_category",
                CATEGORY_ROWS,
                [
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
                ],
                id="category",
            ),
            pytest.param(
                "get_event_counts_by_location",
                LOCATION_ROWS,
                [
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
                ],
                id="location",
            ),
        ],
    )
    async def test_get_event_counts_parses_rows(
        self,
        provider: SupabasePostgresDbEventCountsProvider,
        mock_base_provider: MagicMock,
        method: str,
        rows: list[tuple],
        expected: list[EventCategoryCount] | list[EventLocationCount],
    ) -> None:
        """Grouped rows are parsed into the matching count model, NULLs included."""
        # Arrange
        mock_base_provider.run_select_statement = AsyncMock(return_value=list(rows))

        # Act
        result = await getattr(provider, method)()

        # Assert
        assert result == expected
        mock_base_provider.run_select_statement.assert_awaited_once()

    @pytest.mark.parametrize(
        ("method", "grouped_columns", "absent_columns"),
        [
            pytest.param(
                "get_event_counts_by_category",
                [
                    "geo.union_etl.source_name",
                    "geo.union_etl.subsource_name",
                    "geo.union_etl.event_category",
                    "geo.union_etl.event_subcategory",
                    "geo.union_etl.danger_rating",
                ],
                ["geo.union_etl.country_code", "geo.union_etl.state_province"],
                id="category",
            ),
            pytest.param(
                "get_event_counts_by_location",
                [
                    "geo.union_etl.source_name",
                    "geo.union_etl.subsource_name",
                    "geo.union_etl.country_code",
                    "geo.union_etl.state_province",
                    "geo.union_etl.danger_rating",
                ],
                ["geo.union_etl.event_category", "geo.union_etl.event_subcategory"],
                id="location",
            ),
        ],
    )
    async def test_statement_groups_by_the_five_columns(
        self,
        provider: SupabasePostgresDbEventCountsProvider,
        mock_base_provider: MagicMock,
        method: str,
        grouped_columns: list[str],
        absent_columns: list[str],
    ) -> None:
        """Each statement counts union_etl rows grouped by its own five columns."""
        # Act
        await getattr(provider, method)()

        # Assert
        sql = _statement_sql(mock_base_provider)
        assert "FROM geo.union_etl" in sql
        assert "count(*) AS count" in sql
        group_by = sql.split("GROUP BY", 1)[1]
        for column in grouped_columns:
            assert column in group_by, column
        for column in absent_columns:
            assert column not in group_by, column

    async def test_statement_carries_the_limit(
        self, provider: SupabasePostgresDbEventCountsProvider, mock_base_provider: MagicMock
    ) -> None:
        """The shared statement applies the requested LIMIT to the grouped rows."""
        # Act
        await provider.get_event_counts_by_category(limit=7)

        # Assert
        assert "LIMIT" in _statement_sql(mock_base_provider)

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


@pytest.mark.parametrize(
    "provider_class",
    [SupabasePostgresDbEventCountsProvider, SupabasePostgresDbDataQualityProvider],
)
def test_is_read_only(provider_class: type) -> None:
    """Neither read-only provider exposes create/update/delete methods (read-only contract)."""
    assert not hasattr(provider_class, "create")
    assert not hasattr(provider_class, "update")
    assert not hasattr(provider_class, "delete")
