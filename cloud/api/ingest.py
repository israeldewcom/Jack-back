# cloud/api/ingest.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/telemetry")
async def ingest_telemetry():
    return {"status": "ok"}
