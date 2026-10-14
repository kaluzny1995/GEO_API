"""Tests for the app metadata, run and CORS configurations."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from model.config.app_metadata_config import AppMetadataConfig
from model.config.app_run_config import AppRunConfig
from model.config.cors_middleware_config import CORSMiddlewareConfig

VALID_METADATA = {
    "title": "GEO_API",
    "description": ["Line one.", "Line two."],
    "summary": "Geographic data sharing API.",
    "version": "0.1.0",
}

VALID_CONFIG = {
    "app_run": {
        "host": "127.0.0.1",
        "port": 8000,
        "reload": False,
        "log_level": "info",
    },
    "cors_middleware": {
        "allow_origins": ["*"],
        "allow_credentials": False,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    },
}


class TestAppMetadataConfig:
    """Tests for :class:`AppMetadataConfig`."""

    def test_from_json_joins_description_lines(self, tmp_path: Path) -> None:
        """``from_json`` joins the JSON description lines with newlines."""
        path = tmp_path / "metadata.json"
        path.write_text(json.dumps(VALID_METADATA))
        cfg = AppMetadataConfig.from_json(path=str(path))
        assert cfg.title == "GEO_API"
        assert cfg.description == "Line one.\nLine two."
        assert cfg.summary == "Geographic data sharing API."
        assert cfg.version == "0.1.0"

    def test_frozen(self, tmp_path: Path) -> None:
        """The config model is immutable (frozen)."""
        path = tmp_path / "metadata.json"
        path.write_text(json.dumps(VALID_METADATA))
        cfg = AppMetadataConfig.from_json(path=str(path))
        with pytest.raises(ValidationError):
            cfg.title = "other"

    def test_project_metadata_json_is_valid(self) -> None:
        """The project's ``project_metadata.json`` parses into a valid config."""
        cfg = AppMetadataConfig.from_json()
        assert cfg.title == "GEO_API"
        assert cfg.version


class TestAppRunConfig:
    """Tests for :class:`AppRunConfig`."""

    def test_from_json(self, tmp_path: Path) -> None:
        """``from_json`` reads the nested ``app_run`` section."""
        path = tmp_path / "config.json"
        path.write_text(json.dumps(VALID_CONFIG))
        cfg = AppRunConfig.from_json(path=str(path))
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 8000
        assert cfg.reload is False
        assert cfg.log_level == "info"

    def test_frozen(self, tmp_path: Path) -> None:
        """The config model is immutable (frozen)."""
        path = tmp_path / "config.json"
        path.write_text(json.dumps(VALID_CONFIG))
        cfg = AppRunConfig.from_json(path=str(path))
        with pytest.raises(ValidationError):
            cfg.port = 9000

    def test_project_config_json_is_valid(self) -> None:
        """The project's ``project_config.json`` parses into a valid config."""
        cfg = AppRunConfig.from_json()
        assert cfg.port == 8000


class TestCORSMiddlewareConfig:
    """Tests for :class:`CORSMiddlewareConfig`."""

    def test_from_json(self, tmp_path: Path) -> None:
        """``from_json`` reads the nested ``cors_middleware`` section."""
        path = tmp_path / "config.json"
        path.write_text(json.dumps(VALID_CONFIG))
        cfg = CORSMiddlewareConfig.from_json(path=str(path))
        assert cfg.allow_origins == ["*"]
        assert cfg.allow_credentials is False
        assert cfg.allow_methods == ["*"]
        assert cfg.allow_headers == ["*"]

    def test_frozen(self, tmp_path: Path) -> None:
        """The config model is immutable (frozen)."""
        path = tmp_path / "config.json"
        path.write_text(json.dumps(VALID_CONFIG))
        cfg = CORSMiddlewareConfig.from_json(path=str(path))
        with pytest.raises(ValidationError):
            cfg.allow_origins = ["https://example.com"]

    def test_project_config_json_is_valid(self) -> None:
        """The project's ``project_config.json`` parses into a valid config."""
        cfg = CORSMiddlewareConfig.from_json()
        assert cfg.allow_origins == ["*"]
