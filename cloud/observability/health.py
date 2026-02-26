"""
Deep health checks for all dependencies.
"""
from fastapi import APIRouter
import redis.asyncio as aioredis
from sqlalchemy import create_engine, text
from aiokafka import AIOKafkaProducer
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("")
async def health_check():
    status = {"status": "ok", "components": {}, "version": os.getenv("APP_VERSION", "unknown")}

    # Database
    try:
        engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["components"]["db"] = "ok"
    except Exception as e:
        status["components"]["db"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Redis
    try:
        r = await aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), socket_connect_timeout=2)
        await r.ping()
        status["components"]["redis"] = "ok"
    except Exception as e:
        status["components"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Kafka (optional)
    if os.getenv("KAFKA_BOOTSTRAP_SERVERS"):
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
                request_timeout_ms=3000
            )
            await producer.start()
            await producer.send("healthcheck", b"ping")
            await producer.stop()
            status["components"]["kafka"] = "ok"
        except Exception as e:
            status["components"]["kafka"] = f"error: {str(e)}"
            # Not marking degraded if Kafka is optional
    else:
        status["components"]["kafka"] = "disabled"

    # MLflow
    try:
        import mlflow
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
        mlflow.search_experiments()  # lightweight call
        status["components"]["mlflow"] = "ok"
    except Exception as e:
        status["components"]["mlflow"] = f"error: {str(e)}"
        # optional

    return status
