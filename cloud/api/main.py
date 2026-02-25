# cloud/api/main.py
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routers from existing modules
try:
    from .ingest import router as ingest_router
    logger.info("Imported ingest_router (v1)")
except ImportError as e:
    logger.error(f"Failed to import ingest_router: {e}")
    ingest_router = None

# Optional v2 router – if the module exists, import it; otherwise set to None
try:
    from .v2.ingest import router as v2_router
    logger.info("Imported v2_router")
except ImportError:
    v2_router = None
    logger.info("v2_router not available (optional)")

# Create FastAPI app
app = FastAPI(
    title="CITP Cloud API",
    description="Continuous Identity Trust Platform - Cloud API",
    version="1.0.0",
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",         # ReDoc
)

# Configure CORS (adjust origins as needed for your environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 router if available
if ingest_router:
    app.include_router(
        ingest_router,
        prefix="/v1/telemetry",
        tags=["Telemetry (v1)"],
    )
    logger.info("Included ingest_router at /v1/telemetry")

# Include v2 router if available
if v2_router:
    app.include_router(
        v2_router,
        prefix="/v2/telemetry",
        tags=["Telemetry (v2)"],
    )
    logger.info("Included v2_router at /v2/telemetry")

# ------------------------------------------------------------------
# Basic endpoints for health checks and root information
# ------------------------------------------------------------------
@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint – confirms API is running."""
    return {
        "service": "CITP Cloud API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint – returns OK if the app is running."""
    return {"status": "healthy"}

# ------------------------------------------------------------------
# Optional: Debug endpoint to list all registered routes
# Enable only in development by setting environment variable DEBUG=true
# ------------------------------------------------------------------
if os.getenv("DEBUG", "").lower() == "true":
    from fastapi.routing import APIRoute

    @app.get("/debug/routes", tags=["Debug"])
    async def debug_routes():
        """Return a list of all registered routes (debug only)."""
        routes = []
        for route in app.routes:
            if isinstance(route, APIRoute):
                routes.append({
                    "path": route.path,
                    "name": route.name,
                    "methods": list(route.methods),
                })
        return {"routes": routes}
    logger.info("Debug endpoint /debug/routes enabled")

# ------------------------------------------------------------------
# Startup event
# ------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("CITP Cloud API starting up...")
    logger.info(f"Registered routes: {[route.path for route in app.routes]}")

# ------------------------------------------------------------------
# For running directly with `python cloud/api/main.py` (optional)
# ------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "cloud.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "").lower() == "true",
    )
