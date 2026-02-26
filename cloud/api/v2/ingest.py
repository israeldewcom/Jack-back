"""
v2 Telemetry ingestion endpoint.
Processes telemetry asynchronously, integrates with feature store, risk engine, etc.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
import os
from ...auth.dependencies import get_current_user
from ...streaming.processor import process_telemetry
from ...audit.logger import AuditLogger
from ...db.database import SessionLocal
from ...observability.metrics import telemetry_counter
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class TelemetryEvent(BaseModel):
    session_id: str
    user_id: str
    ip: str
    keystroke_speed: float = Field(..., ge=0, le=100)
    mouse_speed: float = Field(..., ge=0, le=100)
    timestamp: datetime
    device: Optional[str] = None
    role: Optional[str] = "standard"

    @validator('ip')
    def validate_ip(cls, v):
        # Basic IP format validation
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError('Invalid IP address')
        return v

@router.post("/telemetry", status_code=202)
async def ingest_telemetry(
    event: TelemetryEvent,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Accept telemetry event, queue for async processing.
    Returns 202 Accepted immediately.
    """
    # Optional: verify that the authenticated user matches the event user_id
    if current_user["sub"] != event.user_id:
        # In multi-tenant scenarios, you might allow admins to send on behalf
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="User ID mismatch")

    # Add processing task
    background_tasks.add_task(process_telemetry, event.dict())

    # Increment metric
    telemetry_counter.labels(endpoint="v2").inc()

    # Audit log (async – we can fire and forget, but background_tasks ensures it runs)
    audit = AuditLogger(
        secret_key=os.getenv("AUDIT_SECRET", "default-audit-secret-change-me"),
        db_session_factory=SessionLocal
    )
    background_tasks.add_task(
        audit.log,
        event_type="telemetry_ingested",
        user_id=event.user_id,
        details={"session_id": event.session_id},
        session_id=event.session_id
    )

    logger.info(f"Queued telemetry for session {event.session_id}")
    return {"status": "accepted", "message": "Telemetry event queued for processing"}
