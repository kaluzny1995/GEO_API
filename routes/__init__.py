"""API routers."""

from routes.data_quality import router as data_quality_router
from routes.event_counts import router as event_counts_router
from routes.main import router as main_router

__all__ = ["data_quality_router", "event_counts_router", "main_router"]
