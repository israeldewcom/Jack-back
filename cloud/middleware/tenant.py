import re
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from ..db.database import SessionLocal
from ..db.models import Tenant
from ..core.context import set_current_tenant, set_current_user

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract tenant from subdomain (e.g., acme.citp.com)
        host = request.headers.get("host", "")
        subdomain = None
        # Simple subdomain extraction – adjust for your domain
        match = re.search(r"([a-zA-Z0-9-]+)\.citp\.", host)
        if match:
            subdomain = match.group(1)

        # Fallback: header X-Tenant-ID
        tenant_id = request.headers.get("X-Tenant-ID")

        # Or from JWT (handled later in dependency)
        # For now, if we have subdomain, look up tenant
        db = SessionLocal()
        try:
            if subdomain:
                tenant = db.query(Tenant).filter(Tenant.subdomain == subdomain).first()
                if tenant:
                    set_current_tenant(tenant.id)
                else:
                    raise HTTPException(status_code=404, detail="Tenant not found")
            elif tenant_id:
                set_current_tenant(int(tenant_id))
            else:
                # For backward compatibility, maybe use a default tenant
                # Or raise error for v3 endpoints
                pass
        finally:
            db.close()

        response = await call_next(request)
        return response
