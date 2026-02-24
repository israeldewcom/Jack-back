import redis
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..db import models

class UsageTracker:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "usage"

    async def track_event(self, org_id: int, event_type: str, count: int = 1):
        """Increment usage counter for an organization."""
        key = f"{self.prefix}:{org_id}:{event_type}:{datetime.utcnow().strftime('%Y-%m-%d')}"
        self.redis.incrby(key, count)
        self.redis.expire(key, 60*60*24*31)  # keep for 31 days

    def get_daily_usage(self, org_id: int, event_type: str, date: str) -> int:
        key = f"{self.prefix}:{org_id}:{event_type}:{date}"
        val = self.redis.get(key)
        return int(val) if val else 0

    async def check_quota(self, org_id: int, event_type: str, db: Session) -> bool:
        """Check if organization has exceeded its quota."""
        org = db.query(models.Organization).filter_by(id=org_id).first()
        if not org:
            return False
        # Get plan limits
        plan = PLANS.get(org.subscription_tier, PLANS["free"])
        daily_limit = plan.get("limits", {}).get(event_type, float("inf"))
        today = datetime.utcnow().strftime('%Y-%m-%d')
        used = self.get_daily_usage(org_id, event_type, today)
        return used < daily_limit
