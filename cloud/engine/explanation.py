"""
Risk explanation using SHAP.
"""
import shap
import numpy as np
import pandas as pd
import logging
from ..observability.cache import cache  # hypothetical cache decorator

logger = logging.getLogger(__name__)

class RiskExplainer:
    def __init__(self, model, background_data: pd.DataFrame):
        """
        Initialize with a trained model and background dataset for SHAP.
        """
        self.model = model
        self.background = background_data
        # Use KernelExplainer for any model; for tree models we could use TreeExplainer
        self.explainer = shap.KernelExplainer(model.predict_proba, background)
        logger.info("RiskExplainer initialized")

    @cache(ttl=3600)  # cache explanations for an hour
    def explain(self, features: np.ndarray, num_features: int = 5) -> dict:
        """
        Return top contributing features for a prediction.
        """
        shap_values = self.explainer.shap_values(features)
        # For binary classification, shap_values[1] is for positive class
        if isinstance(shap_values, list):
            shap_vals = shap_values[1][0]  # shape (n_features,)
        else:
            shap_vals = shap_values[0]

        feature_names = self.background.columns.tolist()
        importance = dict(zip(feature_names, shap_vals))
        # Sort by absolute value
        top = sorted(importance.items(), key=lambda x: abs(x[1]), reverse=True)[:num_features]

        return {
            "top_features": [{"name": f, "importance": float(v)} for f, v in top],
            "prediction_proba": float(self.model.predict_proba(features)[0][1])
        }
