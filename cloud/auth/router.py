"""
Authentication router: register, login, refresh.
Uses structured logging and audit trail.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
import os
from typing import Optional

from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..db import models
from ..auth.utils import (
    create_access_token,
    verify_password,
    get_password_hash,
    decode_token
)
from ..audit.logger import AuditLogger
from ..observability.logging import StructuredLogger
from ..observability.metrics import login_attempts_counter

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Structured logger for this module
logger = StructuredLogger(__name__)

# Audit logger (initialised lazily)
def get_audit_logger():
    return AuditLogger(
        secret_key=os.getenv("AUDIT_SECRET", "default-audit-secret-change-me"),
        db_session_factory=SessionLocal
    )

# -------------------- Pydantic models --------------------
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

class RegisterResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# -------------------- Endpoints --------------------
@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(request: RegisterRequest):
    """
    Create a new user account.
    """
    db = SessionLocal()
    try:
        # Check if username or email already exists
        if db.query(models.User).filter_by(username=request.username).first():
            logger.warning("Registration failed: username already exists", username=request.username)
            raise HTTPException(status_code=400, detail="Username already exists")
        if db.query(models.User).filter_by(email=request.email).first():
            logger.warning("Registration failed: email already registered", email=request.email)
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password and create user
        hashed = get_password_hash(request.password)
        user = models.User(
            username=request.username,
            email=request.email,
            hashed_password=hashed,
            role="standard",
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Audit log
        audit = get_audit_logger()
        audit.log(
            event_type="user_registered",
            user_id=user.username,
            details={"email": user.email}
        )

        logger.info("User registered successfully", user_id=user.id, username=user.username)
        return RegisterResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at
        )
    finally:
        db.close()

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT access token.
    """
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(username=request.username).first()
        if not user or not verify_password(request.password, user.hashed_password):
            login_attempts_counter.labels(status="failure").inc()
            logger.warning("Login failed: invalid credentials", username=request.username)
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        # Create access token
        access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role, "user_id": user.id},
            expires_delta=access_token_expires
        )

        login_attempts_counter.labels(status="success").inc()
        logger.info("User logged in", user_id=user.id, username=user.username)

        # Audit log
        audit = get_audit_logger()
        audit.log(
            event_type="user_login",
            user_id=user.username,
            details={"method": "password"}
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=int(access_token_expires.total_seconds()),
            user={
                "username": user.username,
                "role": user.role,
                "user_id": user.id,
                "email": user.email
            }
        )
    finally:
        db.close()

@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(token: str = Depends(oauth2_scheme)):
    """
    Issue a new access token using a valid refresh token (old token).
    """
    payload = decode_token(token)
    if not payload:
        logger.warning("Refresh attempt with invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    # Optionally check if user still exists and is active
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(username=payload.get("sub")).first()
        if not user or not user.is_active:
            logger.warning("Refresh failed: user not found or inactive", username=payload.get("sub"))
            raise HTTPException(status_code=401, detail="User not active")
    finally:
        db.close()

    # Create new token with same claims but new expiration
    new_token = create_access_token(
        data={"sub": payload["sub"], "role": payload["role"], "user_id": payload["user_id"]}
    )
    logger.info("Token refreshed", username=payload["sub"])
    return RefreshResponse(access_token=new_token)

# Optional: logout endpoint (client‑side only, but we can blacklist tokens if needed)
@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """
    Invalidate the token (client‑side; here we just log the event).
    In a production system, you might add the token to a blacklist.
    """
    payload = decode_token(token)
    username = payload.get("sub") if payload else "unknown"
    logger.info("User logged out", username=username)

    audit = get_audit_logger()
    audit.log(
        event_type="user_logout",
        user_id=username,
        details={"method": "api"}
    )
    return {"detail": "Logged out successfully"}
