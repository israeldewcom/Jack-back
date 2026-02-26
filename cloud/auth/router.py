"""
Authentication endpoints: register, login, refresh.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import os
from .utils import (
    create_access_token, verify_password, get_password_hash,
    decode_token
)
from ..db.database import SessionLocal
from ..db import models
from ..observability.metrics import login_attempts_counter

router = APIRouter()

@router.post("/register")
async def register(username: str, email: str, password: str):
    db = SessionLocal()
    if db.query(models.User).filter_by(username=username).first():
        db.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(models.User).filter_by(email=email).first():
        db.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(password)
    user = models.User(
        username=username,
        email=email,
        hashed_password=hashed,
        role="standard"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return {"msg": "User created", "user_id": user.id}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(models.User).filter_by(username=form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        login_attempts_counter.labels(status="failure").inc()
        db.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Update last login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    db.close()
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id},
        expires_delta=access_token_expires
    )
    login_attempts_counter.labels(status="success").inc()
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": access_token_expires.total_seconds(),
        "user": {"username": user.username, "role": user.role, "user_id": user.id}
    }

@router.post("/refresh")
async def refresh_token(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Generate new token with same claims but new expiration
    new_token = create_access_token(
        data={"sub": payload["sub"], "role": payload["role"], "user_id": payload["user_id"]}
    )
    return {"access_token": new_token, "token_type": "bearer"}
