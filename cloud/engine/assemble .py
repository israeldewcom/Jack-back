import numpy as np
from typing import List, Dict
from .model_selector import ModelSelector

class EnsembleRiskModel:
    """Combines multiple models with weighted voting."""
    def __init__(self, models: List[Dict], weights: List[float] = None):
        self.models = models  # list of dicts with 'name', 'stage', 'weight'
        self.weights = weights if weights else [1.0/len(models)]*len(models)

    def predict_proba(self, features: np.ndarray) -> float:
        """Return weighted average probability of risk."""
        probas = []
        for model_info in self.models:
            model = ModelSelector.load_model(model_info['name'], model_info['stage'])
            proba = model.predict_proba(features)[0][1]  # assuming binary
            probas.append(proba)
        weighted = np.average(probas, weights=self.weights)
        return weighted
