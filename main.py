"""FastAPI application entry point (uvicorn main:app)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import error
from error_handlers import supabase_server_down_error_handler
from model.config import AppMetadataConfig, CORSMiddlewareConfig
from provider import dispose_provider
from routes import data_quality_router, event_counts_router, main_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Dispose the shared database engine's connection pool on shutdown.

    The provider itself is created lazily on first use (e.g. by ``/health``),
    so startup performs no database I/O and unit tests need no credentials.
    """
    yield
    await dispose_provider()


app_metadata_config = AppMetadataConfig.from_json()
app = FastAPI(**app_metadata_config.model_dump(), lifespan=lifespan)

cors_middleware_config = CORSMiddlewareConfig.from_json()
app.add_middleware(CORSMiddleware, **cors_middleware_config.model_dump())

app.include_router(main_router)
app.include_router(data_quality_router)
app.include_router(event_counts_router)
app.add_exception_handler(error.SupabaseServerDownError, supabase_server_down_error_handler)  # type: ignore[arg-type]
