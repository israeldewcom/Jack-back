"""
Risk computation engine integrating feature store, model, threat intel, thresholds.
"""
import numpy as np
from typing import Dict, Any
import logging
from ..feature_store.feature_store import FeatureStore
from ..model_registry.registry import ModelRegistry
from ..threat_intel.aggregator import ThreatIntelAggregator
from ..engine.adaptive_thresholds import AdaptiveThresholds
from ..engine.online_learner import OnlineRiskLearner
from ..observability.metrics import risk_score_histogram
import asyncio

logger = logging.getLogger(__name__)

class RiskEngine:
    def __init__(
        self,
        feature_store: FeatureStore,
        model_registry: ModelRegistry,
        threat_intel: ThreatIntelAggregator,
        adaptive_thresholds: AdaptiveThresholds,
        online_learner: OnlineRiskLearner
    ):
        self.feature_store = feature_store
        self.model_registry = model_registry
        self.threat_intel = threat_intel
        self.adaptive_thresholds = adaptive_thresholds
        self.online_learner = online_learner

    async def compute_risk(self, telemetry: dict) -> Dict[str, Any]:
        """
        Compute trust score and risk level asynchronously.
        """
        user_id = telemetry["user_id"]
        session_id = telemetry["session_id"]
        timestamp = telemetry["timestamp"]
        ip = telemetry["ip"]
        role = telemetry.get("role", "standard")

        # 1. Get features (with caching)
        features = await self.feature_store.get_user_features(user_id, timestamp)

        # 2. Get IP reputation from threat intel (with caching)
        ip_reputation = await self.threat_intel.check_ip(ip)

        # 3. Load production model (cached in registry)
        model = self.model_registry.load_model("risk_model", stage="Production")

        # 4. Predict base risk score (model expects feature array)
        feature_array = np.array([list(features.values())])
        base_score = model.predict_proba(feature_array)[0][1] * 100  # probability to 0-100

        # 5. Adjust with IP reputation (weighted average, could be configurable)
        #    Lower reputation increases risk (decreases trust score)
        adjusted_score = base_score * (ip_reputation / 100.0)

        # 6. Apply adaptive thresholds based on context
        context = {
            "user_role": role,
            "hour": timestamp.hour,
            "ip_reputation": ip_reputation,
            "country": telemetry.get("country"),  # could be added via geoip
        }
        thresholds = self.adaptive_thresholds.get_thresholds(context)

        # 7. Determine risk level
        if adjusted_score >= thresholds["low"]:
            risk_level = "low"
        elif adjusted_score >= thresholds["medium"]:
            risk_level = "medium"
        else:
            risk_level = "high"

        # 8. Update online learner if label present (for feedback)
        if "label" in telemetry:
            # Fire and forget – we don't wait for this
            asyncio.create_task(self.online_learner.learn_one_async(features, telemetry["label"]))

        # 9. Record metric
        risk_score_histogram.labels(level=risk_level).observe(adjusted_score)

        logger.info(f"Risk computed for session {session_id}: score={adjusted_score:.2f}, level={risk_level}")

        return {
            "trust_score": round(adjusted_score, 2),
            "risk_level": risk_level,
            "thresholds": thresholds,
            "features_used": list(features.keys()),
            "ip_reputation": ip_reputation,
        }
