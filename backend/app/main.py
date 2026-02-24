"""FastAPI application entry point."""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, doctors, generate, notes, reports
from app.services.ai_search import ai_search_service
from app.services.audit import audit_service
from app.services.blob_storage import blob_service
from app.services.cosmos_db import cosmos_service
from app.services.monitoring import monitoring_service
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
    # Initialize telemetry first so spans cover service init
    monitoring_service.initialize()

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


# --- Request telemetry middleware ---
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next) -> Response:
    """Track request duration and status for Azure Monitor."""
    start = time.time()
    response: Response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "Request %s %s → %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
