"""Tests for the Supabase Postgres data quantity provider (base provider mocked)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from model.data_quantity import OVERALL_FILE_DATE, TABLE_NAMES
from provider.supabase_postgres.supabase_postgres_data_quantity_provider import (
    SupabasePostgresDbDataQuantityProvider,
)


@pytest.fixture
def mock_base_provider() -> MagicMock:
    """Base provider mock returning a one-row count result for every statement."""
    base = MagicMock()
    base.run_select_statement = AsyncMock(return_value=[(7,)])
    return base


@pytest.fixture
def provider(mock_base_provider: MagicMock) -> SupabasePostgresDbDataQuantityProvider:
    """Data quantity provider wired to the mocked base provider."""
    return SupabasePostgresDbDataQuantityProvider(supabase_postgres_provider=mock_base_provider)


class TestSupabasePostgresDbDataQuantityProvider:
    """Tests for :class:`SupabasePostgresDbDataQuantityProvider`."""

    async def test_counts_every_tracked_table_for_a_snapshot(
        self, provider: SupabasePostgresDbDataQuantityProvider, mock_base_provider: MagicMock
    ) -> None:
        """One COUNT(*) statement runs per tracked table and each row is parsed."""
        # Act
        counts = await provider.get_table_counts("2026-10-26")

        # Assert
        assert [row.table_name for row in counts] == list(TABLE_NAMES)
        assert {row.file_date for row in counts} == {"2026-10-26"}
        assert {row.count for row in counts} == {7}
        assert mock_base_provider.run_select_statement.await_count == len(TABLE_NAMES)

    async def test_snapshot_count_filters_by_file_date(
        self, provider: SupabasePostgresDbDataQuantityProvider, mock_base_provider: MagicMock
    ) -> None:
        """A dated snapshot counts only the rows whose file_date matches."""
        # Act
        await provider.get_table_counts("2026-10-26")

        # Assert
        statement = mock_base_provider.run_select_statement.call_args_list[0].args[0]
        first_sql = str(statement.compile())
        assert "FROM geo.eonet_event" in first_sql
        assert "WHERE geo.eonet_event.file_date" in first_sql
        assert "2026-10-26" in statement.compile().params.values()

    async def test_overall_count_does_not_filter(
        self, provider: SupabasePostgresDbDataQuantityProvider, mock_base_provider: MagicMock
    ) -> None:
        """The overall snapshot counts every row of every table."""
        # Act
        counts = await provider.get_table_counts(OVERALL_FILE_DATE)

        # Assert
        assert {row.file_date for row in counts} == {OVERALL_FILE_DATE}
        for call in mock_base_provider.run_select_statement.call_args_list:
            sql = str(call.args[0].compile())
            assert "WHERE" not in sql

    async def test_returns_zero_when_the_count_query_returns_no_rows(
        self, provider: SupabasePostgresDbDataQuantityProvider, mock_base_provider: MagicMock
    ) -> None:
        """A missing result is treated as zero rather than an error."""
        # Arrange
        mock_base_provider.run_select_statement = AsyncMock(return_value=[])

        # Act
        counts = await provider.get_table_counts("2026-10-26")

        # Assert
        assert {row.count for row in counts} == {0}

    async def test_file_dates_are_union_dates_plus_overall(
        self, provider: SupabasePostgresDbDataQuantityProvider, mock_base_provider: MagicMock
    ) -> None:
        """The date list comes from geo.union_etl and ends with the overall sentinel."""
        # Arrange — the driver returns a one-column Row per date.
        mock_base_provider.run_select_statement = AsyncMock(return_value=[("2026-10-25",), ("2026-10-26",)])

        # Act
        dates = await provider.get_file_dates()

        # Assert
        assert dates == ["2026-10-25", "2026-10-26", OVERALL_FILE_DATE]
        sql = str(mock_base_provider.run_select_statement.call_args.args[0].compile())
        assert "FROM geo.union_etl" in sql
        assert "DISTINCT" in sql

    async def test_empty_union_table_still_offers_overall(
        self, provider: SupabasePostgresDbDataQuantityProvider, mock_base_provider: MagicMock
    ) -> None:
        """An empty union table yields just the overall sentinel."""
        # Arrange
        mock_base_provider.run_select_statement = AsyncMock(return_value=[])

        # Act
        dates = await provider.get_file_dates()

        # Assert
        assert dates == [OVERALL_FILE_DATE]
