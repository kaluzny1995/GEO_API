"""Tests for the data source files router (provider mocked via dependency override)."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from starlette.testclient import TestClient

from main import app
from model.data_source_file import DataSourceFile, DataSourceSource
from routes.data_source_files import get_data_source_files_provider


def file_row(
    source_name: str,
    file_name: str,
    snapshot_date: str | None,
    records: int = 1,
) -> DataSourceFile:
    """Build one file metadata row for the mocked provider."""
    return DataSourceFile(
        source_name=source_name,
        file_name=file_name,
        snapshot_date=snapshot_date,
        created_at="2026-10-04T02:14:50Z",
        records=records,
        size_kb=0.7,
        pipeline_start_date="2026-09-01",
    )


def source_row(source_name: str) -> DataSourceSource:
    """Build one source-registry row for the mocked provider."""
    return DataSourceSource(
        source_name=source_name,
        pipeline_start_date="2026-09-01",
        updated_at="2026-11-03T22:16:58Z",
    )


@pytest.fixture()
def mock_provider() -> MagicMock:
    """Provider mock returning two sources and two CSV rows."""
    provider = MagicMock()
    provider.get_files = AsyncMock(
        return_value=[
            file_row("EONET", "eonet_events_2026-09-01.csv", "2026-09-01", records=12),
            file_row("NIFC", "nifc_fires_2026-09-03.csv", "2026-09-03", records=7),
        ]
    )
    provider.get_sources = AsyncMock(return_value=[source_row("EONET"), source_row("NIFC")])
    return provider


@pytest.fixture()
def client(mock_provider: MagicMock) -> Generator[TestClient, None, None]:
    """Yield a TestClient with the provider dependency overridden by mock_provider."""
    app.dependency_overrides[get_data_source_files_provider] = lambda: mock_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestGetDataSourceFiles:
    """Tests for ``GET /data-source-files``."""

    def test_returns_sources_and_file_metadata(self, client: TestClient) -> None:
        """The endpoint combines the source registry with the file rows."""
        response = client.get("/data-source-files")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["sources"] == ["EONET", "NIFC"]
        assert body["start_date"] == "2026-09-01"
        assert body["latest_date"] == "2026-09-03"
        assert len(body["files"]) == 2
        assert [file["file_name"] for file in body["files"]] == [
            "eonet_events_2026-09-01.csv",
            "nifc_fires_2026-09-03.csv",
        ]
        assert "pipeline_start_date" not in body["files"][0]
        assert body["files"][0]["records"] == 12

    def test_falls_back_to_file_sources_when_the_source_table_is_empty(
        self, client: TestClient, mock_provider: MagicMock
    ) -> None:
        """A deployment that has only the file table still lists its sources."""
        mock_provider.get_sources = AsyncMock(return_value=[])

        response = client.get("/data-source-files")

        body = response.json()
        assert body["sources"] == ["EONET", "NIFC"]
        assert body["start_date"] == "2026-09-01"

    def test_returns_an_empty_response_without_rows(self, client: TestClient, mock_provider: MagicMock) -> None:
        """Empty tables produce empty lists, not a server error."""
        mock_provider.get_files = AsyncMock(return_value=[])
        mock_provider.get_sources = AsyncMock(return_value=[])

        response = client.get("/data-source-files")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "start_date": None,
            "latest_date": None,
            "sources": [],
            "files": [],
        }
