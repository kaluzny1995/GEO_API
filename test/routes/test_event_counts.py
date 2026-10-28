"""Tests for the event counts router (provider mocked via dependency override)."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from starlette.testclient import TestClient

from main import app
from model.event_count import EventCategoryCount, EventLocationCount
from routes.event_counts import get_event_counts_provider

CATEGORY_ROWS = [
    EventCategoryCount(
        source_name="AVALANCHE_ORG",
        subsource_name="Bridgeport Avalanche Center",
        event_category="avalanche",
        event_subcategory=None,
        danger_rating="no_rating",
        count=39,
    ),
    EventCategoryCount(
        source_name="GDACS",
        subsource_name=None,
        event_category="earthquake",
        event_subcategory="tsunami",
        danger_rating="medium",
        count=12,
    ),
]
LOCATION_ROWS = [
    EventLocationCount(
        source_name="AVALANCHE_ORG",
        subsource_name="Bridgeport Avalanche Center",
        country_code="US",
        state_province="CA",
        danger_rating="no_rating",
        count=39,
    ),
    EventLocationCount(
        source_name="GDACS",
        subsource_name=None,
        country_code="JP",
        state_province=None,
        danger_rating="medium",
        count=12,
    ),
]


@pytest.fixture()
def mock_provider() -> MagicMock:
    """Event counts provider mock returning CATEGORY_ROWS / LOCATION_ROWS per method."""
    provider = MagicMock()
    provider.get_event_counts_by_category = AsyncMock(return_value=list(CATEGORY_ROWS))
    provider.get_event_counts_by_location = AsyncMock(return_value=list(LOCATION_ROWS))
    return provider


@pytest.fixture()
def client(mock_provider: MagicMock) -> Generator[TestClient, None, None]:
    """Yield a TestClient with the provider dependency overridden by mock_provider."""
    app.dependency_overrides[get_event_counts_provider] = lambda: mock_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("path", "method", "other_method", "rows", "expected_fields"),
    [
        pytest.param(
            "/event-counts/category",
            "get_event_counts_by_category",
            "get_event_counts_by_location",
            CATEGORY_ROWS,
            {"source_name", "subsource_name", "event_category", "event_subcategory", "danger_rating", "count"},
            id="category",
        ),
        pytest.param(
            "/event-counts/location",
            "get_event_counts_by_location",
            "get_event_counts_by_category",
            LOCATION_ROWS,
            {"source_name", "subsource_name", "country_code", "state_province", "danger_rating", "count"},
            id="location",
        ),
    ],
)
def test_endpoint_returns_200_with_counts(
    client: TestClient,
    mock_provider: MagicMock,
    path: str,
    method: str,
    other_method: str,
    rows: list[EventCategoryCount] | list[EventLocationCount],
    expected_fields: set[str],
) -> None:
    """Both count endpoints return their grouped rows with the exact response fields."""
    # Act
    response = client.get(path)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 2
    assert set(body[0]) == expected_fields
    assert body[0] == rows[0].model_dump()
    assert body[1] == rows[1].model_dump()
    getattr(mock_provider, method).assert_awaited_once_with(limit=100)
    getattr(mock_provider, other_method).assert_not_awaited()


@pytest.mark.parametrize(
    ("path", "method"),
    [
        pytest.param("/event-counts/category", "get_event_counts_by_category", id="category"),
        pytest.param("/event-counts/location", "get_event_counts_by_location", id="location"),
    ],
)
def test_endpoint_returns_empty_list_when_no_groups(
    client: TestClient, mock_provider: MagicMock, path: str, method: str
) -> None:
    """An empty provider result is returned as an empty JSON list."""
    # Arrange
    getattr(mock_provider, method).return_value = []

    # Act
    response = client.get(path)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.parametrize("limit", [1, 5, 1000])
def test_endpoint_forwards_an_in_range_limit(client: TestClient, mock_provider: MagicMock, limit: int) -> None:
    """A limit within 1..1000 reaches the provider unchanged."""
    # Act
    response = client.get("/event-counts/category", params={"limit": limit})

    # Assert
    assert response.status_code == status.HTTP_200_OK
    mock_provider.get_event_counts_by_category.assert_awaited_once_with(limit=limit)


@pytest.mark.parametrize("limit", [0, -5, 1001])
def test_endpoint_rejects_an_out_of_range_limit(client: TestClient, mock_provider: MagicMock, limit: int) -> None:
    """Limits outside 1..1000 fail validation (422) and never call the provider."""
    # Act
    response = client.get("/event-counts/location", params={"limit": limit})

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_provider.get_event_counts_by_location.assert_not_awaited()
