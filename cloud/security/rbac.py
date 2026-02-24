from functools import wraps
from fastapi import HTTPException

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            # Check user roles/permissions
            if permission not in user.permissions:
                raise HTTPException(status_code=403, detail="Forbidden")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
