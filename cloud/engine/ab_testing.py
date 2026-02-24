import hashlib
import random

class ABTest:
    """Assigns users to model variants for A/B testing."""
    def __init__(self, experiment_name: str, variants: List[str], weights: List[float] = None):
        self.experiment_name = experiment_name
        self.variants = variants
        self.weights = weights if weights else [1.0/len(variants)]*len(variants)

    def get_variant(self, user_id: str) -> str:
        """Deterministic assignment based on user_id hash."""
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        r = hash_val % 100 / 100.0
        cumulative = 0.0
        for variant, weight in zip(self.variants, self.weights):
            cumulative += weight
            if r < cumulative:
                return variant
        return self.variants[-1]
