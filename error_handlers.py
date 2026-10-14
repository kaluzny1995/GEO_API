"""Custom FastAPI exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

import error
from model.message import ResponseMessage


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
