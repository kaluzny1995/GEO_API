"""Uvicorn run configuration (``config.json`` → ``app_run``)."""

import json
import os

from pydantic import BaseModel, ConfigDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")


class AppRunConfig(BaseModel):
    """Uvicorn server settings used by ``run.py``.

    Attributes:
        host: Host to bind.
        port: Port to bind.
        reload: Enable auto-reload on code changes.
        log_level: Uvicorn log level.
    """

    model_config = ConfigDict(frozen=True)

    host: str
    port: int
    reload: bool
    log_level: str

    @staticmethod
    def from_json(path: str | None = None) -> "AppRunConfig":
        """Load run settings from a JSON file.

        Args:
            path: Path to the config file. Defaults to ``config.json``
                in the project root.

        Returns:
            A frozen :class:`AppRunConfig` instance.
        """
        if path is None:
            path = CONFIG_PATH
        with open(path) as f:
            return AppRunConfig(**json.load(f)["app_run"])
