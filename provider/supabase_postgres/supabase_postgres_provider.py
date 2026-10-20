"""Supabase Postgres provider built on SQLModel's async engine (asyncpg driver)."""

import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any
from uuid import uuid4

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import Select, SelectOfScalar

import error
import util
from model.config.supabase_config import SupabaseConnectionConfig
from provider.db.i_db_provider import IDbProvider

# Exception types wrapped into SupabaseServerDownError by every provider operation.
CONNECTION_ERRORS = (
    sqlalchemy.exc.OperationalError,
    sqlalchemy.exc.InterfaceError,
    OSError,
)


class SupabasePostgresProvider(IDbProvider):
    """Supabase Postgres provider (SQLModel + SQLAlchemy 2.0 async engine + asyncpg).

    Mirrors ETLReddit's ``SupabasePostgresProvider``, upgraded to an async
    engine so it will not block FastAPI's event loop.

    Attributes:
        connection_url: SQLAlchemy asyncpg connection URL.
        db_engine: Async SQLAlchemy engine (connection pool).
        logger: Provider logger (module logger by default — no file handler;
            the endpoint loggers own the log files).
    """

    connection_url: str
    db_engine: AsyncEngine
    logger: logging.Logger

    def __init__(
        self,
        connection_url: str | None = None,
        db_engine: AsyncEngine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            connection_url: Explicit connection URL. Defaults to the URL built
                from ``.env`` credentials via :class:`SupabaseConnectionConfig`.
            db_engine: Pre-built async engine. Defaults to a new engine on ``connection_url``.
            logger: Custom logger. Defaults to the module logger (no file
                handler — connection failures surface in the calling endpoint's
                log file via the endpoint boundary traceback).
        """
        super().__init__()
        self.connection_url = connection_url or SupabaseConnectionConfig.from_env().get_connection_url()
        # The Supabase transaction pooler (port 6543) multiplexes many clients over one
        # server connection. asyncpg's default sequential statement names
        # (`__asyncpg_stmt_N__`) then collide across clients with
        # `prepared statement "..." already exists`, so every prepared statement gets a
        # unique name (SQLAlchemy's documented PgBouncer workaround). The URL also sets
        # `prepared_statement_cache_size=0` — the asyncpg counterpart of JDBC's
        # `prepareThreshold=0` used in GEO_ETL.
        self.db_engine = db_engine or create_async_engine(
            self.connection_url,
            connect_args={"prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__"},
        )
        self.logger = logger or logging.getLogger(__name__)

    def _endpoint_logger(self) -> logging.Logger:
        """Return the calling endpoint's logger, or the provider's own logger outside a request.

        During a request the route wrapper (``routes/logging_route.py``) publishes its
        logger via ``util.endpoint_logger``; providers log through it so database
        records land in the endpoint's log file.
        """
        return util.endpoint_logger.get() or self.logger

    def _sql_text(self, statement: Select | SelectOfScalar) -> str:
        """Return the statement's SQL on a single line, with bound parameters appended.

        Args:
            statement: SQLModel select statement.

        Returns:
            The compiled SQL (whitespace collapsed), `` | params={...}`` when the
            statement has bound parameters.
        """
        compiled = statement.compile(dialect=self.db_engine.dialect)
        sql = " ".join(str(compiled).split())
        if compiled.params:
            return f"{sql} | params={compiled.params}"
        return sql

    async def connect(self) -> None:
        """Verify that the database is reachable by running ``SELECT 1``.

        Logs ``Connected to Supabase Postgres`` on success (to the calling
        endpoint's log file during a request).

        Raises:
            SupabaseServerDownError: If the connection cannot be established.
        """
        log = self._endpoint_logger()
        try:
            async with self.db_engine.connect() as connection:
                await connection.execute(sqlalchemy.text("SELECT 1"))
        except CONNECTION_ERRORS as e:
            log.error(f"Supabase Postgres DB server is down. Message: {e}")
            raise error.SupabaseServerDownError(f"Supabase Postgres DB server is down. Message: {e}") from e
        log.info("Connected to Supabase Postgres")

    def get_logger(self) -> logging.Logger:
        """Return the provider's logger."""
        return self.logger

    def get_db_engine(self) -> AsyncEngine:
        """Return the async SQLAlchemy engine."""
        return self.db_engine

    async def create_table_if_not_exists(self, entity: type[SQLModel], table: str, schema: str) -> None:
        """Create a table if it does not exist.

        Args:
            entity: SQLModel table class (``table=True``) defining the schema.
            table: Table name.
            schema: Schema name (e.g. ``"geo"``).

        Raises:
            SupabaseServerDownError: If the database cannot be reached.
        """
        log = self._endpoint_logger()
        try:
            async with self.db_engine.connect() as connection:
                has_table = await connection.run_sync(
                    lambda sync_conn: sqlalchemy.inspect(sync_conn).has_table(table_name=table, schema=schema)
                )
            if has_table:
                return
            async with self.db_engine.begin() as connection:
                await connection.run_sync(
                    lambda sync_conn: SQLModel.metadata.create_all(
                        sync_conn,
                        tables=[entity.__table__],  # type: ignore[attr-defined]
                    )
                )
            log.info(f"Table '{schema}.{table}' created.")
        except CONNECTION_ERRORS as e:
            log.error(f"Supabase Postgres DB server is down. Message: {e}")
            raise error.SupabaseServerDownError(f"Supabase Postgres DB server is down. Message: {e}") from e

    async def run_select_statement(self, statement: Select | SelectOfScalar) -> Sequence[Any]:
        """Execute a select statement and return the results.

        ``Result.all()`` already materializes the rows into a fresh list, so
        it is returned as-is — no second copy of the result set is made, which
        keeps the peak allocation of this stage at one list of rows.

        Logs to the calling endpoint's log file (via ``util.endpoint_logger``):
        ``Connected to Supabase Postgres`` once a connection is checked out,
        ``Executing SQL: ...`` with the compiled statement, and
        ``Returned N records`` on success.

        Args:
            statement: SQLModel select statement.

        Returns:
            The query results (the driver's row list, owned by this call).

        Raises:
            SupabaseServerDownError: If the database cannot be reached.
        """
        log = self._endpoint_logger()
        try:
            async with AsyncSession(self.db_engine) as session:
                await session.connection()  # checks a connection out of the pool (connects if needed)
                log.info("Connected to Supabase Postgres")
                log.info(f"Executing SQL: {self._sql_text(statement)}")
                result = await session.exec(statement)
                rows = result.all()
            log.info(f"Returned {len(rows)} records")
            return rows
        except CONNECTION_ERRORS as e:
            log.error(f"Supabase Postgres DB server is down. Message: {e}")
            raise error.SupabaseServerDownError(f"Supabase Postgres DB server is down. Message: {e}") from e

    async def run_insert_statement(
        self, entities: list[SQLModel], batch_size: int, num_entities: int = 10000, name: str = "entities"
    ) -> None:
        """Insert entities into the database in batches.

        One transaction per batch; progress is logged after each commit.
        Chunks are pulled lazily from ``util.chunk_list_equal_size``, so only
        the batch being written is held in addition to the input list.

        Args:
            entities: Rows to insert.
            batch_size: Number of rows per transaction.
            num_entities: Total number of entities (for progress logging).
            name: Entity name used in log messages.

        Raises:
            SupabaseServerDownError: If the database cannot be reached.
        """
        log = self._endpoint_logger()
        try:
            chunks = util.chunk_list_equal_size(entities, batch_size)
            async with AsyncSession(self.db_engine, expire_on_commit=False) as session:
                num_inserted = 0
                for chunk in chunks:
                    session.add_all(chunk)
                    await session.commit()
                    num_inserted += len(chunk)
                    log.info(f"{name.capitalize()}: {num_inserted} out of {num_entities}")
        except CONNECTION_ERRORS as e:
            log.error(f"Supabase Postgres DB server is down. Message: {e}")
            raise error.SupabaseServerDownError(f"Supabase Postgres DB server is down. Message: {e}") from e

    async def close(self) -> None:
        """Dispose the engine's connection pool."""
        await self.db_engine.dispose()


_provider: SupabasePostgresProvider | None = None


def get_provider() -> SupabasePostgresProvider:
    """Return the process-wide :class:`SupabasePostgresProvider`, creating it on first use.

    Returns:
        The shared provider instance.
    """
    global _provider
    if _provider is None:
        _provider = SupabasePostgresProvider()
    return _provider


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a SQLModel ``AsyncSession`` — use with FastAPI's ``Depends``.

    Example::

        @app.get("/events")
        async def list_events(session: AsyncSession = Depends(get_session)):
            ...

    Yields:
        An open async session bound to the shared provider's engine.
    """
    async with AsyncSession(get_provider().db_engine) as session:
        yield session


async def dispose_provider() -> None:
    """Dispose the shared provider's engine pool and reset the singleton.

    Called from the FastAPI lifespan on shutdown; a no-op when no provider
    was ever created (e.g. in unit tests that never touch the database).
    """
    global _provider
    if _provider is not None:
        await _provider.close()
        _provider = None
