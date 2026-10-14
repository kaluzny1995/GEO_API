"""Data quality metrics provider interface (read-only)."""

from abc import ABC, abstractmethod

from model.data_quality import DataQuality


class IDbDataQualityProvider(ABC):
    """Data quality metrics provider interface.

    Read-only by design: GEO_ETL owns the ``geo.data_quality`` table, the API
    only serves it — there are no create/update/delete methods.
    """

    @abstractmethod
    async def get_data_quality(self, table_name: str, file_date: str = "overall") -> list[DataQuality]:
        """Return the data quality metrics for a table.

        Args:
            table_name: Measured table name.
            file_date: Snapshot date (``YYYY-MM-DD``) or ``"overall"``
                (whole-table snapshot) — the default.

        Returns:
            The metric rows ordered by ``metric``.
        """
        pass

    @abstractmethod
    async def get_data_quality_for_file_dates(self, table_name: str, file_dates: list[str]) -> list[DataQuality]:
        """Return the data quality metrics for a table across many file_dates.

        Args:
            table_name: Measured table name.
            file_dates: Snapshot dates (``YYYY-MM-DD``).

        Returns:
            The metric rows ordered by ``file_date`` then ``metric``.
        """
        pass
