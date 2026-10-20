"""Tests for the per-endpoint LoggingRoute (no network, no database)."""

import logging
from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import APIRouter, FastAPI, HTTPException, status
from starlette.testclient import TestClient

import util
from routes.logging_route import LoggingRoute

# Endpoint names are logger names — unique per test run so the tests never
# share handlers with each other or with the main-app route tests.
_SUFFIX = uuid4().hex[:8]
_OK = f"ok_{_SUFFIX}"
_QUERY = f"query_{_SUFFIX}"
_BOOM = f"boom_{_SUFFIX}"
_CLIENT_ERROR = f"client_error_{_SUFFIX}"
_CTX = f"ctx_{_SUFFIX}"

# Records what util.endpoint_logger holds while the /ctx endpoint runs.
_SEEN_DURING_REQUEST: list[Any] = []


@pytest.fixture()
def app() -> FastAPI:
    """Build a fresh app whose routes use LoggingRoute (fresh loggers per test)."""
    router = APIRouter(route_class=LoggingRoute)

    @router.get("/ok", tags=["logging-test"], name=_OK)
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/query", tags=["logging-test"], name=_QUERY)
    async def query(q: str = "") -> dict[str, str]:
        return {"q": q}

    @router.get("/boom", tags=["logging-test"], name=_BOOM)
    async def boom() -> None:
        raise RuntimeError("boom")

    @router.get("/client-error", tags=["logging-test"], name=_CLIENT_ERROR)
    async def client_error() -> None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="missing")

    @router.get("/ctx", tags=["logging-test"], name=_CTX)
    async def ctx() -> dict[str, str]:
        _SEEN_DURING_REQUEST.append(util.endpoint_logger.get())
        return {"status": "ok"}

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture()
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Yield a TestClient, then close every handler this app's loggers added."""
    with TestClient(app) as test_client:
        yield test_client
    for endpoint_name in (_OK, _QUERY, _BOOM, _CLIENT_ERROR, _CTX):
        logger = logging.getLogger(f"geo_api.{endpoint_name}")
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)


def _endpoint_log_file(tmp_path: Any, endpoint_name: str) -> Any:
    """Return the endpoint's single log file (call after a request created it)."""
    files = list((tmp_path / "logging_test").glob(f"{endpoint_name}_*.log"))
    assert len(files) == 1
    return files[0]


class TestLoggingRoute:
    """Tests for :class:`routes.logging_route.LoggingRoute`."""

    def test_request_logs_start_and_finish_to_endpoint_file(self, client: TestClient, tmp_path: Any) -> None:
        """A request writes a start line and a finish line with status and timing."""
        # Act
        response = client.get("/ok")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        content = _endpoint_log_file(tmp_path, _OK).read_text()
        assert "GET /ok started" in content
        assert "GET /ok finished with 200 in" in content

    def test_one_file_per_endpoint_for_repeated_requests(self, client: TestClient, tmp_path: Any) -> None:
        """Repeated requests append to the same file — one file per endpoint per run."""
        # Act
        client.get("/ok")
        client.get("/ok")

        # Assert
        log_file = _endpoint_log_file(tmp_path, _OK)
        assert log_file.read_text().count("GET /ok started") == 2

    def test_query_string_is_logged(self, client: TestClient, tmp_path: Any) -> None:
        """The target line includes the query string when present."""
        # Act
        response = client.get("/query", params={"q": "hello"})

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "GET /query?q=hello finished with 200 in" in _endpoint_log_file(tmp_path, _QUERY).read_text()

    def test_unhandled_error_logs_traceback_and_propagates(self, client: TestClient, tmp_path: Any) -> None:
        """An unhandled error is logged with a full traceback and re-raised (→ 500)."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="boom"):
            client.get("/boom")

        # Assert
        content = _endpoint_log_file(tmp_path, _BOOM).read_text()
        assert "GET /boom failed after" in content
        assert "RuntimeError: boom" in content

    def test_http_exception_is_logged_as_warning_without_traceback(self, client: TestClient, tmp_path: Any) -> None:
        """A client error (4xx) is logged as a warning — no traceback noise."""
        # Act
        response = client.get("/client-error")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        content = _endpoint_log_file(tmp_path, _CLIENT_ERROR).read_text()
        assert "GET /client-error finished with 404 in" in content
        assert "Traceback" not in content

    def test_file_is_created_under_tag_directory(self, client: TestClient, tmp_path: Any) -> None:
        """The file path is ``<root>/<tag_snake>/<endpoint>_<timestamp>.log``."""
        # Act
        client.get("/ok")

        # Assert
        assert _endpoint_log_file(tmp_path, _OK).name.startswith(f"{_OK}_20")

    def test_handler_named_root_does_not_collide_with_root_logger(self, tmp_path: Any) -> None:
        """An endpoint handler named ``root`` logs only its own requests (namespace ``geo_api.``)."""
        # Arrange
        other_name = f"other_{_SUFFIX}"
        router = APIRouter(route_class=LoggingRoute)

        @router.get("/root-endpoint", tags=["logging-test"], name="root")
        async def root_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        @router.get("/other-endpoint", tags=["logging-test"], name=other_name)
        async def other_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        app = FastAPI()
        app.include_router(router)

        # Act
        with TestClient(app) as client:
            client.get("/root-endpoint")
            client.get("/other-endpoint")

        # Assert
        root_file = _endpoint_log_file(tmp_path, "root")
        content = root_file.read_text()
        assert "GET /root-endpoint started" in content
        assert "other-endpoint" not in content

        # Cleanup
        for logger_name in ("geo_api.root", f"geo_api.{other_name}"):
            logger = logging.getLogger(logger_name)
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)

    def test_context_logger_is_set_during_request_and_reset_after(self, client: TestClient) -> None:
        """During a request ``util.endpoint_logger`` holds the endpoint's logger; after it, None.

        Providers read this context variable, so their database records (connection,
        SQL, row counts) land in the calling endpoint's log file.
        """
        # Arrange
        _SEEN_DURING_REQUEST.clear()

        # Act
        response = client.get("/ctx")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        (seen_logger,) = _SEEN_DURING_REQUEST
        assert seen_logger is not None
        assert seen_logger.name == f"geo_api.{_CTX}"
        assert util.endpoint_logger.get() is None
