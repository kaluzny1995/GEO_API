"""Supabase Postgres provider for data quantity row counts."""

from sqlalchemy import Column, MetaData, String, Table, func
from sqlmodel.sql.expression import Select, SelectOfScalar

from model.data_quantity import OVERALL_FILE_DATE, TABLE_NAMES, TableCount
from model.union_etl import union_etl
from provider.db.i_db_data_quantity_provider import IDbDataQuantityProvider
from provider.db.i_db_provider import IDbProvider
from provider.supabase_postgres.supabase_postgres_provider import get_provider


def _tracked_table(table_name: str) -> Table:
    """Return a minimal ``geo.<table_name>`` Core table for a ``COUNT(*)``.

    Only ``file_date`` is declared — the count statement needs nothing else, and
    the table name always comes from :data:`model.data_quantity.TABLE_NAMES`
    (never from a request), so it is safe to interpolate into the schema. A
    fresh :class:`~sqlalchemy.MetaData` is used per call so repeated requests do
    not collide on the same table key.

    Args:
        table_name: One of the tracked table names.

    Returns:
        The Core table object for the ``geo`` schema.
    """
    return Table(table_name, MetaData(), Column("file_date", String), schema="geo")


class SupabasePostgresDbDataQuantityProvider(IDbDataQuantityProvider):
    """Read-only ``COUNT(*)`` provider for the tracked GEO tables.

    Mirrors the other read-only providers: an interface plus a Supabase
    implementation that delegates statement execution to the shared base
    provider (and therefore reuses its engine and logging).
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

    async def get_table_counts(self, file_date: str) -> list[TableCount]:
        """Return the actual row count of every tracked table for *file_date*.

        Args:
            file_date: Snapshot date (``YYYY-MM-DD``) or ``"overall"`` for the
                whole table.

        Returns:
            One count row per tracked table, in ``TABLE_NAMES`` order.
        """
        counts: list[TableCount] = []
        for table_name in TABLE_NAMES:
            table = _tracked_table(table_name)
            statement: Select | SelectOfScalar = Select(func.count()).select_from(table)
            if file_date != OVERALL_FILE_DATE:
                statement = statement.where(table.c.file_date == file_date)
            rows = await self.supabase_postgres_provider.run_select_statement(statement)
            count = int(rows[0][0]) if rows else 0
            counts.append(TableCount(table_name=table_name, file_date=file_date, count=count))
        return counts

    async def get_file_dates(self) -> list[str]:
        """Return every snapshot date present in ``geo.union_etl``.

        Returns:
            The distinct ``file_date`` values in ascending order, followed by
            the ``"overall"`` sentinel.
        """
        statement: Select | SelectOfScalar = Select(union_etl.c.file_date).distinct().order_by(union_etl.c.file_date)
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        return [*[str(row[0] if not isinstance(row, str) else row) for row in rows], OVERALL_FILE_DATE]
