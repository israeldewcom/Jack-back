from contextvars import ContextVar
from typing import Optional

# Context variables for the current request
current_tenant_id: ContextVar[Optional[int]] = ContextVar("current_tenant_id", default=None)
current_user_id: ContextVar[Optional[int]] = ContextVar("current_user_id", default=None)
current_user_role: ContextVar[Optional[str]] = ContextVar("current_user_role", default=None)

def set_current_tenant(tenant_id: int):
    current_tenant_id.set(tenant_id)

def get_current_tenant() -> Optional[int]:
    return current_tenant_id.get()

def set_current_user(user_id: int, role: str):
    current_user_id.set(user_id)
    current_user_role.set(role)

def get_current_user() -> Optional[int]:
    return current_user_id.get()

def get_current_role() -> Optional[str]:
    return current_user_role.get()
