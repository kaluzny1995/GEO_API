"""Supabase Postgres provider for data quality metrics."""

from sqlmodel import select

from model.data_quality import DataQuality
from provider.db.i_db_data_quality_provider import IDbDataQualityProvider
from provider.db.i_db_provider import IDbProvider
from provider.supabase_postgres.supabase_postgres_provider import get_provider


class SupabasePostgresDbDataQualityProvider(IDbDataQualityProvider):
    """Read-only data quality metrics provider for ``geo.data_quality``.

    Mirrors ETLReddit's entity providers (interface + Supabase implementation
    with an injected base provider), read-only because GEO_ETL owns the table.
    """

    supabase_postgres_provider: IDbProvider

    def __init__(self, supabase_postgres_provider: IDbProvider | None = None) -> None:
        """Initialize the provider.

        Args:
            supabase_postgres_provider: Base provider for running statements.
                Defaults to the shared :func:`get_provider` singleton.
        """
        super().__init__()
        self.supabase_postgres_provider = supabase_postgres_provider or get_provider()

    async def get_data_quality(self, table_name: str, file_date: str = "overall") -> list[DataQuality]:
        """Return the data quality metrics for a table.

        Args:
            table_name: Measured table name.
            file_date: Snapshot date (``YYYY-MM-DD``) or ``"overall"``
                (whole-table snapshot) — the default.

        Returns:
            The metric rows ordered by ``metric``.
        """
        statement = (
            select(DataQuality)
            .where(DataQuality.table_name == table_name)
            .where(DataQuality.file_date == file_date)
            .order_by(DataQuality.metric)
        )
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        return rows

    async def get_data_quality_for_file_dates(self, table_name: str, file_dates: list[str]) -> list[DataQuality]:
        """Return the data quality metrics for a table across many file_dates.

        Args:
            table_name: Measured table name.
            file_dates: Snapshot dates (``YYYY-MM-DD``).

        Returns:
            The metric rows ordered by ``file_date`` then ``metric``; an empty
            list when ``file_dates`` is empty.
        """
        if not file_dates:
            return []
        statement = (
            select(DataQuality)
            .where(DataQuality.table_name == table_name)
            .where(DataQuality.file_date.in_(file_dates))  # type: ignore[attr-defined]
            .order_by(DataQuality.file_date, DataQuality.metric)
        )
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        return rows
