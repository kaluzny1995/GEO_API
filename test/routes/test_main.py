"""Tests for the main router (root, hello, health)."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from starlette.testclient import TestClient

import error
from model.message import ResponseMessage


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Yield a TestClient for the FastAPI app (runs lifespan)."""
    from main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "endpoint_url, expected_title",
    [
        ("/", "Hello GEO_API"),
        ("/hello", "Hello GEO_API"),
    ],
)
def test_hello_endpoints_return_200(client: TestClient, endpoint_url: str, expected_title: str) -> None:
    """Root and hello endpoints return a 200 greeting message."""
    # Arrange
    # Act
    response = client.get(endpoint_url)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    message = ResponseMessage(**response.json())
    assert message.title == expected_title
    assert message.description == "Successful response."
    assert message.code == status.HTTP_200_OK


@pytest.mark.parametrize(
    ("connect_effect", "status_code", "title"),
    [
        (None, status.HTTP_200_OK, "Healthy"),
        (
            error.SupabaseServerDownError("Supabase Postgres DB server is down."),
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Service Unavailable.",
        ),
    ],
)
def test_health_reflects_database_reachability(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    connect_effect: Exception | None,
    status_code: int,
    title: str,
) -> None:
    """Health returns 200 when the provider connects and 503 when it cannot."""
    # Arrange
    mock_provider = MagicMock()
    mock_provider.connect = AsyncMock(side_effect=connect_effect)
    monkeypatch.setattr("routes.main.get_provider", lambda: mock_provider)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == status_code
    message = ResponseMessage(**response.json())
    assert message.title == title
    assert message.code == status_code
    mock_provider.connect.assert_awaited_once()
