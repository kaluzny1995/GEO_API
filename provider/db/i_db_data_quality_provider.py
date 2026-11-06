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

    @abstractmethod
    async def get_file_dates(self, table_name: str) -> list[str]:
        """Return every snapshot date recorded for a table.

        Unlike the client-side "probe a rolling window" approach, this is the
        authoritative list: it is a ``SELECT DISTINCT file_date`` over
        ``geo.data_quality``, so it never misses snapshots older than any
        arbitrary window and never invents dates that have no rows.

        Args:
            table_name: Measured table name.

        Returns:
            The distinct ``file_date`` values in ascending order (``"overall"``
            sorts last because it is not a date). Empty when the table has no
            metrics.
        """
        pass

    @abstractmethod
    async def get_table_names(self) -> list[str]:
        """Return the tables and views available in the ``geo`` schema.

        The dropdown in GEO_APP must not rely on a hardcoded list: the pipeline
        adds source/ETL tables and, since the ``VIEW`` jobs were introduced,
        ``*_vw`` relations. This introspection returns every user-facing relation
        so a newly added table/view appears without a frontend release. The internal
        ``data_quality`` metrics table is excluded.

        Returns:
            Relation names in ascending order.
        """
        pass
