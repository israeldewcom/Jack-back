from fastapi import FastAPI, Depends
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

app = FastAPI(title="CITP Cloud API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware
app.add_middleware(BillingMiddleware)

# Routers
app.include_router(v1_ingest.router, prefix="/v1")
app.include_router(v2_ingest.router)
app.include_router(auth_router.router)
app.include_router(health_router)
app.include_router(metrics_router)

@app.on_event("startup")
async def startup():
    setup_logging()
    # Start Kafka consumer
    consumer = TelemetryConsumer(max_concurrent=20)
    asyncio.create_task(consumer.start())

@app.get("/")
async def root():
    return {
        "service": "CITP Cloud API",
        "version": "2.0.0",
        "status": "operational",
        "documentation": "/docs"
    }
