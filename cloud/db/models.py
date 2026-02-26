# cloud/db/models.py (additions)
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    role = Column(String, default="standard")
    mfa_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    ip = Column(String)
    device = Column(String)
    trust_score = Column(Float, default=100.0)
    risk_level = Column(String)
    status = Column(String, default="active")
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

class Telemetry(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True)
    session_id = Column(String, index=True)
    user_id = Column(String, index=True)
    ip = Column(String)
    keystroke_speed = Column(Float)
    mouse_speed = Column(Float)
    timestamp = Column(DateTime, index=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String)
    user_id = Column(String, index=True)
    session_id = Column(String, nullable=True)
    details = Column(JSON)
    signature = Column(String)

class FeatureCache(Base):
    __tablename__ = "feature_cache"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    feature_name = Column(String)
    feature_value = Column(Float)
    computed_at = Column(DateTime, default=datetime.utcnow)

class MFAChallenge(Base):
    __tablename__ = "mfa_challenges"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    session_id = Column(String)
    provider = Column(String)
    challenge_id = Column(String, unique=True)
    expires_at = Column(DateTime)
    verified = Column(Boolean, default=False)

class PolicyRule(Base):
    __tablename__ = "policy_rules"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    condition = Column(JSON)   # e.g., {"trust_score": {"lt": 50}}
    action = Column(String)     # "block", "mfa", "log"
    priority = Column(Integer)
    enabled = Column(Boolean, default=True)
    triggered_count = Column(Integer, default=0)

class BillingUsage(Base):
    __tablename__ = "billing_usage"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String)
    api_calls = Column(Integer, default=0)
    ml_predictions = Column(Integer, default=0)
    mfa_challenges = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.utcnow)
