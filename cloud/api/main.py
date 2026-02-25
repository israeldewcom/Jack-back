# cloud/api/main.py
from fastapi import FastAPI
from .ingest import router as ingest_router

app = FastAPI(title="CITP Cloud API")

app.include_router(ingest_router, prefix="/v1/telemetry", tags=["ingest"])
# app.include_router(v2_router, prefix="/v2/telemetry", tags=["ingest v2"])

@app.get("/health")
async def health():
    return {"status": "ok"}
