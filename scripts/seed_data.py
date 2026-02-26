#!/usr/bin/env python3
"""
Seed initial data (users, policy rules) for development.
"""
from cloud.db.database import SessionLocal
from cloud.db import models
from cloud.auth.utils import get_password_hash
import uuid

def main():
    db = SessionLocal()
    # Create admin user
    admin = models.User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        role="admin",
        mfa_enabled=False
    )
    db.add(admin)

    # Create some policy rules
    rules = [
        models.PolicyRule(
            name="Block high risk",
            description="Block sessions with trust score below 30",
            condition={"trust_score": {"lt": 30}},
            action="block",
            priority=1
        ),
        models.PolicyRule(
            name="MFA for medium risk",
            description="Require MFA when trust score between 30 and 50",
            condition={"trust_score": {"gte": 30, "lt": 50}},
            action="mfa",
            priority=2
        ),
        models.PolicyRule(
            name="Log all events",
            description="Log all telemetry events",
            condition={},  # empty condition always matches
            action="log",
            priority=100
        )
    ]
    for rule in rules:
        db.add(rule)

    db.commit()
    db.close()
    print("Seed data inserted.")

if __name__ == "__main__":
    main()
