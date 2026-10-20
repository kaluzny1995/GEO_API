"""Shared test fixtures."""

import pytest

import routes.logging_route


@pytest.fixture(autouse=True)
def endpoint_log_directory(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect the per-endpoint log files to a per-test tmp dir (no litter in ``logs/``)."""
    monkeypatch.setattr(routes.logging_route, "LOG_DIRECTORY", str(tmp_path))
