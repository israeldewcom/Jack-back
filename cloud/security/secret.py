"""
Secrets management – retrieves secrets from environment or vault.
"""
import os
import boto3
from botocore.exceptions import ClientError

class SecretsManager:
    def __init__(self):
        self.use_vault = os.getenv("SECRETS_BACKEND", "env") == "vault"
        if self.use_vault:
            # Initialize Vault client (simplified)
            import hvac
            self.vault_client = hvac.Client(
                url=os.getenv("VAULT_ADDR"),
                token=os.getenv("VAULT_TOKEN")
            )
        else:
            self.vault_client = None

    def get_secret(self, key: str, default=None):
        if self.use_vault:
            try:
                secret = self.vault_client.secrets.kv.v2.read_secret_version(path=key)
                return secret['data']['data']['value']
            except:
                return default
        else:
            return os.getenv(key, default)
