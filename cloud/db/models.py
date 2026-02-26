# Additions to existing models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="standard")
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)  # for TOTP
    phone_number = Column(String(20), nullable=True)  # for SMS
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(255), primary_key=True)
    user_id = Column(String(50), index=True, nullable=False)
    ip = Column(String(45))
    device = Column(String(255))
    trust_score = Column(Float, default=100.0)
    risk_level = Column(String(20))
    status = Column(String(20), default="active")
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    terminated_at = Column(DateTime, nullable=True)

class Telemetry(Base):
    __tablename__ = "telemetry"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(255), index=True)
    user_id = Column(String(50), index=True)
    ip = Column(String(45))
    keystroke_speed = Column(Float)
    mouse_speed = Column(Float)
    timestamp = Column(DateTime, index=True)
    # Additional fields can be added without breaking

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String(50), index=True)
    user_id = Column(String(50), index=True)
    session_id = Column(String(255), nullable=True)
    details = Column(JSON)
    signature = Column(String(128))

class FeatureCache(Base):
    __tablename__ = "feature_cache"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(50), index=True)
    feature_name = Column(String(50))
    feature_value = Column(Float)
    computed_at = Column(DateTime, default=datetime.utcnow, index=True)

class MFAChallenge(Base):
    __tablename__ = "mfa_challenges"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(50), index=True)
    session_id = Column(String(255))
    provider = Column(String(20))  # duo, totp, sms
    challenge_id = Column(String(255), unique=True)
    expires_at = Column(DateTime)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PolicyRule(Base):
    __tablename__ = "policy_rules"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(String(255))
    condition = Column(JSON)   # e.g., {"trust_score": {"lt": 50}}
    action = Column(String(50)) # "block", "mfa", "log", "allow"
    priority = Column(Integer, default=100)
    enabled = Column(Boolean, default=True)
    triggered_count = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BillingUsage(Base):
    __tablename__ = "billing_usage"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(50), index=True)  # can be user_id or organization_id
    api_calls = Column(Integer, default=0)
    ml_predictions = Column(Integer, default=0)
    mfa_challenges = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.utcnow, index=True)

class TelemetryHourlyAgg(Base):
    """Precomputed aggregates for feature store."""
    __tablename__ = "telemetry_hourly_agg"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(50), index=True)
    hour = Column(DateTime, index=True)
    avg_keystroke_speed = Column(Float)
    avg_mouse_speed = Column(Float)
    unique_ips = Column(Integer)
    max_risk_score = Column(Float)
    event_count = Column(Integer)
