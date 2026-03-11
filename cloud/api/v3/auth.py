from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

from ...db.database import get_db
from ...db import models
from ...core.security import hash_password, verify_password, is_valid_email
from ...core.email import send_invitation_email, send_password_reset_email
from ...security.auth import create_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])

# --- Register a new tenant (company) ---
@router.post("/register")
def register_tenant(
    *,
    db: Session = Depends(get_db),
    company_name: str,
    subdomain: str,
    admin_email: str,
    admin_password: str,
    admin_full_name: str
):
    # Validate
    if not is_valid_email(admin_email):
        raise HTTPException(status_code=400, detail="Invalid email")
    if db.query(models.Tenant).filter(models.Tenant.subdomain == subdomain).first():
        raise HTTPException(status_code=400, detail="Subdomain already taken")
    if db.query(models.User).filter(models.User.email == admin_email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create tenant
    tenant = models.Tenant(name=company_name, subdomain=subdomain)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Create admin user
    hashed = hash_password(admin_password)
    user = models.User(
        tenant_id=tenant.id,
        email=admin_email,
        hashed_password=hashed,
        full_name=admin_full_name,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign admin role
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    if not admin_role:
        # Create default roles if not exist
        admin_role = models.Role(name="admin", description="Tenant administrator")
        analyst_role = models.Role(name="analyst", description="Security analyst")
        auditor_role = models.Role(name="auditor", description="Read-only auditor")
        db.add_all([admin_role, analyst_role, auditor_role])
        db.commit()
        db.refresh(admin_role)

    user_role = models.UserRole(user_id=user.id, role_id=admin_role.id)
    db.add(user_role)
    db.commit()

    # Create free subscription
    tenant.plan = "free"
    db.commit()

    # Return JWT
    access_token = create_access_token(data={"sub": user.email, "tenant_id": tenant.id, "role": "admin"})
    return {"access_token": access_token, "token_type": "bearer"}


# --- Login ---
@router.post("/login")
def login(db: Session = Depends(get_db), email: str, password: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Get user's role(s) – for simplicity, take first role
    role = db.query(models.Role).join(models.UserRole).filter(models.UserRole.user_id == user.id).first()
    role_name = role.name if role else "analyst"

    access_token = create_access_token(data={"sub": user.email, "tenant_id": user.tenant_id, "role": role_name})
    return {"access_token": access_token, "token_type": "bearer"}


# --- Invite user (admin only) ---
@router.post("/invite")
def invite_user(
    *,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks,
    email: str,
    role_name: str = "analyst",
    current_user: dict = Depends(get_current_user)  # we need a dependency to extract from JWT
):
    # This requires a dependency that extracts current user from JWT and checks admin role.
    # We'll implement get_current_user later.
    tenant_id = current_user["tenant_id"]
    inviter_name = current_user["full_name"]

    # Check if user already exists
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="User already exists")

    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Create invitation token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    invitation = models.Invitation(
        tenant_id=tenant_id,
        email=email,
        role_id=role.id,
        token=token,
        expires_at=expires_at
    )
    db.add(invitation)
    db.commit()

    # Send email (async)
    invite_link = f"https://{subdomain}.citp.com/accept-invite?token={token}"
    background_tasks.add_task(send_invitation_email, email, inviter_name, invite_link)

    return {"message": "Invitation sent"}


# --- Accept invitation ---
@router.post("/accept-invite")
def accept_invite(token: str, full_name: str, password: str, db: Session = Depends(get_db)):
    invite = db.query(models.Invitation).filter(models.Invitation.token == token).first()
    if not invite or invite.expires_at < datetime.utcnow() or invite.accepted_at:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")

    # Create user
    hashed = hash_password(password)
    user = models.User(
        tenant_id=invite.tenant_id,
        email=invite.email,
        hashed_password=hashed,
        full_name=full_name,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign role
    user_role = models.UserRole(user_id=user.id, role_id=invite.role_id)
    db.add(user_role)
    db.commit()

    # Mark invitation as accepted
    invite.accepted_at = datetime.utcnow()
    db.commit()

    # Return JWT
    access_token = create_access_token(data={"sub": user.email, "tenant_id": user.tenant_id, "role": invite.role.name})
    return {"access_token": access_token, "token_type": "bearer"}


# --- Request password reset ---
@router.post("/forgot-password")
def forgot_password(email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Don't reveal if user exists
        return {"message": "If that email exists, a reset link has been sent"}

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    reset = models.PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
    db.add(reset)
    db.commit()

    reset_link = f"https://{user.tenant.subdomain}.citp.com/reset-password?token={token}"
    background_tasks.add_task(send_password_reset_email, email, reset_link)

    return {"message": "If that email exists, a reset link has been sent"}


# --- Reset password ---
@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    reset = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.token == token).first()
    if not reset or reset.expires_at < datetime.utcnow() or reset.used_at:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == reset.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = hash_password(new_password)
    reset.used_at = datetime.utcnow()
    db.commit()

    return {"message": "Password updated"}
