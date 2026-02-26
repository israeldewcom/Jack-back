import redis.asyncio as aioredis
import pickle
import logging
from river import linear_model, preprocessing, compose, drift
from typing import Optional

logger = logging.getLogger(__name__)

class OnlineRiskLearner:
    def __init__(self, redis_client: aioredis.Redis, model_key: str = "online_risk_model"):
        self.redis = redis_client
        self.model_key = model_key
        self.drift_detector = drift.ADWIN()
        self.model = self._load_model_sync()  # sync for simplicity, but could be async

    def _load_model_sync(self):
        data = self.redis.get(self.model_key)
        if data:
            return pickle.loads(data)
        else:
            model = compose.Pipeline(
                ("scale", preprocessing.StandardScaler()),
                ("lr", linear_model.LogisticRegression())
            )
            logger.info("Created new online model")
            return model

    async def _save_model(self):
        await self.redis.set(self.model_key, pickle.dumps(self.model))

    async def learn_one_async(self, features: dict, label: bool):
        # Update model
        self.model.learn_one(features, label)

        # Check drift
        proba = self.model.predict_proba_one(features).get(True, 0.5)
        self.drift_detector.update(proba)
        if self.drift_detector.drift_detected:
            logger.warning("Concept drift detected – consider retraining.")

        await self._save_model()

    async def predict_proba_one(self, features: dict) -> float:
        proba = self.model.predict_proba_one(features)
        return proba.get(True, 0.5)
