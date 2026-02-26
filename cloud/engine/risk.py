import numpy as np
from ..feature_store.feature_store import FeatureStore
from ..model_registry.registry import ModelRegistry
from ..threat_intel.aggregator import ThreatIntelAggregator
from ..engine.adaptive_thresholds import AdaptiveThresholds
from ..engine.online_learner import OnlineRiskLearner
from ..observability.metrics import risk_score_histogram
import asyncio
import logging

logger = logging.getLogger(__name__)

class RiskEngine:
    def __init__(self, feature_store: FeatureStore, model_registry: ModelRegistry,
                 threat_intel: ThreatIntelAggregator, adaptive_thresholds: AdaptiveThresholds,
                 online_learner: OnlineRiskLearner):
        self.feature_store = feature_store
        self.model_registry = model_registry
        self.threat_intel = threat_intel
        self.adaptive_thresholds = adaptive_thresholds
        self.online_learner = online_learner

    async def compute_risk(self, telemetry: dict) -> dict:
        """Compute trust score and risk level for a telemetry event."""
        user_id = telemetry["user_id"]
        session_id = telemetry["session_id"]
        timestamp = telemetry["timestamp"]

        # 1. Get features (from feature store, cached)
        features = await self.feature_store.get_user_features(user_id, timestamp)

        # 2. Get IP reputation (async)
        ip_reputation = await self.threat_intel.check_ip(telemetry["ip"])

        # 3. Load production model
        model = self.model_registry.load_model("risk_model", stage="Production")

        # 4. Predict base risk score
        feature_array = np.array([list(features.values())])
        base_score = model.predict_proba(feature_array)[0][1] * 100  # probability as score

        # 5. Adjust with IP reputation
        adjusted_score = base_score * (ip_reputation / 100)

        # 6. Apply adaptive thresholds based on context
        context = {
            "user_role": telemetry.get("role", "standard"),
            "hour": timestamp.hour,
            "ip_reputation": ip_reputation
        }
        thresholds = self.adaptive_thresholds.get_thresholds(context)

        # 7. Determine risk level
        if adjusted_score >= thresholds["low"]:
            risk_level = "low"
        elif adjusted_score >= thresholds["medium"]:
            risk_level = "medium"
        else:
            risk_level = "high"

        # 8. Update online learner if label present
        if "label" in telemetry:
            await self.online_learner.learn_one_async(features, telemetry["label"])

        # 9. Record metric
        risk_score_histogram.labels(level=risk_level).observe(adjusted_score)

        return {
            "trust_score": adjusted_score,
            "risk_level": risk_level,
            "thresholds": thresholds,
            "features_used": list(features.keys())
        }
