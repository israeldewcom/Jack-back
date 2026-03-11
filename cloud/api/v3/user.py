from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...db.database import get_db
from ...db import models
from ...core.context import get_current_tenant, get_current_user, get_current_role
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/users", tags=["users"])

# Dependency to get current user from JWT (we'll need to implement this)
# For brevity, assume we have a function get_current_user_from_token that returns a dict with id, tenant_id, role

class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    roles: List[str]
    last_login_at: Optional[datetime]

    class Config:
        orm_mode = True

@router.get("/", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # admin only
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    tenant_id = current_user["tenant_id"]
    users = db.query(models.User).filter(models.User.tenant_id == tenant_id).all()
    # Enrich with roles
    result = []
    for u in users:
        roles = db.query(models.Role).join(models.UserRole).filter(models.UserRole.user_id == u.id).all()
        user_out = UserOut.from_orm(u)
        user_out.roles = [r.name for r in roles]
        result.append(user_out)
    return result


class UpdateUserRoleRequest(BaseModel):
    user_id: int
    role_name: str

@router.put("/role")
def update_user_role(
    req: UpdateUserRoleRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    tenant_id = current_user["tenant_id"]

    user = db.query(models.User).filter(models.User.id == req.user_id, models.User.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(models.Role).filter(models.Role.name == req.role_name).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Delete existing roles
    db.query(models.UserRole).filter(models.UserRole.user_id == user.id).delete()
    db.commit()

    # Add new role
    user_role = models.UserRole(user_id=user.id, role_id=role.id)
    db.add(user_role)
    db.commit()

    return {"message": "Role updated"}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    tenant_id = current_user["tenant_id"]

    user = db.query(models.User).filter(models.User.id == user_id, models.User.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
