"""API routers."""

from routes.data_quality import router as data_quality_router
from routes.data_quantity import router as data_quantity_router
from routes.data_source_files import router as data_source_files_router
from routes.event_counts import router as event_counts_router
from routes.logging_route import LoggingRoute
from routes.main import router as main_router

__all__ = [
    "LoggingRoute",
    "data_quality_router",
    "data_quantity_router",
    "data_source_files_router",
    "event_counts_router",
    "main_router",
]
