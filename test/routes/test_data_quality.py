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

    @pytest.mark.parametrize(
        ("params", "expected_dates"),
        [
            pytest.param({"file_dates": ["2026-09-19", "2026-09-20"]}, ["2026-09-19", "2026-09-20"], id="repeated"),
            pytest.param({"file_dates": "2026-09-19,2026-09-20"}, ["2026-09-19", "2026-09-20"], id="comma-separated"),
            pytest.param({"file_dates": ["2026-09-20"]}, ["2026-09-20"], id="single"),
        ],
    )
    def test_file_dates_endpoint_forwards_dates(
        self,
        client: TestClient,
        mock_provider: MagicMock,
        params: dict[str, str | list[str]],
        expected_dates: list[str],
    ) -> None:
        """Repeated and comma-separated file_dates both reach the provider as a date list."""
        # Act
        response = client.get("/data-quality/usgs_earthquake/file-dates", params=params)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body) == 2
        assert body[0]["metric"] == "bad_row_pct"
        mock_provider.get_data_quality_for_file_dates.assert_awaited_once_with("usgs_earthquake", expected_dates)
        mock_provider.get_data_quality.assert_not_awaited()

    @pytest.mark.parametrize(
        "request_url",
        [
            pytest.param("/data-quality/usgs_earthquake/file-dates", id="missing"),
            pytest.param("/data-quality/usgs_earthquake/file-dates?file_dates=", id="empty"),
        ],
    )
    def test_file_dates_endpoint_returns_422_when_dates_missing_or_empty(
        self, client: TestClient, mock_provider: MagicMock, request_url: str
    ) -> None:
        """Missing or empty file_dates fail validation and never call the provider."""
        # Act
        response = client.get(request_url)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_provider.get_data_quality_for_file_dates.assert_not_awaited()

    def test_file_dates_endpoint_returns_422_above_the_raw_limit(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """More than 100 raw file_dates parameters are rejected by Query(max_length=100)."""
        # Act
        response = client.get(
            "/data-quality/usgs_earthquake/file-dates",
            params={"file_dates": [f"2026-09-{(i % 28) + 1:02d}" for i in range(101)]},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_provider.get_data_quality_for_file_dates.assert_not_awaited()

    def test_file_dates_endpoint_returns_422_above_the_normalized_limit(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """Comma expansion cannot push the request past 100 dates: the post-normalization
        guard rejects it even though the raw parameter count stays within the limit."""
        # Act
        many_dates = ",".join(f"2026-09-{(i % 28) + 1:02d}" for i in range(150))
        response = client.get(
            "/data-quality/usgs_earthquake/file-dates",
            params={"file_dates": [many_dates]},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_provider.get_data_quality_for_file_dates.assert_not_awaited()
