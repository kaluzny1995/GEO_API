"""Shared helper utilities."""

import logging
import os
from typing import Any


def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """Create a logger that writes to ``log_file``.

    Missing parent directories of ``log_file`` are created automatically.

    Args:
        name: Logger name.
        log_file: Path of the log file.
        level: Logging level.

    Returns:
        A configured :class:`logging.Logger`.
    """
    log_file_folder = os.path.dirname(log_file)
    if log_file_folder and not os.path.exists(log_file_folder):
        os.makedirs(log_file_folder)

    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def chunk_list_equal_size(objects: list[Any], batch_size: int) -> list[list[Any]]:
    """Split ``objects`` into consecutive chunks of at most ``batch_size`` items.

    Args:
        objects: Items to split.
        batch_size: Maximum number of items per chunk.

    Returns:
        A list of chunks (the last chunk may be shorter).
    """
    return [objects[i : i + batch_size] for i in range(0, len(objects), batch_size)]
