"""Custom FastAPI exception handlers and error middleware."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

import error
from model.message import ResponseMessage

logger = logging.getLogger(__name__)


async def supabase_server_down_error_handler(request: Request, exc: error.SupabaseServerDownError) -> JSONResponse:
    """Map :class:`SupabaseServerDownError` to a 503 Service Unavailable response.

    Args:
        request: The originating request.
        exc: The caught exception.

    Returns:
        A 503 JSON response with a standard :class:`ResponseMessage` body.
    """
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ResponseMessage(
            title="Service Unavailable.",
            description=str(exc),
            code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ).model_dump(),
    )


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Map any unhandled exception to a JSON 500 that still carries CORS headers.

    Starlette's ``ServerErrorMiddleware`` sits outside ``CORSMiddleware`` and turns
    an unhandled exception into a plain-text 500 with no ``Access-Control-Allow-
    Origin`` header. A browser then reports the failure as a CORS error instead
    of the real server error. Handling ``Exception`` here keeps the response
    inside the CORS middleware and returns the same :class:`ResponseMessage`
    envelope as the other error handlers, without exposing internals.

    Args:
        request: The originating request.
        exc: The caught exception.

    Returns:
        A generic 500 JSON response.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ResponseMessage(
            title="Internal Server Error.",
            description="An unexpected error occurred.",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ).model_dump(),
    )


class InternalServerErrorMiddleware(BaseHTTPMiddleware):
    """Catch unhandled route errors inside CORS and return a JSON 500.

    ``app.add_exception_handler(Exception, ...)`` is handled by Starlette's
    outermost ``ServerErrorMiddleware``, outside ``CORSMiddleware``; its plain
    text 500 has no CORS header. This middleware is registered *before* CORS so
    CORS wraps it, and therefore decorates the JSON 500 with the normal
    ``Access-Control-Allow-Origin`` header.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Run the request and translate an unexpected exception into a 500 response."""
        try:
            return await call_next(request)
        except Exception as exc:  # The UI boundary: never leak an unhandled traceback to an HTTP client.
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            return await internal_server_error_handler(request, exc)
