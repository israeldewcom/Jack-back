from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ...db.database import get_db
from ...db import models
from ...core.security import generate_api_key, hash_api_key
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/apikeys", tags=["api keys"])

class APIKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = None

class APIKeyOut(BaseModel):
    id: int
    name: str
    last_chars: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool

    class Config:
        orm_mode = True

@router.post("/", response_model=APIKeyOut)
def create_api_key(
    req: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    user_id = current_user["id"]

    # Generate key
    plain_key = generate_api_key()
    key_hash = hash_api_key(plain_key)
    last_chars = plain_key[-4:]

    expires_at = None
    if req.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)

    api_key = models.APIKey(
        tenant_id=tenant_id,
        user_id=user_id,
        name=req.name,
        key_hash=key_hash,
        last_chars=last_chars,
        expires_at=expires_at
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Return the plain key only once
    return {**APIKeyOut.from_orm(api_key).dict(), "plain_key": plain_key}


@router.get("/", response_model=List[APIKeyOut])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    keys = db.query(models.APIKey).filter(
        models.APIKey.tenant_id == tenant_id,
        models.APIKey.user_id == current_user["id"]
    ).all()
    return keys


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    key = db.query(models.APIKey).filter(
        models.APIKey.id == key_id,
        models.APIKey.tenant_id == current_user["tenant_id"],
        models.APIKey.user_id == current_user["id"]
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    db.commit()
    return {"message": "API key revoked"}
