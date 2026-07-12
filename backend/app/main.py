"""
Open Analytics AI - Main FastAPI Application
Natural Language to SQL Analytics Platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.core.database import init_db
from app.api import (
    upload_router,
    query_router,
    schema_router,
    export_router,
    auth_router,
    llm_router,
    dashboard_router,
    health_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Open Analytics AI...")
    await init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.EXPORT_DIR, exist_ok=True)
    logger.info("Application ready.")
    yield
    logger.info("Shutting down Open Analytics AI...")


app = FastAPI(
    title="Open Analytics AI",
    description="Natural Language to SQL Analytics Platform - 100% Open Source",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(health_router, prefix="/api/health", tags=["Health"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(upload_router, prefix="/api/upload", tags=["File Upload"])
app.include_router(schema_router, prefix="/api/schema", tags=["Schema"])
app.include_router(query_router, prefix="/api/query", tags=["Query"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(llm_router, prefix="/api/llm", tags=["LLM"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

if os.path.exists(settings.EXPORT_DIR):
    app.mount("/exports", StaticFiles(directory=settings.EXPORT_DIR), name="exports")
