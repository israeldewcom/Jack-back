import os
from ..feature_store.feature_store import FeatureStore
from ..model_registry.registry import ModelRegistry
from ..engine.risk import RiskEngine
from ..engine.online_learner import OnlineRiskLearner
from ..threat_intel.aggregator import ThreatIntelAggregator
from ..db.database import SessionLocal
from ..db import models
from ..observability.logging import logger
import redis.asyncio as aioredis

# Global singletons (initialized once at startup)
redis_client = aioredis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
feature_store = FeatureStore(os.getenv("DATABASE_URL"), os.getenv("REDIS_URL"))
model_registry = ModelRegistry()
threat_intel = ThreatIntelAggregator(redis_client)
online_learner = OnlineRiskLearner(redis_client)
risk_engine = RiskEngine(feature_store, model_registry, threat_intel, None, online_learner)  # adaptive thresholds injected later

async def process_telemetry(telemetry: dict):
    """Process a telemetry event – idempotent."""
    db = SessionLocal()
    try:
        # Store raw telemetry (if not already stored – using upsert)
        existing = db.query(models.Telemetry).filter_by(
            session_id=telemetry["session_id"],
            timestamp=telemetry["timestamp"]
        ).first()
        if not existing:
            db_telemetry = models.Telemetry(**telemetry)
            db.add(db_telemetry)
            db.commit()

        # Compute risk
        risk_result = await risk_engine.compute_risk(telemetry)

        # Update session
        session = db.query(models.Session).filter_by(id=telemetry["session_id"]).first()
        if not session:
            session = models.Session(
                id=telemetry["session_id"],
                user_id=telemetry["user_id"],
                ip=telemetry["ip"],
                device=telemetry.get("device", "unknown"),
                trust_score=risk_result["trust_score"],
                risk_level=risk_result["risk_level"]
            )
            db.add(session)
        else:
            session.trust_score = risk_result["trust_score"]
            session.risk_level = risk_result["risk_level"]
            session.last_activity = telemetry["timestamp"]
        db.commit()

        # Evaluate policies
        from ..engine.policy import PolicyEngine
        policy_engine = PolicyEngine(lambda: SessionLocal())
        actions = policy_engine.evaluate({
            "trust_score": risk_result["trust_score"],
            "risk_level": risk_result["risk_level"],
            "user_role": telemetry.get("role", "standard"),
            "ip": telemetry["ip"]
        })
        if actions:
            logger.info(f"Policy actions for session {telemetry['session_id']}: {actions}")

    except Exception as e:
        logger.exception(f"Error processing telemetry: {e}")
    finally:
        db.close()
