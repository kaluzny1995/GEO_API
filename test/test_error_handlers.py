"""Tests for the global exception handlers."""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from error_handlers import InternalServerErrorMiddleware
from model.message import ResponseMessage


def _app_with_boom() -> FastAPI:
    """Build a CORS-enabled app whose route raises an unhandled exception."""
    app = FastAPI()
    app.add_middleware(InternalServerErrorMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"])

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("database connection exploded")

    return app


class TestInternalServerErrorMiddleware:
    """Tests for :class:`error_handlers.InternalServerErrorMiddleware`."""

    def test_unhandled_error_returns_json_500_with_cors_headers(self) -> None:
        """A browser sees a real 500 response, not an opaque CORS failure."""
        # Arrange
        app = _app_with_boom()

        # Act
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/boom", headers={"Origin": "http://localhost:3000"})

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        message = ResponseMessage(**response.json())
        assert message.title == "Internal Server Error."
        assert message.description == "An unexpected error occurred."
        assert message.code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_unhandled_error_does_not_leak_internal_details(self) -> None:
        """The generic response never echoes the exception message."""
        # Arrange
        app = _app_with_boom()

        # Act
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/boom", headers={"Origin": "http://localhost:3000"})

        # Assert
        assert "database connection exploded" not in response.text
