import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import redis.asyncio as aioredis
import json
import logging
from typing import Optional
from ..observability.logging import logger

class FeatureStore:
    def __init__(self, db_uri: str, redis_url: str = "redis://redis:6379/0"):
        self.db_engine = create_engine(db_uri)
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        logger.info("FeatureStore initialized")

    async def get_user_features(self, user_id: str, timestamp: datetime) -> dict:
        cache_key = f"features:user:{user_id}:{timestamp.isoformat()}"
        cached = await self.redis.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            return json.loads(cached)

        # Compute features from pre‑aggregated tables (or raw if needed)
        # Using precomputed daily aggregates for performance
        start_time = timestamp - timedelta(hours=24)
        query = text("""
            SELECT
                AVG(keystroke_speed) as avg_keystroke_speed,
                AVG(mouse_speed) as avg_mouse_speed,
                COUNT(DISTINCT ip_address) as unique_ips,
                MAX(risk_score) as max_risk_score_24h,
                COUNT(*) as event_count
            FROM telemetry_hourly_agg   -- precomputed table
            WHERE user_id = :user_id
              AND hour >= :start_time
        """)
        with self.db_engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id, "start_time": start_time}).fetchone()

        features = {
            "event_count": result.event_count or 0,
            "avg_keystroke_speed": float(result.avg_keystroke_speed or 0.0),
            "avg_mouse_speed": float(result.avg_mouse_speed or 0.0),
            "unique_ips": result.unique_ips or 0,
            "max_risk_score_24h": float(result.max_risk_score_24h or 0.0),
            "hour_of_day": timestamp.hour,
            "day_of_week": timestamp.weekday(),
        }

        # Cache for 1 hour (3600 seconds)
        await self.redis.setex(cache_key, 3600, json.dumps(features))
        logger.debug(f"Computed features for user {user_id}")
        return features

    async def precompute_aggregates(self, start: datetime, end: datetime):
        """Batch job to populate telemetry_hourly_agg."""
        # Implementation for scheduled backfill
        pass
