"""Supabase Postgres provider for event count aggregations."""

from typing import Any

from sqlalchemy import func
from sqlmodel.sql.expression import Select

from model.event_count import EventCategoryCount, EventLocationCount
from model.union_etl import union_etl
from provider.db.i_db_event_counts_provider import IDbEventCountsProvider
from provider.db.i_db_provider import IDbProvider
from provider.supabase_postgres.supabase_postgres_provider import get_provider


def _to_category_count(row: Any) -> EventCategoryCount:
    """Convert one grouped query row into an :class:`EventCategoryCount`.

    Args:
        row: Result row in the column order of the category ``SELECT``.

    Returns:
        The parsed count row.
    """
    source_name, subsource_name, event_category, event_subcategory, danger_rating, count = row
    return EventCategoryCount(
        source_name=source_name,
        subsource_name=subsource_name,
        event_category=event_category,
        event_subcategory=event_subcategory,
        danger_rating=danger_rating,
        count=count,
    )


def _to_location_count(row: Any) -> EventLocationCount:
    """Convert one grouped query row into an :class:`EventLocationCount`.

    Args:
        row: Result row in the column order of the location ``SELECT``.

    Returns:
        The parsed count row.
    """
    source_name, subsource_name, country_code, state_province, danger_rating, count = row
    return EventLocationCount(
        source_name=source_name,
        subsource_name=subsource_name,
        country_code=country_code,
        state_province=state_province,
        danger_rating=danger_rating,
        count=count,
    )


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

    async def get_event_counts_by_category(self) -> list[EventCategoryCount]:
        """Return row counts grouped by source, event taxonomy and danger rating.

        Returns:
            One row per distinct ``source_name`` / ``subsource_name`` /
            ``event_category`` / ``event_subcategory`` / ``danger_rating``
            combination, ordered by those five columns; an empty list when the
            table has no rows.
        """
        # sqlmodel's select() overloads stop at four entities
        # (sqlmodel/sql/_expression_select_gen.py), so a six-column aggregate is
        # built with the equivalent Select(...) constructor — sqlmodel's select()
        # does exactly that for more than one entity.
        statement: Select = (
            Select(
                union_etl.c.source_name,
                union_etl.c.subsource_name,
                union_etl.c.event_category,
                union_etl.c.event_subcategory,
                union_etl.c.danger_rating,
                func.count().label("count"),
            )
            .group_by(
                union_etl.c.source_name,
                union_etl.c.subsource_name,
                union_etl.c.event_category,
                union_etl.c.event_subcategory,
                union_etl.c.danger_rating,
            )
            .order_by(
                union_etl.c.source_name,
                union_etl.c.subsource_name,
                union_etl.c.event_category,
                union_etl.c.event_subcategory,
                union_etl.c.danger_rating,
            )
        )
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        return [_to_category_count(row) for row in rows]

    async def get_event_counts_by_location(self) -> list[EventLocationCount]:
        """Return row counts grouped by source, location and danger rating.

        Returns:
            One row per distinct ``source_name`` / ``subsource_name`` /
            ``country_code`` / ``state_province`` / ``danger_rating``
            combination, ordered by those five columns; an empty list when the
            table has no rows.
        """
        # See get_event_counts_by_category for why Select(...) is used over select().
        statement: Select = (
            Select(
                union_etl.c.source_name,
                union_etl.c.subsource_name,
                union_etl.c.country_code,
                union_etl.c.state_province,
                union_etl.c.danger_rating,
                func.count().label("count"),
            )
            .group_by(
                union_etl.c.source_name,
                union_etl.c.subsource_name,
                union_etl.c.country_code,
                union_etl.c.state_province,
                union_etl.c.danger_rating,
            )
            .order_by(
                union_etl.c.source_name,
                union_etl.c.subsource_name,
                union_etl.c.country_code,
                union_etl.c.state_province,
                union_etl.c.danger_rating,
            )
        )
        rows = await self.supabase_postgres_provider.run_select_statement(statement)
        return [_to_location_count(row) for row in rows]
