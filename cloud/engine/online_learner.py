"""
Online learning using River, with drift detection and Redis persistence.
"""
import redis.asyncio as aioredis
import pickle
import logging
from river import linear_model, preprocessing, compose, drift
from typing import Optional
import os

logger = logging.getLogger(__name__)

class OnlineRiskLearner:
    def __init__(self, redis_client: aioredis.Redis, model_key: str = "online_risk_model"):
        self.redis = redis_client
        self.model_key = model_key
        self.drift_detector = drift.ADWIN()
        self.model = self._load_model_sync()  # could be async, but we call it in __init__

    def _load_model_sync(self):
        # Synchronous load for simplicity; in production you'd want async startup
        import asyncio
        loop = asyncio.new_event_loop()
        data = loop.run_until_complete(self.redis.get(self.model_key))
        if data:
            return pickle.loads(data)
        else:
            # Default model: logistic regression with feature scaling
            model = compose.Pipeline(
                ('scale', preprocessing.StandardScaler()),
                ('lr', linear_model.LogisticRegression())
            )
            logger.info("Created new online model")
            return model

    async def _save_model(self):
        await self.redis.set(self.model_key, pickle.dumps(self.model))

    async def learn_one_async(self, features: dict, label: bool):
        """Update model with a single sample (async)."""
        self.model.learn_one(features, label)

        # Check for concept drift
        proba = self.model.predict_proba_one(features).get(True, 0.5)
        self.drift_detector.update(proba)
        if self.drift_detector.drift_detected:
            logger.warning("Concept drift detected – consider retraining the production model.")

        await self._save_model()

    async def predict_proba_one(self, features: dict) -> float:
        """Return probability of risk (positive class)."""
        proba = self.model.predict_proba_one(features)
        return proba.get(True, 0.5)
