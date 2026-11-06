"""Supabase Postgres provider for data quality metrics."""

import sqlalchemy
from sqlmodel import select

from model.data_quality import DataQuality
from provider.db.i_db_data_quality_provider import IDbDataQualityProvider
from provider.db.i_db_provider import IDbProvider
from provider.supabase_postgres.supabase_postgres_provider import get_provider

# ``information_schema.tables`` modelled just enough for a name/type projection.
# A Core Table (not a SQLModel entity) keeps the introspection query plain and
# lets the shared provider log/execute it like the other select statements.
_INFORMATION_SCHEMA_TABLES = sqlalchemy.Table(
    "tables",
    sqlalchemy.MetaData(),
    sqlalchemy.Column("table_schema", sqlalchemy.String),
    sqlalchemy.Column("table_name", sqlalchemy.String),
    sqlalchemy.Column("table_type", sqlalchemy.String),
    schema="information_schema",
)


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

    async def get_file_dates(self, table_name: str) -> list[str]:
        """Return every snapshot date recorded for a table.

        A ``SELECT DISTINCT file_date`` over ``geo.data_quality`` — the
        authoritative list, so a client never has to guess a window.

        Args:
            table_name: Measured table name.

        Returns:
            The distinct ``file_date`` values in ascending order (``"overall"``
            sorts last because it is not a date); empty when the table has no
            metrics.
        """
        statement = (
            select(DataQuality.file_date)
            .where(DataQuality.table_name == table_name)
            .distinct()
            .order_by(DataQuality.file_date)
        )
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        return [str(row) for row in rows]

    async def get_table_names(self) -> list[str]:
        """Return every user-facing table/view in the ``geo`` schema.

        ``information_schema.tables`` lists both base tables and views, so the
        data-quality dropdown follows the database instead of a hardcoded list.
        The internal ``data_quality`` metrics table is filtered out.

        Returns:
            Relation names in ascending order.
        """
        statement = (
            select(_INFORMATION_SCHEMA_TABLES.c.table_name)
            .where(_INFORMATION_SCHEMA_TABLES.c.table_schema == "geo")
            .where(_INFORMATION_SCHEMA_TABLES.c.table_type.in_(("BASE TABLE", "VIEW")))
            .order_by(_INFORMATION_SCHEMA_TABLES.c.table_name)
        )
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        names = [str(row[0]) if isinstance(row, (tuple, list)) else str(row) for row in rows]
        return [name for name in names if name != "data_quality"]
