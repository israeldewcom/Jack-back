# cloud/api/main.py
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute

# Import your routers
from .ingest import router as ingest_router
from .v2.ingest import router as v2_router
from ..observability.health import router as health_router  # optional health endpoint

# Import any global dependencies that need lifespan management
from ..feature_store.feature_store import FeatureStore
from ..model_registry.registry import ModelRegistry
from ..engine.online_learner import OnlineRiskLearner
from ..threat_intel.aggregator import ThreatIntelAggregator
from ..audit.logger import AuditLogger
from ..security.secrets import get_secret
import redis
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize shared resources
    logger.info("Starting up CITP API...")
    
    # Example: create Redis client and store in app.state
    redis_host = get_secret("REDIS_HOST", "redis")
    redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
    app.state.redis = redis_client
    
    # Initialize database engine (if needed for direct use)
    db_url = get_secret("DATABASE_URL")
    if db_url:
        app.state.db_engine = create_engine(db_url)
    
    # Initialize feature store, model registry, etc.
    app.state.feature_store = FeatureStore(db_url, redis_host=redis_host)
    app.state.model_registry = ModelRegistry()
    app.state.online_learner = OnlineRiskLearner(redis_client)
    app.state.threat_intel = ThreatIntelAggregator(redis_client)
    
    # Audit logger needs a db session factory; we'll set it later per request
    # For now, we can pass a session maker
    from ..db.database import SessionLocal
    app.state.audit_logger = AuditLogger(
        secret_key=get_secret("AUDIT_SECRET_KEY", "default-insecure-key"),
        db_session_factory=SessionLocal
    )
    
    logger.info("CITP API started successfully")
    yield
    # Shutdown: clean up resources
    logger.info("Shutting down CITP API...")
    redis_client.close()
    # close db engine if needed
    logger.info("Shutdown complete.")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Continuous Identity Trust Platform",
    description="Enterprise‑grade identity trust and risk assessment API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",          # Swagger UI
    redoc_url="/api/redoc",         # ReDoc
    openapi_url="/api/openapi.json" # OpenAPI schema
)

# Include routers
app.include_router(ingest_router, prefix="/v1/telemetry", tags=["Ingestion v1"])
app.include_router(v2_router, prefix="/v2/telemetry", tags=["Ingestion v2"])
app.include_router(health_router, prefix="/health", tags=["Health"])  # optional

# Root endpoint for basic info
@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "CITP Cloud API",
        "version": "2.0.0",
        "documentation": "/api/docs"
    }

# Optional: debug endpoint to list all registered routes (disable in production)
if os.getenv("ENVIRONMENT", "production").lower() == "development":
    @app.get("/debug/routes", tags=["Debug"])
    async def debug_routes():
        routes = []
        for route in app.routes:
            if isinstance(route, APIRoute):
                routes.append({
                    "path": route.path,
                    "name": route.name,
                    "methods": list(route.methods)
                })
        return {"routes": routes}

# For local development: run with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "cloud.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development"
    )
