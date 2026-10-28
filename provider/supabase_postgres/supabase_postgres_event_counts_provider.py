"""Supabase Postgres provider for event count aggregations."""

from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import func
from sqlmodel.sql.expression import Select

from model.event_count import EventCategoryCount, EventLocationCount
from model.union_etl import union_etl
from provider.db.i_db_event_counts_provider import IDbEventCountsProvider
from provider.db.i_db_provider import IDbProvider
from provider.supabase_postgres.supabase_postgres_provider import get_provider

EventCountT = TypeVar("EventCountT", EventCategoryCount, EventLocationCount)


def _to_count(count_type: type[EventCountT], row: Any) -> EventCountT:
    """Convert one grouped query row into an event count model.

    Args:
        count_type: The model to build — its field order mirrors the column
            order of the ``SELECT`` (grouping columns, then ``count``).
        row: Result row in the column order of the statement.

    Returns:
        The parsed count row.
    """
    return count_type(**dict(zip(count_type.model_fields, row, strict=True)))


def _counts_statement(columns: Sequence[Any], limit: int) -> Select:
    """Build the ``SELECT ... COUNT(*) GROUP BY ... ORDER BY ... LIMIT`` statement.

    Shared by both aggregations — they differ only in which five columns
    they group by.

    Args:
        columns: The grouping columns, in SELECT/GROUP BY/ORDER BY order.
        limit: Maximum number of groups returned.

    Returns:
        The aggregate statement (the grouping columns plus ``count``).

    Note:
        Built with the ``Select(...)`` constructor instead of sqlmodel's
        ``select()`` because select()'s overloads stop at four entities
        (sqlmodel/sql/_expression_select_gen.py), and these aggregates group
        by five.
    """
    return Select(*columns, func.count().label("count")).group_by(*columns).order_by(*columns).limit(limit)


class SupabasePostgresDbEventCountsProvider(IDbEventCountsProvider):
    """Read-only event count aggregation provider for ``geo.union_etl``.

    Mirrors ETLReddit's entity providers (interface + Supabase implementation
    with an injected base provider); the queries are ``SELECT ... COUNT(*)
    GROUP BY`` aggregates instead of row reads, still executed through the
    shared ``run_select_statement``.
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

    async def get_event_counts_by_category(self, limit: int = 100) -> list[EventCategoryCount]:
        """Return row counts grouped by source, event taxonomy and danger rating.

        Args:
            limit: Maximum number of groups returned (default 100).

        Returns:
            One row per distinct ``source_name`` / ``subsource_name`` /
            ``event_category`` / ``event_subcategory`` / ``danger_rating``
            combination, ordered by those five columns; an empty list when the
            table has no rows.
        """
        statement = _counts_statement(
            (
                union_etl.c.source_name,
                union_etl.c.subsource_name,
                union_etl.c.event_category,
                union_etl.c.event_subcategory,
                union_etl.c.danger_rating,
            ),
            limit,
        )
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        return [_to_count(EventCategoryCount, row) for row in rows]

    async def get_event_counts_by_location(self, limit: int = 100) -> list[EventLocationCount]:
        """Return row counts grouped by source, location and danger rating.

        Args:
            limit: Maximum number of groups returned (default 100).

        Returns:
            One row per distinct ``source_name`` / ``subsource_name`` /
            ``country_code`` / ``state_province`` / ``danger_rating``
            combination, ordered by those five columns; an empty list when the
            table has no rows.
        """
        statement = _counts_statement(
            (
                union_etl.c.source_name,
                union_etl.c.subsource_name,
                union_etl.c.country_code,
                union_etl.c.state_province,
                union_etl.c.danger_rating,
            ),
            limit,
        )
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        return [_to_count(EventLocationCount, row) for row in rows]
