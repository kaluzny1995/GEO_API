"""Database connection-pool configuration (``config.json`` → ``database``)."""

import json
import os

from pydantic import BaseModel, ConfigDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.json")


class DatabaseConfig(BaseModel):
    """Pool settings for the shared SQLAlchemy async engine.

    Attributes:
        pool_size: Number of connections kept in the pool.
        max_overflow: Extra connections allowed above ``pool_size``.
        pool_recycle_seconds: Recycle pooled connections after this many seconds.
    """

    model_config = ConfigDict(frozen=True)

    pool_size: int = 5
    max_overflow: int = 5
    pool_recycle_seconds: int = 300

    @staticmethod
    def from_json(path: str | None = None) -> "DatabaseConfig":
        """Load the pool settings from a JSON file.

        Args:
            path: Path to the config file. Defaults to ``config.json``
                in the project root.

        Returns:
            A frozen :class:`DatabaseConfig` instance.
        """
        if path is None:
            path = CONFIG_PATH
        with open(path) as f:
            return DatabaseConfig(**json.load(f)["database"])
