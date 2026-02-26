"""
Authentication dependencies for FastAPI.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .utils import decode_token
from ..db.database import SessionLocal
from ..db import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Validate token and return user info."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Optionally verify user still exists in DB
    db = SessionLocal()
    user = db.query(models.User).filter_by(username=payload.get("sub")).first()
    db.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"sub": user.username, "role": user.role, "user_id": user.id}
