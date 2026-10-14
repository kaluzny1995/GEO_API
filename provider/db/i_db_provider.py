"""Database provider interface."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel
from sqlmodel.sql.expression import Select, SelectOfScalar


class IDbProvider(ABC):
    """Database provider interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Verify that the database is reachable."""
        pass

    @abstractmethod
    def get_logger(self) -> logging.Logger:
        """Return the provider's logger."""
        pass

    @abstractmethod
    def get_db_engine(self) -> AsyncEngine:
        """Return the async SQLAlchemy engine."""
        pass

    @abstractmethod
    async def create_table_if_not_exists(self, entity: type[SQLModel], table: str, schema: str) -> None:
        """Create a table if it does not exist."""
        pass

    @abstractmethod
    async def run_select_statement(self, statement: Select | SelectOfScalar) -> Sequence[Any]:
        """Execute a select statement and return the results."""
        pass

    @abstractmethod
    async def run_insert_statement(
        self, entities: list[SQLModel], batch_size: int, num_entities: int = 10000, name: str = "entities"
    ) -> None:
        """Insert entities into the database in batches."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Dispose the engine's connection pool."""
        pass
