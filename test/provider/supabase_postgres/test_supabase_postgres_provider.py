"""Tests for the Supabase Postgres base provider (session faked, no network)."""

import logging
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import sqlalchemy.exc
from sqlalchemy.dialects import postgresql
from sqlmodel import select

import error
import util
from model.data_quality import DataQuality
from provider.supabase_postgres import supabase_postgres_provider as provider_module
from provider.supabase_postgres.supabase_postgres_provider import CONNECTION_ERRORS, SupabasePostgresProvider

# Rows as the driver's Result.all() would return them — the very list object tests assert on.
ROWS: list[Any] = [("AVALANCHE_ORG", 39), ("GDACS", 12)]


class _FakeResult:
    """Stand-in for SQLModel's result object: ``all()`` hands back the canned list."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _ListHandler(logging.Handler):
    """Handler that collects log messages — asserts what a logger received."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _patch_session(
    monkeypatch: pytest.MonkeyPatch, rows: list[Any] | None = None, exc: Exception | None = None
) -> None:
    """Replace the module's AsyncSession with a fake returning *rows* or raising *exc*."""

    class _FakeSession:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "_FakeSession":
            return self

        async def __aexit__(self, *_exc_info: Any) -> bool:
            return False

        async def connection(self) -> Any:
            return MagicMock()

        async def exec(self, _statement: Any) -> _FakeResult:
            if exc is not None:
                raise exc
            return _FakeResult(rows or [])

    monkeypatch.setattr(provider_module, "AsyncSession", _FakeSession)


@pytest.fixture
def db_engine() -> MagicMock:
    """Async engine mock with a real asyncpg dialect and an awaitable dispose()."""
    engine = MagicMock()
    engine.dispose = AsyncMock()
    engine.dialect = postgresql.asyncpg.dialect()
    return engine


@pytest.fixture
def provider(db_engine: MagicMock) -> SupabasePostgresProvider:
    """Provider built from explicit arguments — no ``.env`` read, no real engine."""
    return SupabasePostgresProvider(
        connection_url="postgresql+asyncpg://user:password@localhost:5432/postgres",
        db_engine=db_engine,
        logger=logging.getLogger("test_supabase_postgres_provider"),
    )


@pytest.fixture()
def endpoint_logger() -> Iterator[tuple[logging.Logger, _ListHandler]]:
    """Publish an endpoint logger via ``util.endpoint_logger`` for the duration of the test."""
    logger = logging.getLogger(f"test_endpoint_logger_{uuid4().hex}")
    logger.setLevel(logging.INFO)
    handler = _ListHandler()
    logger.addHandler(handler)
    token = util.endpoint_logger.set(logger)
    yield logger, handler
    util.endpoint_logger.reset(token)
    logger.removeHandler(handler)


class TestRunSelectStatement:
    """Tests for :meth:`SupabasePostgresProvider.run_select_statement`."""

    async def test_returns_the_result_list_unchanged(
        self, provider: SupabasePostgresProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The driver's row list is returned as-is — no duplicate copy is made."""
        # Arrange
        _patch_session(monkeypatch, rows=ROWS)

        # Act
        result = await provider.run_select_statement(select(DataQuality))

        # Assert
        assert result is ROWS
        assert list(result) == [("AVALANCHE_ORG", 39), ("GDACS", 12)]

    @pytest.mark.parametrize(
        "connection_error",
        [
            sqlalchemy.exc.OperationalError("SELECT 1", {}, Exception("connection refused")),
            sqlalchemy.exc.InterfaceError("SELECT 1", {}, Exception("interface closed")),
            OSError("network unreachable"),
        ],
    )
    async def test_connection_errors_are_wrapped(
        self, provider: SupabasePostgresProvider, monkeypatch: pytest.MonkeyPatch, connection_error: Exception
    ) -> None:
        """Every connection-level failure surfaces as SupabaseServerDownError (→ 503)."""
        # Arrange
        _patch_session(monkeypatch, exc=connection_error)

        # Act & Assert
        with pytest.raises(error.SupabaseServerDownError) as exc_info:
            await provider.run_select_statement(select(DataQuality))

        assert str(connection_error) in str(exc_info.value)


class TestLogger:
    """Tests for the provider's default logger."""

    def test_default_logger_is_module_logger_without_file_handlers(self, db_engine: MagicMock) -> None:
        """No ``logs/supabase/`` file is created — the module logger owns no handlers."""
        # Act
        provider = SupabasePostgresProvider(
            connection_url="postgresql+asyncpg://user:password@localhost:5432/postgres",
            db_engine=db_engine,
        )

        # Assert
        assert provider.logger.name == provider_module.__name__
        assert provider.logger.handlers == []


class TestEndpointLogging:
    """Tests for the endpoint-aware database logging of :class:`SupabasePostgresProvider`."""

    async def test_run_select_logs_connection_sql_and_row_count(
        self, provider: SupabasePostgresProvider, monkeypatch: pytest.MonkeyPatch, endpoint_logger: Any
    ) -> None:
        """A successful select logs connection, the launched SQL and the returned row count."""
        # Arrange
        _, handler = endpoint_logger
        _patch_session(monkeypatch, rows=ROWS)

        # Act
        result = await provider.run_select_statement(select(DataQuality))

        # Assert
        assert result is ROWS
        assert "Connected to Supabase Postgres" in handler.messages
        sql_message = next(message for message in handler.messages if message.startswith("Executing SQL:"))
        assert "SELECT" in sql_message
        assert "data_quality" in sql_message
        assert "Returned 2 records" in handler.messages

    async def test_run_select_logs_bound_parameters(
        self, provider: SupabasePostgresProvider, monkeypatch: pytest.MonkeyPatch, endpoint_logger: Any
    ) -> None:
        """The SQL line appends the statement's bound parameters (table, file_date, ...)."""
        # Arrange
        _, handler = endpoint_logger
        _patch_session(monkeypatch, rows=[])

        # Act
        await provider.run_select_statement(select(DataQuality).where(DataQuality.table_name == "usgs_earthquake"))

        # Assert
        sql_message = next(message for message in handler.messages if message.startswith("Executing SQL:"))
        assert "params=" in sql_message
        assert "usgs_earthquake" in sql_message

    async def test_connect_logs_connected(self, provider: SupabasePostgresProvider, endpoint_logger: Any) -> None:
        """A successful health check logs 'Connected to Supabase Postgres'."""
        # Arrange
        _, handler = endpoint_logger
        connection = MagicMock()
        connection.execute = AsyncMock()
        connection_context = MagicMock()
        connection_context.__aenter__ = AsyncMock(return_value=connection)
        connection_context.__aexit__ = AsyncMock(return_value=False)
        provider.db_engine.connect = MagicMock(return_value=connection_context)

        # Act
        await provider.connect()

        # Assert
        assert "Connected to Supabase Postgres" in handler.messages

    async def test_without_endpoint_logger_falls_back_to_provider_logger(
        self, provider: SupabasePostgresProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Outside a request the records go to the provider's own logger."""
        # Arrange
        handler = _ListHandler()
        provider.logger.setLevel(logging.INFO)
        provider.logger.addHandler(handler)
        _patch_session(monkeypatch, rows=ROWS)

        # Act
        try:
            await provider.run_select_statement(select(DataQuality))
        finally:
            provider.logger.removeHandler(handler)

        # Assert
        assert "Connected to Supabase Postgres" in handler.messages
        assert "Returned 2 records" in handler.messages


class TestClose:
    """Tests for :meth:`SupabasePostgresProvider.close`."""

    async def test_close_disposes_the_engine_pool(
        self, provider: SupabasePostgresProvider, db_engine: MagicMock
    ) -> None:
        """Shutdown releases the pool (the lifespan hook relies on this)."""
        # Act
        await provider.close()

        # Assert
        db_engine.dispose.assert_awaited_once()

    def test_connection_errors_constant_covers_expected_types(self) -> None:
        """The wrapped error set stays the contract every provider method relies on."""
        assert (
            sqlalchemy.exc.OperationalError,
            sqlalchemy.exc.InterfaceError,
            OSError,
        ) == CONNECTION_ERRORS
