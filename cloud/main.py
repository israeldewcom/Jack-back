"""
Main FastAPI application for CITP Cloud API.
Integrates all routers and background tasks.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from .api import ingest as v1_ingest
from .api.v2 import ingest as v2_ingest
from .auth import router as auth_router
from .observability.health import router as health_router
from .observability.metrics import metrics_router
from .observability.logging import setup_logging
from .streaming.consumer import TelemetryConsumer
from .billing.middleware import BillingMiddleware
import asyncio

app = FastAPI(
    title="CITP Cloud API",
    description="Continuous Identity Trust Platform",
    version="2.0.0",
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Billing middleware (adds usage tracking)
if os.getenv("ENABLE_BILLING", "false").lower() == "true":
    app.add_middleware(BillingMiddleware)

# Include routers – v1 untouched, v2 added
app.include_router(v1_ingest.router, prefix="/v1", tags=["Telemetry v1"])
if os.getenv("ENABLE_V2_API", "true").lower() == "true":
    app.include_router(v2_ingest.router, prefix="/v2", tags=["Telemetry v2"])
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(metrics_router, prefix="/metrics", tags=["Metrics"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    setup_logging()
    # Start Kafka consumer if enabled
    if os.getenv("ENABLE_KAFKA_CONSUMER", "true").lower() == "true":
        consumer = TelemetryConsumer(max_concurrent=int(os.getenv("KAFKA_MAX_CONCURRENT", "10")))
        asyncio.create_task(consumer.start())
    # Additional startup tasks (e.g., warm up caches) can be added here

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    # Gracefully stop background tasks
    pass

@app.get("/")
async def root():
    return {
        "service": "CITP Cloud API",
        "version": "2.0.0",
        "status": "operational",
        "documentation": "/docs",
        "v1_endpoints": "/v1/telemetry",
        "v2_endpoints": "/v2/telemetry" if os.getenv("ENABLE_V2_API") else "disabled",
    }
