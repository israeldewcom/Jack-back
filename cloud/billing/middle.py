"""
Middleware to track API usage for billing.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from ..db.database import SessionLocal
from ..db import models
from datetime import datetime
import os

class BillingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Only count successful requests to certain endpoints
        if response.status_code < 400 and request.url.path.startswith("/v2/"):
            # Extract tenant ID from auth header or JWT
            tenant_id = request.headers.get("X-Tenant-ID") or "unknown"
            # Asynchronously update usage (fire and forget)
            # In production, use a background task or queue to avoid blocking
            self._increment_usage(tenant_id, request.url.path)
        return response

    def _increment_usage(self, tenant_id, path):
        db = SessionLocal()
        try:
            today = datetime.utcnow().date()
            usage = db.query(models.BillingUsage).filter_by(
                tenant_id=tenant_id,
                date=today
            ).first()
            if not usage:
                usage = models.BillingUsage(
                    tenant_id=tenant_id,
                    date=today,
                    api_calls=0,
                    ml_predictions=0,
                    mfa_challenges=0
                )
                db.add(usage)
            usage.api_calls += 1
            if "/risk" in path:  # adjust based on actual endpoints
                usage.ml_predictions += 1
            db.commit()
        except Exception as e:
            # Log but don't fail the request
            import logging
            logging.getLogger(__name__).error(f"Billing update failed: {e}")
        finally:
            db.close()
