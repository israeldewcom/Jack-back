from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from ...auth.dependencies import get_current_user
from ...streaming.processor import process_telemetry
from ...audit.logger import AuditLogger
from ...db.database import SessionLocal
from ...observability.metrics import telemetry_counter

router = APIRouter(prefix="/v2/telemetry", tags=["Telemetry v2"])

class TelemetryEvent(BaseModel):
    session_id: str
    user_id: str
    ip: str
    keystroke_speed: float = Field(..., ge=0, le=100)
    mouse_speed: float = Field(..., ge=0, le=100)
    timestamp: datetime
    device: Optional[str] = None
    role: Optional[str] = "standard"

@router.post("")
async def ingest_telemetry(
    event: TelemetryEvent,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    # Validate user matches (optional)
    if current_user["sub"] != event.user_id:
        raise HTTPException(403, "User mismatch")

    # Process asynchronously
    background_tasks.add_task(process_telemetry, event.dict())

    # Increment metric
    telemetry_counter.labels(endpoint="v2").inc()

    # Audit log
    audit = AuditLogger(os.getenv("AUDIT_SECRET"), SessionLocal)
    audit.log("telemetry_ingested", event.user_id, {"session_id": event.session_id}, event.session_id)

    return {"status": "accepted", "message": "Telemetry event queued for processing"}
