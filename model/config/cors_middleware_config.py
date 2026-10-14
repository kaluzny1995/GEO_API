"""CORS middleware configuration (``config.json`` → ``cors_middleware``)."""

import json
import os

from pydantic import BaseModel, ConfigDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")


class CORSMiddlewareConfig(BaseModel):
    """CORS middleware settings for the FastAPI app.

    Attributes:
        allow_origins: Allowed origins.
        allow_credentials: Whether credentials are allowed.
        allow_methods: Allowed HTTP methods.
        allow_headers: Allowed request headers.
    """

    model_config = ConfigDict(frozen=True)

    allow_origins: list[str]
    allow_credentials: bool
    allow_methods: list[str]
    allow_headers: list[str]

    @staticmethod
    def from_json(path: str | None = None) -> "CORSMiddlewareConfig":
        """Load CORS settings from a JSON file.

        Args:
            path: Path to the config file. Defaults to ``config.json``
                in the project root.

        Returns:
            A frozen :class:`CORSMiddlewareConfig` instance.
        """
        if path is None:
            path = CONFIG_PATH
        with open(path) as f:
            return CORSMiddlewareConfig(**json.load(f)["cors_middleware"])
