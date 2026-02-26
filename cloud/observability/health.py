from fastapi import APIRouter
import redis.asyncio as aioredis
from sqlalchemy import create_engine
from aiokafka import AIOKafkaProducer
import os

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def health_check():
    status = {"status": "ok", "components": {}}
    # Database
    try:
        engine = create_engine(os.getenv("DATABASE_URL"))
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        status["components"]["db"] = "ok"
    except Exception as e:
        status["components"]["db"] = f"error: {e}"
        status["status"] = "degraded"

    # Redis
    try:
        r = await aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        await r.ping()
        status["components"]["redis"] = "ok"
    except Exception as e:
        status["components"]["redis"] = f"error: {e}"
        status["status"] = "degraded"

    # Kafka
    try:
        producer = AIOKafkaProducer(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"))
        await producer.start()
        await producer.send("healthcheck", b"ping")
        await producer.stop()
        status["components"]["kafka"] = "ok"
    except Exception as e:
        status["components"]["kafka"] = f"error: {e}"
        # not marking degraded if Kafka is optional

    # MLflow
    try:
        import mlflow
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
        mlflow.search_experiments()  # simple call
        status["components"]["mlflow"] = "ok"
    except Exception as e:
        status["components"]["mlflow"] = f"error: {e}"
        # optional

    return status
