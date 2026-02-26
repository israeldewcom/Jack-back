"""
Policy engine for evaluating rules based on context.
"""
from sqlalchemy.orm import Session
from ..db import models
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    def evaluate(self, context: dict) -> List[Dict[str, Any]]:
        """
        Evaluate all enabled rules against context.
        Returns list of actions with rule names.
        """
        db = self.db_session_factory()
        try:
            rules = db.query(models.PolicyRule).filter_by(enabled=True).order_by(models.PolicyRule.priority).all()
            actions = []
            for rule in rules:
                if self._matches(rule.condition, context):
                    actions.append({"action": rule.action, "rule": rule.name})
                    rule.triggered_count += 1
                    db.commit()
                    logger.info(f"Policy rule '{rule.name}' triggered with action {rule.action}")
            return actions
        finally:
            db.close()

    def _matches(self, condition: dict, context: dict) -> bool:
        """
        Recursively evaluate condition against context.
        Condition format: {"field": {"operator": value}} or {"and": [conditions]} or {"or": [conditions]}
        """
        if "and" in condition:
            return all(self._matches(sub, context) for sub in condition["and"])
        if "or" in condition:
            return any(self._matches(sub, context) for sub in condition["or"])
        # Simple field comparison
        for field, ops in condition.items():
            if field not in context:
                return False
            val = context[field]
            for op, target in ops.items():
                if op == "lt":
                    if not (val < target):
                        return False
                elif op == "lte":
                    if not (val <= target):
                        return False
                elif op == "gt":
                    if not (val > target):
                        return False
                elif op == "gte":
                    if not (val >= target):
                        return False
                elif op == "eq":
                    if not (val == target):
                        return False
                elif op == "neq":
                    if not (val != target):
                        return False
                elif op == "in":
                    if val not in target:
                        return False
                else:
                    logger.warning(f"Unknown operator {op} in policy condition")
                    return False
        return True
