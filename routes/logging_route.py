"""Request-logging route class — one log file per endpoint (GEO_* logging conventions)."""

import datetime as dt
import logging
import os
import time
from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

import util

# Root directory of the per-endpoint log files (overridable in tests).
LOG_DIRECTORY = "logs"

# Namespace of the per-endpoint loggers — keeps names like "root" from
# colliding with the actual root logger or third-party loggers.
_LOGGER_NAMESPACE = "geo_api"


def endpoint_log_file(endpoint_name: str, tag: str | Enum) -> str:
    """Return the log file path of an endpoint: ``<LOG_DIRECTORY>/<tag>/<endpoint>_<timestamp>.log``.

    Args:
        endpoint_name: Endpoint (route handler) name.
        tag: First router tag of the endpoint — becomes the subdirectory.

    Returns:
        The path of the endpoint's log file (timestamped per application run).
    """
    return os.path.join(
        LOG_DIRECTORY, str(tag).replace("-", "_"), f"{endpoint_name}_{dt.datetime.now().isoformat()}.log"
    )


def _elapsed_ms(started_at: float) -> float:
    """Return milliseconds elapsed since ``started_at`` (``time.perf_counter`` base)."""
    return round((time.perf_counter() - started_at) * 1000, 1)


class LoggingRoute(APIRoute):
    """``APIRoute`` that logs every request to the endpoint's own log file.

    Following the GEO_ETL / GEO_Download convention, each endpoint gets a
    logger (named ``geo_api.<handler>``) writing to
    ``logs/<tag>/<handler>_<timestamp>.log`` plus stdout, format
    ``%(asctime)s %(levelname)s %(message)s``. The file is created lazily on
    the endpoint's first request — one file per endpoint per application run,
    appended to for every subsequent request.

    Every request logs a start line and a finish line with status and elapsed
    time. Client errors (4xx) are logged as warnings; anything else is logged
    with a full traceback at the endpoint boundary and re-raised, so the
    global exception handler can map it (e.g. ``SupabaseServerDownError`` → 503).
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap the standard route handler with per-request logging."""
        original_route_handler = super().get_route_handler()
        endpoint_name = self.name or "endpoint"
        endpoint_logger: logging.Logger | None = None

        async def log_request(request: Request) -> Response:
            nonlocal endpoint_logger
            if endpoint_logger is None:
                endpoint_logger = util.setup_logger(
                    name=f"{_LOGGER_NAMESPACE}.{endpoint_name}",
                    log_file=endpoint_log_file(endpoint_name, self.tags[0] if self.tags else "misc"),
                )
            target = request.url.path
            if request.query_params:
                target = f"{target}?{request.query_params}"
            started_at = time.perf_counter()
            endpoint_logger.info(f"{request.method} {target} started")
            token = util.endpoint_logger.set(endpoint_logger)
            try:
                response = await original_route_handler(request)
            except (StarletteHTTPException, RequestValidationError) as e:
                endpoint_logger.warning(
                    f"{request.method} {target} finished with {getattr(e, 'status_code', 422)} "
                    f"in {_elapsed_ms(started_at)} ms"
                )
                raise
            except Exception:
                endpoint_logger.exception(f"{request.method} {target} failed after {_elapsed_ms(started_at)} ms")
                raise
            finally:
                util.endpoint_logger.reset(token)
            endpoint_logger.info(
                f"{request.method} {target} finished with {response.status_code} in {_elapsed_ms(started_at)} ms"
            )
            return response

        return log_request
