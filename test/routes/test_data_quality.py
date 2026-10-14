"""Tests for the data quality router (provider mocked via dependency override)."""

import datetime as dt
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from starlette.testclient import TestClient

from main import app
from model.data_quality import DataQuality
from routes.data_quality import get_data_quality_provider

ROWS = [
    DataQuality(
        table_name="usgs_earthquake",
        file_date="overall",
        metric="bad_row_pct",
        value=0.001,
        computed_at=dt.datetime(2026, 9, 21, 2, 15, 0),
    ),
    DataQuality(
        table_name="usgs_earthquake",
        file_date="overall",
        metric="total_records",
        value=12345.0,
        computed_at=dt.datetime(2026, 9, 21, 2, 15, 0),
    ),
]


@pytest.fixture()
def mock_provider() -> MagicMock:
    """Data quality provider mock returning ROWS from both read methods."""
    provider = MagicMock()
    provider.get_data_quality = AsyncMock(return_value=list(ROWS))
    provider.get_data_quality_for_file_dates = AsyncMock(return_value=list(ROWS))
    return provider


@pytest.fixture()
def client(mock_provider: MagicMock) -> Generator[TestClient, None, None]:
    """Yield a TestClient with the provider dependency overridden by mock_provider."""
    app.dependency_overrides[get_data_quality_provider] = lambda: mock_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestGetDataQuality:
    """Tests for the single-date data quality endpoints."""

    def test_overall_endpoint_returns_200_with_metrics(self, client: TestClient, mock_provider: MagicMock) -> None:
        """Overall endpoint returns 200 with the metric rows."""
        # Act
        response = client.get("/data-quality/usgs_earthquake")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 2
        assert body[0]["table_name"] == "usgs_earthquake"
        assert body[0]["file_date"] == "overall"
        assert body[0]["metric"] == "bad_row_pct"
        assert body[0]["value"] == 0.001
        assert body[1]["metric"] == "total_records"
        mock_provider.get_data_quality.assert_awaited_once_with("usgs_earthquake")

    def test_file_date_endpoint_returns_200_with_metrics(self, client: TestClient, mock_provider: MagicMock) -> None:
        """Date endpoint forwards table_name and file_date to the provider."""
        # Act
        response = client.get("/data-quality/usgs_earthquake/2026-09-20")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 2
        assert body[0]["file_date"] == "overall"  # mocked rows keep their own file_date
        mock_provider.get_data_quality.assert_awaited_once_with("usgs_earthquake", "2026-09-20")

    def test_overall_endpoint_returns_empty_list_when_no_metrics(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """An empty provider result is returned as an empty JSON list."""
        # Arrange
        mock_provider.get_data_quality = AsyncMock(return_value=[])

        # Act
        response = client.get("/data-quality/unknown_table")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


class TestGetDataQualityForFileDates:
    """Tests for the many-file-dates data quality endpoint."""

    def test_file_dates_endpoint_returns_200_with_metrics(self, client: TestClient, mock_provider: MagicMock) -> None:
        """Repeated file_dates params are forwarded as a date list."""
        # Act
        response = client.get(
            "/data-quality/usgs_earthquake/file-dates",
            params={"file_dates": ["2026-09-19", "2026-09-20"]},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 2
        assert body[0]["metric"] == "bad_row_pct"
        mock_provider.get_data_quality_for_file_dates.assert_awaited_once_with(
            "usgs_earthquake", ["2026-09-19", "2026-09-20"]
        )
        mock_provider.get_data_quality.assert_not_awaited()

    def test_file_dates_endpoint_accepts_comma_separated_dates(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """A single comma-separated file_dates param is split into a date list."""
        # Act
        response = client.get("/data-quality/usgs_earthquake/file-dates?file_dates=2026-09-19,2026-09-20")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_provider.get_data_quality_for_file_dates.assert_awaited_once_with(
            "usgs_earthquake", ["2026-09-19", "2026-09-20"]
        )

    def test_file_dates_endpoint_supports_single_date(self, client: TestClient, mock_provider: MagicMock) -> None:
        """A single file_dates value still routes through the many-dates method."""
        # Act
        response = client.get("/data-quality/usgs_earthquake/file-dates", params={"file_dates": ["2026-09-20"]})

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_provider.get_data_quality_for_file_dates.assert_awaited_once_with("usgs_earthquake", ["2026-09-20"])

    def test_file_dates_endpoint_returns_422_when_dates_missing(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """Missing file_dates fails validation and never calls the provider."""
        # Act
        response = client.get("/data-quality/usgs_earthquake/file-dates")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_provider.get_data_quality_for_file_dates.assert_not_awaited()

    def test_file_dates_endpoint_returns_422_when_dates_empty(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """An empty file_dates value is rejected by the endpoint's normalization guard."""
        # Act — empty CSV yields an empty list after normalization, rejected as 422
        response = client.get("/data-quality/usgs_earthquake/file-dates?file_dates=")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
