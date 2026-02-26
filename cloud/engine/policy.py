from sqlalchemy.orm import Session
from ..db import models
import json
import logging

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self, db_session_factory):
        self.db = db_session_factory

    def evaluate(self, context: dict) -> list:
        """Evaluate all enabled rules against context. Return list of actions."""
        db = self.db()
        rules = db.query(models.PolicyRule).filter_by(enabled=True).order_by(models.PolicyRule.priority).all()
        actions = []
        for rule in rules:
            if self._matches(rule.condition, context):
                actions.append({"action": rule.action, "rule": rule.name})
                rule.triggered_count += 1
                db.commit()
                logger.info(f"Policy rule '{rule.name}' triggered with action {rule.action}")
        return actions

    def _matches(self, condition: dict, context: dict) -> bool:
        """Evaluate condition against context. Condition format: {"field": {"operator": value}}"""
        for field, ops in condition.items():
            if field not in context:
                return False
            val = context[field]
            for op, target in ops.items():
                if op == "lt" and not (val < target):
                    return False
                elif op == "gt" and not (val > target):
                    return False
                elif op == "eq" and not (val == target):
                    return False
                # add more operators as needed
        return True
