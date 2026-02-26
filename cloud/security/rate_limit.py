"""
Rate limiting middleware using Redis.
"""
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as aioredis
import os
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client: aioredis.Redis, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.redis = redis_client
        self.calls = calls
        self.period = period

    async def dispatch(self, request: Request, call_next):
        # Identify client by API key or IP
        client_id = request.headers.get("X-API-Key") or request.client.host
        key = f"rate_limit:{client_id}"
        current = await self.redis.get(key)
        if current and int(current) >= self.calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        pipe = self.redis.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, self.period)
        await pipe.execute()
        response = await call_next(request)
        return response
