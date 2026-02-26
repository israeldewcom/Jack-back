"""
Adaptive thresholds based on user context, with caching.
"""
from sqlalchemy.orm import Session
from datetime import datetime
import redis.asyncio as aioredis
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AdaptiveThresholds:
    """
    Context‑aware thresholds that can be overridden by ML models.
    """
    def __init__(self, db_session_factory, redis_client: aioredis.Redis, cache_ttl: int = 300):
        self.db_session_factory = db_session_factory
        self.redis = redis_client
        self.cache_ttl = cache_ttl

    async def get_thresholds(self, context: dict) -> Dict[str, int]:
        """
        Return low/medium/high thresholds for given context.
        """
        cache_key = f"thresholds:{json.dumps(context, sort_keys=True)}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Default thresholds (configurable via env)
        defaults = {
            "low": int(os.getenv("THRESHOLD_LOW_DEFAULT", "70")),
            "medium": int(os.getenv("THRESHOLD_MEDIUM_DEFAULT", "50")),
            "high": int(os.getenv("THRESHOLD_HIGH_DEFAULT", "30"))
        }

        # In a real system, you might query a thresholds table with ML-derived values
        # For now, we use a simple rule: if user is admin, thresholds are stricter
        if context.get("user_role") == "admin":
            thresholds = {
                "low": int(os.getenv("THRESHOLD_LOW_ADMIN", "80")),
                "medium": int(os.getenv("THRESHOLD_MEDIUM_ADMIN", "60")),
                "high": int(os.getenv("THRESHOLD_HIGH_ADMIN", "40"))
            }
        else:
            # Night time (0-6) – lower trust expected
            hour = context.get("hour", 12)
            if hour < 6 or hour > 22:
                thresholds = {
                    "low": int(os.getenv("THRESHOLD_LOW_NIGHT", "60")),
                    "medium": int(os.getenv("THRESHOLD_MEDIUM_NIGHT", "40")),
                    "high": int(os.getenv("THRESHOLD_HIGH_NIGHT", "20"))
                }
            else:
                thresholds = defaults

        # Store in cache
        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(thresholds))
        return thresholds
