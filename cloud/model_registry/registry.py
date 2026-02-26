"""
MLflow model registry wrapper with caching and version management.
"""
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import logging
from typing import Optional, List, Dict
import os

logger = logging.getLogger(__name__)

class ModelRegistry:
    def __init__(self, tracking_uri: str = None):
        if tracking_uri is None:
            tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
        logger.info(f"ModelRegistry connected to {tracking_uri}")

    def register_model(self, local_path: str, model_name: str, stage: str = 'Staging') -> int:
        """
        Log a model from local path and register it with the given stage.
        Returns version number.
        """
        with mlflow.start_run() as run:
            mlflow.sklearn.log_model(local_path, model_name)
            run_id = run.info.run_id
            model_uri = f"runs:/{run_id}/{model_name}"
            mlflow.register_model(model_uri, model_name)

        # Get latest version
        latest_version = self.client.get_latest_versions(model_name, stages=["None"])[0].version
        self.client.transition_model_version_stage(
            name=model_name,
            version=latest_version,
            stage=stage
        )
        logger.info(f"Registered {model_name} version {latest_version} as {stage}")
        return latest_version

    def load_model(self, model_name: str, stage: str = 'Production'):
        """
        Load a model by name and stage. Caches in memory? MLflow handles internal caching.
        """
        model_uri = f"models:/{model_name}/{stage}"
        logger.info(f"Loading model from {model_uri}")
        return mlflow.sklearn.load_model(model_uri)

    def list_models(self) -> List[Dict]:
        """Return all registered models with their latest versions."""
        models = []
        for rm in self.client.search_registered_models():
            model_info = {"name": rm.name, "latest_versions": []}
            for v in rm.latest_versions:
                model_info["latest_versions"].append({
                    "version": v.version,
                    "stage": v.current_stage,
                    "run_id": v.run_id
                })
            models.append(model_info)
        return models

    def transition_model(self, model_name: str, version: int, stage: str):
        """Move a specific model version to a new stage."""
        self.client.transition_model_version_stage(model_name, version, stage)
        logger.info(f"Transitioned {model_name} v{version} to {stage}")

    def get_model_version(self, model_name: str, stage: str) -> Optional[int]:
        """Get version number of the model in given stage."""
        versions = self.client.get_latest_versions(model_name, stages=[stage])
        if versions:
            return versions[0].version
        return None
