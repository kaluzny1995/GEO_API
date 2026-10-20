"""Shared helper utilities."""

import logging
import os
from collections.abc import Iterator
from typing import Any


def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """Create a logger that writes to ``log_file``.

    Missing parent directories of ``log_file`` are created automatically.
    Idempotent per ``(name, log_file)`` pair: re-requesting a logger that
    already has a handler for this file adds no second handler, so rebuilding
    a provider (repeatedly, e.g. in tests) neither duplicates every log line
    nor leaks file descriptors.

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

    logger = logging.getLogger(name)
    logger.setLevel(level)
    resolved_log_file = os.path.abspath(log_file)
    if not any(
        isinstance(handler, logging.FileHandler) and handler.baseFilename == resolved_log_file
        for handler in logger.handlers
    ):
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)

    return logger


def chunk_list_equal_size(objects: list[Any], batch_size: int) -> Iterator[list[Any]]:
    """Yield consecutive chunks of at most ``batch_size`` items.

    Lazy on purpose: only the current chunk is built, so batching a large
    list costs ``O(batch_size)`` extra memory instead of materializing every
    chunk up front (``O(len(objects))``).

    Args:
        objects: Items to split.
        batch_size: Maximum number of items per chunk.

    Yields:
        Chunks in order (the last chunk may be shorter).
    """
    for start in range(0, len(objects), batch_size):
        yield objects[start : start + batch_size]
