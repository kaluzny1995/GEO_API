"""Tests for the Supabase Postgres base provider (session faked, no network)."""

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import sqlalchemy.exc
from sqlmodel import select

import error
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

        async def exec(self, _statement: Any) -> _FakeResult:
            if exc is not None:
                raise exc
            return _FakeResult(rows or [])

    monkeypatch.setattr(provider_module, "AsyncSession", _FakeSession)


@pytest.fixture
def db_engine() -> MagicMock:
    """Async engine mock whose dispose() is awaitable."""
    engine = MagicMock()
    engine.dispose = AsyncMock()
    return engine


@pytest.fixture
def provider(db_engine: MagicMock) -> SupabasePostgresProvider:
    """Provider built from explicit arguments — no ``.env`` read, no real engine."""
    return SupabasePostgresProvider(
        connection_url="postgresql+asyncpg://user:password@localhost:5432/postgres",
        db_engine=db_engine,
        logger=logging.getLogger("test_supabase_postgres_provider"),
    )


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
