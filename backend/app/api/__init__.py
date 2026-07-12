from .health import router as health_router
from .auth import router as auth_router
from .upload import router as upload_router
from .schema import router as schema_router
from .query import router as query_router
from .export import router as export_router
from .llm import router as llm_router
from .dashboard import router as dashboard_router

__all__ = [
    "health_router", "auth_router", "upload_router", "schema_router",
    "query_router", "export_router", "llm_router", "dashboard_router",
]
