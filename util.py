"""Shared helper utilities."""

import logging
import os
import sys
from collections.abc import Iterator
from contextvars import ContextVar
from typing import Any, Final

from starlette import status

_LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"

# starlette 1.0 renamed HTTP_422_UNPROCESSABLE_ENTITY to HTTP_422_UNPROCESSABLE_CONTENT
# (RFC 9110 terminology) and turned the old name into a module __getattr__ that emits a
# StarletteDeprecationWarning on every access. FastAPI's own request-validation path uses
# the new name, so referring to the old one is the only thing that warns here.
#
# Resolve to the new constant when the installed starlette has it, else fall back to the
# literal 422. Both are the same number, and the deprecated name is deliberately never
# touched (note that ``getattr(status, "…_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)``
# would still evaluate the default eagerly and therefore still warn), so this is silent on
# starlette <1.0 — where the new name does not exist — and on >=1.0 alike.
HTTP_422_UNPROCESSABLE: Final = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

# Logger of the endpoint currently handling a request. Set by the route
# wrapper (routes/logging_route.py) and read by providers, so database
# records (connection, SQL, row counts) land in the endpoint's log file.
endpoint_logger: ContextVar[logging.Logger | None] = ContextVar("endpoint_logger", default=None)


def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """Create a logger that writes to ``log_file`` and mirrors records to stdout.

    Follows the GEO_ETL / GEO_Download convention: every record goes to the
    log file *and* to stdout, so console runs (and subprocess orchestrators)
    show the same output without opening the file.

    Missing parent directories of ``log_file`` are created automatically.
    Idempotent per handler: re-requesting a logger that already has a handler
    for this file (or a stdout handler) adds no second one, so rebuilding a
    logger repeatedly (e.g. in tests) neither duplicates every log line nor
    leaks file descriptors. Propagation is disabled: the logger owns its
    handlers, so records never double-emit through an ancestor logger (e.g.
    the root logger) and unrelated records never pollute the log file.

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
    logger.propagate = False

    resolved_log_file = os.path.abspath(log_file)
    existing_paths = {handler.baseFilename for handler in logger.handlers if isinstance(handler, logging.FileHandler)}
    if resolved_log_file not in existing_paths:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(file_handler)

    # FileHandler is a StreamHandler subclass — only consider plain stream handlers.
    has_stdout_handler = any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        and handler.stream is sys.stdout
        for handler in logger.handlers
    )
    if not has_stdout_handler:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(stream_handler)

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
