import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import logging
from ..core.context import get_current_tenant  # new import

logger = logging.getLogger(__name__)

class ModelRegistry:
    def __init__(self, tracking_uri: str = 'http://mlflow:5000'):
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient()
        logger.info(f"ModelRegistry connected to {tracking_uri}")

    def register_model(self, local_path: str, model_name: str, stage: str = 'Staging', tenant_id: int = None) -> int:
        """Log a model and register it with tenant isolation."""
        if tenant_id is None:
            tenant_id = get_current_tenant()
        # Incorporate tenant into model name or tags for isolation
        full_model_name = f"tenant_{tenant_id}_{model_name}" if tenant_id else model_name
        with mlflow.start_run():
            mlflow.sklearn.log_model(local_path, full_model_name)
            run_id = mlflow.active_run().info.run_id
            model_uri = f"runs:/{run_id}/{full_model_name}"
            mlflow.register_model(model_uri, full_model_name)
            latest_version = self.client.get_latest_versions(full_model_name, stages=["None"])[0].version
            self.client.transition_model_version_stage(
                name=full_model_name,
                version=latest_version,
                stage=stage
            )
        logger.info(f"Registered {full_model_name} version {latest_version} as {stage}")
        return latest_version

    def load_model(self, model_name: str, stage: str = 'Production', tenant_id: int = None):
        """Load a model by name and stage, with tenant isolation."""
        if tenant_id is None:
            tenant_id = get_current_tenant()
        full_model_name = f"tenant_{tenant_id}_{model_name}" if tenant_id else model_name
        model_uri = f"models:/{full_model_name}/{stage}"
        logger.info(f"Loading model from {model_uri}")
        return mlflow.sklearn.load_model(model_uri)

    def list_models(self, tenant_id: int = None) -> list:
        """Return all registered models for the current tenant."""
        if tenant_id is None:
            tenant_id = get_current_tenant()
        # Filter by tenant prefix
        all_models = self.client.search_registered_models()
        if tenant_id:
            prefix = f"tenant_{tenant_id}_"
            filtered = [m for m in all_models if m.name.startswith(prefix)]
        else:
            filtered = all_models
        return [dict(rm) for rm in filtered]

    def transition_model(self, model_name: str, version: int, stage: str, tenant_id: int = None):
        """Move a specific model version to a new stage."""
        if tenant_id is None:
            tenant_id = get_current_tenant()
        full_model_name = f"tenant_{tenant_id}_{model_name}" if tenant_id else model_name
        self.client.transition_model_version_stage(full_model_name, version, stage)
        logger.info(f"Transitioned {full_model_name} v{version} to {stage}")
