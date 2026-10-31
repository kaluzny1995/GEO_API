"""Data quantity provider interface."""

from abc import ABC, abstractmethod

from model.data_quantity import TableCount


class IDbDataQuantityProvider(ABC):
    """Read-only row-count contract for the tracked GEO tables."""

    @abstractmethod
    async def get_table_counts(self, file_date: str) -> list[TableCount]:
        """Return the row count of every tracked table for one snapshot.

        Args:
            file_date: Snapshot date (``YYYY-MM-DD``) or ``"overall"`` for the
                whole table.

        Returns:
            One :class:`~model.data_quantity.TableCount` per tracked table, in
            the configured ``TABLE_NAMES`` order.
        """
        pass

    @abstractmethod
    async def get_file_dates(self) -> list[str]:
        """Return every snapshot date present in ``geo.union_etl``.

        Returns:
            The distinct ``file_date`` values in ascending order, followed by
            the ``"overall"`` sentinel. Empty tables still yield
            ``["overall"]`` so the view can show the whole-table count.
        """
        pass
