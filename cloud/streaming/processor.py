"""
Process telemetry events: store, compute risk, update session, evaluate policies.
"""
import os
from ..feature_store.feature_store import FeatureStore
from ..model_registry.registry import ModelRegistry
from ..engine.risk import RiskEngine
from ..engine.online_learner import OnlineRiskLearner
from ..threat_intel.aggregator import ThreatIntelAggregator
from ..engine.adaptive_thresholds import AdaptiveThresholds
from ..engine.policy import PolicyEngine
from ..db.database import SessionLocal
from ..db import models
from ..observability.logging import logger
import redis.asyncio as aioredis

# Global singletons (initialized once at startup)
_redis_client = None
_feature_store = None
_model_registry = None
_threat_intel = None
_online_learner = None
_adaptive_thresholds = None
_risk_engine = None
_policy_engine = None

async def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True
        )
    return _redis_client

async def get_feature_store():
    global _feature_store
    if _feature_store is None:
        _feature_store = FeatureStore(
            os.getenv("DATABASE_URL"),
            os.getenv("REDIS_URL")
        )
    return _feature_store

async def get_model_registry():
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry

async def get_threat_intel():
    global _threat_intel
    if _threat_intel is None:
        redis = await get_redis()
        _threat_intel = ThreatIntelAggregator(redis)
    return _threat_intel

async def get_online_learner():
    global _online_learner
    if _online_learner is None:
        redis = await get_redis()
        _online_learner = OnlineRiskLearner(redis)
    return _online_learner

async def get_adaptive_thresholds():
    global _adaptive_thresholds
    if _adaptive_thresholds is None:
        redis = await get_redis()
        _adaptive_thresholds = AdaptiveThresholds(lambda: SessionLocal(), redis)
    return _adaptive_thresholds

async def get_risk_engine():
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine(
            await get_feature_store(),
            await get_model_registry(),
            await get_threat_intel(),
            await get_adaptive_thresholds(),
            await get_online_learner()
        )
    return _risk_engine

def get_policy_engine():
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine(lambda: SessionLocal())
    return _policy_engine

async def process_telemetry(telemetry: dict):
    """
    Idempotent processing of a telemetry event.
    """
    db = SessionLocal()
    try:
        # 1. Store raw telemetry (if not already stored)
        # Use timestamp + session_id as natural key for idempotency
        existing = db.query(models.Telemetry).filter_by(
            session_id=telemetry["session_id"],
            timestamp=telemetry["timestamp"]
        ).first()
        if not existing:
            db_telemetry = models.Telemetry(**telemetry)
            db.add(db_telemetry)
            db.commit()
            logger.debug(f"Stored telemetry for session {telemetry['session_id']}")

        # 2. Compute risk
        risk_engine = await get_risk_engine()
        risk_result = await risk_engine.compute_risk(telemetry)

        # 3. Update session
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

        # 4. Evaluate policies
        policy_engine = get_policy_engine()
        context = {
            "trust_score": risk_result["trust_score"],
            "risk_level": risk_result["risk_level"],
            "user_role": telemetry.get("role", "standard"),
            "ip": telemetry["ip"],
            "user_id": telemetry["user_id"]
        }
        actions = policy_engine.evaluate(context)
        if actions:
            logger.info(f"Policy actions for session {telemetry['session_id']}: {actions}")
            # If action is "block", we could mark session as terminated, etc.
            # This is just logging for now.

    except Exception as e:
        logger.exception(f"Error processing telemetry: {e}")
        raise  # Re-raise to trigger Kafka retry/DLQ
    finally:
        db.close()
