"""Tests for the Supabase Postgres data quality provider (base provider mocked)."""

import datetime as dt
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from model.data_quality import DataQuality
from provider.supabase_postgres.supabase_postgres_data_quality_provider import SupabasePostgresDbDataQualityProvider

ROWS = [
    DataQuality(
        table_name="usgs_earthquake",
        file_date="overall",
        metric="bad_row_pct",
        value=0.001,
        computed_at=dt.datetime(2026, 9, 21, 2, 15, 0),
    ),
    DataQuality(
        table_name="usgs_earthquake",
        file_date="overall",
        metric="total_records",
        value=12345.0,
        computed_at=dt.datetime(2026, 9, 21, 2, 15, 0),
    ),
]


@pytest.fixture
def mock_base_provider() -> MagicMock:
    """Base provider mock returning ROWS from run_select_statement."""
    base = MagicMock()
    base.run_select_statement = AsyncMock(return_value=list(ROWS))
    return base


@pytest.fixture
def provider(mock_base_provider: MagicMock) -> SupabasePostgresDbDataQualityProvider:
    """Data quality provider wired to the mocked base provider."""
    return SupabasePostgresDbDataQualityProvider(supabase_postgres_provider=mock_base_provider)


def _statement_params(mock_base_provider: MagicMock) -> dict[str, Any]:
    """Compile the captured select statement and return its bind parameters."""
    statement = mock_base_provider.run_select_statement.call_args.args[0]
    return statement.compile().params


class TestSupabasePostgresDbDataQualityProvider:
    """Tests for :class:`SupabasePostgresDbDataQualityProvider`."""

    async def test_get_data_quality_defaults_to_overall(
        self, provider: SupabasePostgresDbDataQualityProvider, mock_base_provider: MagicMock
    ) -> None:
        """Default call filters by file_date = overall."""
        result = await provider.get_data_quality("usgs_earthquake")

        assert result == ROWS
        mock_base_provider.run_select_statement.assert_awaited_once()
        params = _statement_params(mock_base_provider)
        assert "usgs_earthquake" in params.values()
        assert "overall" in params.values()

    async def test_get_data_quality_with_file_date(
        self, provider: SupabasePostgresDbDataQualityProvider, mock_base_provider: MagicMock
    ) -> None:
        """Passing a file_date filters by that date instead of overall."""
        result = await provider.get_data_quality("usgs_earthquake", "2026-09-20")

        assert result == ROWS
        mock_base_provider.run_select_statement.assert_awaited_once()
        params = _statement_params(mock_base_provider)
        assert "usgs_earthquake" in params.values()
        assert "2026-09-20" in params.values()
        assert "overall" not in params.values()

    async def test_get_data_quality_returns_empty_list_when_no_metrics(self, mock_base_provider: MagicMock) -> None:
        """No matching rows yield an empty list, not an error."""
        mock_base_provider.run_select_statement = AsyncMock(return_value=[])
        provider = SupabasePostgresDbDataQualityProvider(supabase_postgres_provider=mock_base_provider)

        result = await provider.get_data_quality("unknown_table")

        assert result == []

    async def test_get_data_quality_for_file_dates_filters_by_many_dates(
        self, provider: SupabasePostgresDbDataQualityProvider, mock_base_provider: MagicMock
    ) -> None:
        """Many dates compile to a single IN bind parameter."""
        result = await provider.get_data_quality_for_file_dates("usgs_earthquake", ["2026-09-19", "2026-09-20"])

        assert result == ROWS
        mock_base_provider.run_select_statement.assert_awaited_once()
        params = _statement_params(mock_base_provider)
        assert "usgs_earthquake" in params.values()
        assert ["2026-09-19", "2026-09-20"] in params.values()

    async def test_get_data_quality_for_file_dates_with_single_date(
        self, provider: SupabasePostgresDbDataQualityProvider, mock_base_provider: MagicMock
    ) -> None:
        """A single-element date list still uses the IN clause."""
        result = await provider.get_data_quality_for_file_dates("usgs_earthquake", ["2026-09-20"])

        assert result == ROWS
        params = _statement_params(mock_base_provider)
        assert ["2026-09-20"] in params.values()

    async def test_get_data_quality_for_file_dates_empty_list_returns_empty_without_query(
        self, provider: SupabasePostgresDbDataQualityProvider, mock_base_provider: MagicMock
    ) -> None:
        """An empty file_dates list short-circuits without querying."""
        result = await provider.get_data_quality_for_file_dates("usgs_earthquake", [])

        assert result == []
        mock_base_provider.run_select_statement.assert_not_awaited()
