"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, doctors, generate, notes, reports
from app.services.ai_search import ai_search_service
from app.services.audit import audit_service
from app.services.blob_storage import blob_service
from app.services.cosmos_db import cosmos_service
from app.services.openai_service import openai_service
from app.utils.phi_sanitizer import PHISanitizingFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# HIPAA: attach PHI-scrubbing filter to root logger
logging.getLogger().addFilter(PHISanitizingFilter())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize Azure service clients on startup."""
    logger.info("Initializing Azure service clients...")
    audit_service.configure(settings.APPINSIGHTS_CONNECTION_STRING)
    try:
        await cosmos_service.initialize()
        await blob_service.initialize()
        await openai_service.initialize()
        await ai_search_service.initialize()
        logger.info("All Azure services initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Azure services: %s", e)
        logger.warning("Application starting with degraded service connectivity")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="Impressions Generator",
    description="Healthcare radiology/oncology clinical note generation API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(doctors.router)
app.include_router(notes.router)
app.include_router(generate.router)
app.include_router(reports.router)
app.include_router(admin.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
