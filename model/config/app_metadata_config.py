"""Application metadata configuration for the FastAPI app (``metadata.json``)."""

import json
import os

from pydantic import BaseModel, ConfigDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
METADATA_PATH = os.path.join(PROJECT_DIR, "metadata.json")


class AppMetadataConfig(BaseModel):
    """FastAPI application metadata.

    Attributes:
        title: API title.
        description: API description (a list of lines in ``metadata.json``).
        summary: Short API summary.
        version: API version.
    """

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    summary: str
    version: str

    @staticmethod
    def from_json(path: str | None = None) -> "AppMetadataConfig":
        """Load metadata from a JSON file.

        Args:
            path: Path to the metadata file. Defaults to ``metadata.json``
                in the project root.

        Returns:
            A frozen :class:`AppMetadataConfig` instance.
        """
        if path is None:
            path = METADATA_PATH
        with open(path) as f:
            config_dict = json.load(f)
        config_dict["description"] = "\n".join(config_dict["description"])
        return AppMetadataConfig(**config_dict)
