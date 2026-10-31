"""Tests for the data quantity router (provider mocked via dependency override)."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from starlette.testclient import TestClient

from main import app
from model.data_quantity import OVERALL_FILE_DATE, TableCount
from routes.data_quantity import get_data_quantity_provider
from util import HTTP_422_UNPROCESSABLE

ROWS = [
    TableCount(table_name="eonet_event", file_date="2026-10-26", count=4),
    TableCount(table_name="eonet_event_etl", file_date="2026-10-26", count=4),
    TableCount(table_name="union_etl", file_date="2026-10-26", count=717),
]


@pytest.fixture()
def mock_provider() -> MagicMock:
    """Data quantity provider mock returning ROWS and a date list."""
    provider = MagicMock()
    provider.get_table_counts = AsyncMock(return_value=list(ROWS))
    provider.get_file_dates = AsyncMock(return_value=["2026-10-25", "2026-10-26", OVERALL_FILE_DATE])
    return provider


@pytest.fixture()
def client(mock_provider: MagicMock) -> Generator[TestClient, None, None]:
    """Yield a TestClient with the provider dependency overridden by mock_provider."""
    app.dependency_overrides[get_data_quantity_provider] = lambda: mock_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestGetDataQuantity:
    """Tests for the actual row-count endpoint."""

    @pytest.mark.parametrize("file_date", ["2026-10-26", OVERALL_FILE_DATE])
    def test_endpoint_returns_200_with_counts(
        self, client: TestClient, mock_provider: MagicMock, file_date: str
    ) -> None:
        """A dated or overall snapshot returns the provider's count rows."""
        # Act
        response = client.get(f"/data-quantity/{file_date}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 3
        assert set(body[0]) == {"table_name", "file_date", "count"}
        assert body[2] == {"table_name": "union_etl", "file_date": "2026-10-26", "count": 717}
        mock_provider.get_table_counts.assert_awaited_once_with(file_date)

    def test_endpoint_returns_empty_list_when_no_counts(self, client: TestClient, mock_provider: MagicMock) -> None:
        """An empty provider result is returned as an empty JSON list."""
        # Arrange
        mock_provider.get_table_counts = AsyncMock(return_value=[])

        # Act
        response = client.get("/data-quantity/2026-10-26")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.parametrize("file_date", ["yesterday", "2026-13-01", "2026-1-1", "2026-10-26T00:00:00"])
    def test_endpoint_rejects_an_invalid_file_date(
        self, client: TestClient, mock_provider: MagicMock, file_date: str
    ) -> None:
        """Anything that is not overall or YYYY-MM-DD fails validation (422)."""
        # Act
        response = client.get(f"/data-quantity/{file_date}")

        # Assert
        assert response.status_code == HTTP_422_UNPROCESSABLE
        mock_provider.get_table_counts.assert_not_awaited()


class TestGetDataQuantityFileDates:
    """Tests for the snapshot-date discovery endpoint."""

    def test_dates_endpoint_returns_the_union_dates(self, client: TestClient, mock_provider: MagicMock) -> None:
        """GET /data-quantity/dates returns the provider's date list."""
        # Act
        response = client.get("/data-quantity/dates")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == ["2026-10-25", "2026-10-26", OVERALL_FILE_DATE]
        mock_provider.get_file_dates.assert_awaited_once_with()

    def test_dates_endpoint_is_not_captured_by_the_file_date_route(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """`/dates` must resolve to discovery, not `/{file_date}`."""
        # Act
        response = client.get("/data-quantity/dates")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_provider.get_file_dates.assert_awaited_once()
        mock_provider.get_table_counts.assert_not_awaited()
