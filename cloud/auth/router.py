# cloud/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from datetime import timedelta
from ..db.database import SessionLocal
from ..db import models
from .utils import create_access_token, verify_password, get_password_hash
from ..security.auth import decode_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
async def register(username: str, email: str, password: str):
    db = SessionLocal()
    if db.query(models.User).filter_by(username=username).first():
        raise HTTPException(400, "Username already exists")
    hashed = get_password_hash(password)
    user = models.User(username=username, email=email, hashed_password=hashed)
    db.add(user)
    db.commit()
    return {"msg": "User created"}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(models.User).filter_by(username=form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "user": {"username": user.username, "role": user.role}}

@router.post("/refresh")
async def refresh_token(token: str = Depends(OAuth2PasswordBearer(tokenUrl="auth/login"))):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token")
    new_token = create_access_token(data={"sub": payload["sub"], "role": payload["role"]})
    return {"access_token": new_token}
