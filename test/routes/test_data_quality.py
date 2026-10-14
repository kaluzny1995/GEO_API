"""Tests for the data quality router (provider mocked via dependency override)."""

import datetime as dt
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
def mock_provider():
    provider = MagicMock()
    provider.get_data_quality = AsyncMock(return_value=list(ROWS))
    provider.get_data_quality_for_file_dates = AsyncMock(return_value=list(ROWS))
    return provider


@pytest.fixture()
def client(mock_provider):
    app.dependency_overrides[get_data_quality_provider] = lambda: mock_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestGetDataQuality:
    def test_overall_endpoint_returns_200_with_metrics(self, client, mock_provider):
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

    def test_file_date_endpoint_returns_200_with_metrics(self, client, mock_provider):
        # Act
        response = client.get("/data-quality/usgs_earthquake/2026-09-20")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 2
        assert body[0]["file_date"] == "overall"  # mocked rows keep their own file_date
        mock_provider.get_data_quality.assert_awaited_once_with("usgs_earthquake", "2026-09-20")

    def test_overall_endpoint_returns_empty_list_when_no_metrics(self, client, mock_provider):
        # Arrange
        mock_provider.get_data_quality = AsyncMock(return_value=[])

        # Act
        response = client.get("/data-quality/unknown_table")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


class TestGetDataQualityForFileDates:
    def test_file_dates_endpoint_returns_200_with_metrics(self, client, mock_provider):
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

    def test_file_dates_endpoint_accepts_comma_separated_dates(self, client, mock_provider):
        # Act
        response = client.get("/data-quality/usgs_earthquake/file-dates?file_dates=2026-09-19,2026-09-20")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_provider.get_data_quality_for_file_dates.assert_awaited_once_with(
            "usgs_earthquake", ["2026-09-19", "2026-09-20"]
        )

    def test_file_dates_endpoint_supports_single_date(self, client, mock_provider):
        # Act
        response = client.get("/data-quality/usgs_earthquake/file-dates", params={"file_dates": ["2026-09-20"]})

        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_provider.get_data_quality_for_file_dates.assert_awaited_once_with("usgs_earthquake", ["2026-09-20"])

    def test_file_dates_endpoint_returns_422_when_dates_missing(self, client, mock_provider):
        # Act
        response = client.get("/data-quality/usgs_earthquake/file-dates")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_provider.get_data_quality_for_file_dates.assert_not_awaited()

    def test_file_dates_endpoint_returns_422_when_dates_empty(self, client, mock_provider):
        # Act — empty CSV yields an empty list, rejected by min_length=1
        response = client.get("/data-quality/usgs_earthquake/file-dates?file_dates=")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
