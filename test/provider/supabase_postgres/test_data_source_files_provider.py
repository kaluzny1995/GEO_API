"""Tests for the Supabase Postgres data source files provider (base provider mocked)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import sqlalchemy

from model.data_source_file import DataSourceFile, DataSourceSource
from provider.supabase_postgres.supabase_postgres_data_source_files_provider import (
    SupabasePostgresDbDataSourceFilesProvider,
)


def _select_result(statement) -> list:
    """Return a representative row for whichever metadata table is queried."""
    sql = str(statement.compile())
    if "data_source_sources" in sql:
        return [
            DataSourceSource(
                source_name="EONET",
                pipeline_start_date="2026-09-01",
                updated_at="2026-11-03T22:16:58Z",
            )
        ]
    return [
        DataSourceFile(
            source_name="EONET",
            file_name="eonet_events_2026-09-01.csv",
            snapshot_date="2026-09-01",
            created_at="2026-10-04T02:14:50Z",
            records=12,
            size_kb=0.7,
            pipeline_start_date="2026-09-01",
        )
    ]


@pytest.fixture
def mock_base_provider() -> MagicMock:
    """Base provider mock returning representative rows for both tables."""
    base = MagicMock()
    base.run_select_statement = AsyncMock(side_effect=_select_result)
    return base


@pytest.fixture
def provider(mock_base_provider: MagicMock) -> SupabasePostgresDbDataSourceFilesProvider:
    """Data source files provider wired to the mocked base provider."""
    return SupabasePostgresDbDataSourceFilesProvider(supabase_postgres_provider=mock_base_provider)


class TestSupabasePostgresDbDataSourceFilesProvider:
    """Tests for :class:`SupabasePostgresDbDataSourceFilesProvider`."""

    async def test_returns_the_file_rows(
        self, provider: SupabasePostgresDbDataSourceFilesProvider, mock_base_provider: MagicMock
    ) -> None:
        """The provider returns the base provider's file rows unchanged."""
        rows = await provider.get_files()

        assert len(rows) == 1
        assert rows[0].file_name == "eonet_events_2026-09-01.csv"
        statement = mock_base_provider.run_select_statement.call_args.args[0]
        sql = str(statement.compile())
        assert "FROM geo.data_source_files" in sql
        assert "ORDER BY" in sql

    async def test_returns_the_source_rows(
        self, provider: SupabasePostgresDbDataSourceFilesProvider, mock_base_provider: MagicMock
    ) -> None:
        """The provider returns the source registry rows unchanged."""
        rows = await provider.get_sources()

        assert len(rows) == 1
        assert rows[0].source_name == "EONET"
        statement = mock_base_provider.run_select_statement.call_args.args[0]
        sql = str(statement.compile())
        assert "FROM geo.data_source_sources" in sql
        assert "ORDER BY" in sql

    async def test_returns_empty_lists_when_the_tables_do_not_exist(
        self, provider: SupabasePostgresDbDataSourceFilesProvider, mock_base_provider: MagicMock
    ) -> None:
        """A fresh deployment has no metadata tables until the first job run."""
        mock_base_provider.run_select_statement = AsyncMock(
            side_effect=sqlalchemy.exc.ProgrammingError("SELECT", {}, Exception("relation does not exist"))
        )

        assert await provider.get_files() == []
        assert await provider.get_sources() == []
