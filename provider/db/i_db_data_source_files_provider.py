"""Data source files provider interface (read-only)."""

from abc import ABC, abstractmethod

from model.data_source_file import DataSourceFile, DataSourceSource


class IDbDataSourceFilesProvider(ABC):
    """Read-only contract for the CSV metadata tables written by GEO_ETL."""

    @abstractmethod
    async def get_files(self) -> list[DataSourceFile]:
        """Return every published CSV metadata row.

        Returns:
            Rows ordered by ``source_name`` then ``file_name``.
        """
        pass

    @abstractmethod
    async def get_sources(self) -> list[DataSourceSource]:
        """Return every published source-folder row.

        Returns:
            Rows ordered by ``source_name``. This list keeps a source visible
            even when it currently has no CSV files.
        """
        pass
