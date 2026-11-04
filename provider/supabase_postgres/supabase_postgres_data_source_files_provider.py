"""Supabase Postgres provider for the CSV metadata tables."""

import sqlalchemy
from sqlmodel import select

from model.data_source_file import DataSourceFile, DataSourceSource
from provider.db.i_db_data_source_files_provider import IDbDataSourceFilesProvider
from provider.db.i_db_provider import IDbProvider
from provider.supabase_postgres.supabase_postgres_provider import get_provider


class SupabasePostgresDbDataSourceFilesProvider(IDbDataSourceFilesProvider):
    """Read-only provider for ``geo.data_source_files`` and ``geo.data_source_sources``.

    Both tables are owned by GEO_ETL's PySpark ``DATA_SOURCE_FILE`` job; this
    provider only selects from them. A fresh deployment has no tables until the
    first job run, so an undefined-table ``ProgrammingError`` is treated as an
    empty inventory instead of a 500.
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

    async def get_files(self) -> list[DataSourceFile]:
        """Return every CSV metadata row ordered by source and file name."""
        statement = select(DataSourceFile).order_by(DataSourceFile.source_name, DataSourceFile.file_name)
        try:
            return await self.supabase_postgres_provider.run_select_statement(statement)
        except sqlalchemy.exc.ProgrammingError:
            return []

    async def get_sources(self) -> list[DataSourceSource]:
        """Return every source-folder row ordered by source name."""
        statement = select(DataSourceSource).order_by(DataSourceSource.source_name)
        try:
            return await self.supabase_postgres_provider.run_select_statement(statement)
        except sqlalchemy.exc.ProgrammingError:
            return []
