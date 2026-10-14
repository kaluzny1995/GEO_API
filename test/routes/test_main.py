"""Tests for the main router (root, hello, health)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from starlette.testclient import TestClient

import error
from model.message import ResponseMessage


@pytest.fixture()
def client():
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
def test_hello_endpoints_return_200(client, endpoint_url: str, expected_title: str):
    # Arrange
    # Act
    response = client.get(endpoint_url)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    message = ResponseMessage(**response.json())
    assert message.title == expected_title
    assert message.description == "Successful response."
    assert message.code == status.HTTP_200_OK


def test_health_returns_200_when_database_is_reachable(client, monkeypatch):
    # Arrange
    mock_provider = MagicMock()
    mock_provider.connect = AsyncMock()
    monkeypatch.setattr("routes.main.get_provider", lambda: mock_provider)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    message = ResponseMessage(**response.json())
    assert message.title == "Healthy"
    assert message.code == status.HTTP_200_OK
    mock_provider.connect.assert_awaited_once()


def test_health_returns_503_when_database_is_down(client, monkeypatch):
    # Arrange
    mock_provider = MagicMock()
    mock_provider.connect = AsyncMock(side_effect=error.SupabaseServerDownError("Supabase Postgres DB server is down."))
    monkeypatch.setattr("routes.main.get_provider", lambda: mock_provider)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    message = ResponseMessage(**response.json())
    assert message.title == "Service Unavailable."
    assert message.code == status.HTTP_503_SERVICE_UNAVAILABLE
