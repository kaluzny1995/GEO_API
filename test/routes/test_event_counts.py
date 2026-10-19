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


class TestGetEventCountsByCategory:
    """Tests for the event taxonomy count endpoint."""

    def test_category_endpoint_returns_200_with_counts(self, client: TestClient, mock_provider: MagicMock) -> None:
        """Category endpoint returns 200 with the grouped count rows."""
        # Act
        response = client.get("/event-counts/category")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 2
        assert set(body[0]) == {
            "source_name",
            "subsource_name",
            "event_category",
            "event_subcategory",
            "danger_rating",
            "count",
        }
        assert body[0]["source_name"] == "AVALANCHE_ORG"
        assert body[0]["event_category"] == "avalanche"
        assert body[0]["event_subcategory"] is None
        assert body[0]["danger_rating"] == "no_rating"
        assert body[0]["count"] == 39
        assert body[1]["event_subcategory"] == "tsunami"
        mock_provider.get_event_counts_by_category.assert_awaited_once_with()
        mock_provider.get_event_counts_by_location.assert_not_awaited()

    def test_category_endpoint_returns_empty_list_when_no_groups(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """An empty provider result is returned as an empty JSON list."""
        # Arrange
        mock_provider.get_event_counts_by_category = AsyncMock(return_value=[])

        # Act
        response = client.get("/event-counts/category")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


class TestGetEventCountsByLocation:
    """Tests for the location count endpoint."""

    def test_location_endpoint_returns_200_with_counts(self, client: TestClient, mock_provider: MagicMock) -> None:
        """Location endpoint returns 200 with the grouped count rows."""
        # Act
        response = client.get("/event-counts/location")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 2
        assert set(body[0]) == {
            "source_name",
            "subsource_name",
            "country_code",
            "state_province",
            "danger_rating",
            "count",
        }
        assert body[0]["source_name"] == "AVALANCHE_ORG"
        assert body[0]["country_code"] == "US"
        assert body[0]["state_province"] == "CA"
        assert body[0]["danger_rating"] == "no_rating"
        assert body[0]["count"] == 39
        assert body[1]["state_province"] is None
        mock_provider.get_event_counts_by_location.assert_awaited_once_with()
        mock_provider.get_event_counts_by_category.assert_not_awaited()

    def test_location_endpoint_returns_empty_list_when_no_groups(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """An empty provider result is returned as an empty JSON list."""
        # Arrange
        mock_provider.get_event_counts_by_location = AsyncMock(return_value=[])

        # Act
        response = client.get("/event-counts/location")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
