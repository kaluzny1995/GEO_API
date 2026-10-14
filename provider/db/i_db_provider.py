"""Database provider interface."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel
from sqlmodel.sql.expression import Select, SelectOfScalar


class IDbProvider(ABC):
    """Database provider interface.

    Async contract every database provider implements: connectivity check,
    engine/logger access, table management and batch select/insert statements.
    Implementations wrap a concrete engine (e.g. Supabase Postgres via asyncpg)
    and translate connection failures into :class:`error.SupabaseServerDownError`.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Verify that the database is reachable.

        Raises:
            SupabaseServerDownError: If the connection cannot be established.
        """
        pass

    @abstractmethod
    def get_logger(self) -> logging.Logger:
        """Return the provider's logger.

        Returns:
            The provider's :class:`logging.Logger`.
        """
        pass

    @abstractmethod
    def get_db_engine(self) -> AsyncEngine:
        """Return the async SQLAlchemy engine.

        Returns:
            The provider's :class:`~sqlalchemy.ext.asyncio.AsyncEngine`.
        """
        pass

    @abstractmethod
    async def create_table_if_not_exists(self, entity: type[SQLModel], table: str, schema: str) -> None:
        """Create a table if it does not exist.

        Args:
            entity: SQLModel table class (``table=True``) defining the schema.
            table: Table name.
            schema: Schema name (e.g. ``"geo"``).

        Raises:
            SupabaseServerDownError: If the database cannot be reached.
        """
        pass

    @abstractmethod
    async def run_select_statement(self, statement: Select | SelectOfScalar) -> Sequence[Any]:
        """Execute a select statement and return the results.

        Args:
            statement: SQLModel select statement.

        Returns:
            The query results.

        Raises:
            SupabaseServerDownError: If the database cannot be reached.
        """
        pass

    @abstractmethod
    async def run_insert_statement(
        self, entities: list[SQLModel], batch_size: int, num_entities: int = 10000, name: str = "entities"
    ) -> None:
        """Insert entities into the database in batches.

        Args:
            entities: Rows to insert.
            batch_size: Number of rows per transaction.
            num_entities: Total number of entities (for progress logging).
            name: Entity name used in log messages.

        Raises:
            SupabaseServerDownError: If the database cannot be reached.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Dispose the engine's connection pool."""
        pass
