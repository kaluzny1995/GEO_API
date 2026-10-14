"""Main router: root, hello and health endpoints."""

from fastapi import APIRouter, status

from model.message import ResponseMessage
from provider import get_provider

router = APIRouter()


@router.get("/", response_model=ResponseMessage, tags=["main"])
async def root() -> ResponseMessage:
    """Root endpoint — basic liveness message.

    Returns:
        A 200 greeting message.
    """
    return ResponseMessage(
        title="Hello GEO_API",
        description="Successful response.",
        code=status.HTTP_200_OK,
    )


@router.get("/hello", response_model=ResponseMessage, tags=["main"])
async def hello() -> ResponseMessage:
    """Hello endpoint — basic liveness message.

    Returns:
        A 200 greeting message.
    """
    return ResponseMessage(
        title="Hello GEO_API",
        description="Successful response.",
        code=status.HTTP_200_OK,
    )


@router.get("/health", response_model=ResponseMessage, tags=["main"])
async def health() -> ResponseMessage:
    """Health endpoint — verifies the Supabase Postgres connection.

    Returns:
        A 200 healthy message when the database is reachable.

    Raises:
        SupabaseServerDownError: When the database is unreachable —
            mapped to 503 by the global exception handler.
    """
    await get_provider().connect()
    return ResponseMessage(
        title="Healthy",
        description="API and database connection are OK.",
        code=status.HTTP_200_OK,
    )
