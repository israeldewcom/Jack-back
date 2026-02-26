"""
MFA orchestration service.
"""
from .providers.duo import DuoMFAProvider
from .providers.totp import TOTPProvider
from .providers.sms import SMSProvider
from ..db.database import SessionLocal
from ..db import models
import logging
import uuid
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class MFAService:
    def __init__(self):
        self.providers = {}
        if os.getenv("DUO_IKEY"):
            self.providers["duo"] = DuoMFAProvider()
        if os.getenv("TWILIO_ACCOUNT_SID"):
            self.providers["sms"] = SMSProvider()
        # TOTP always available
        self.providers["totp"] = TOTPProvider()

    async def challenge(self, user_id: str, session_id: str, provider: str = "duo") -> dict:
        if provider not in self.providers:
            raise ValueError(f"Unknown provider {provider}")
        provider_instance = self.providers[provider]
        challenge_data = await provider_instance.challenge(user_id, session_id)
        if not challenge_data.get("success"):
            return challenge_data

        # Store challenge in DB
        db = SessionLocal()
        challenge = models.MFAChallenge(
            user_id=user_id,
            session_id=session_id,
            provider=provider,
            challenge_id=challenge_data.get("challenge_id", str(uuid.uuid4())),
            expires_at=datetime.utcnow() + timedelta(minutes=int(os.getenv("MFA_CHALLENGE_TTL_MINUTES", "5"))),
            verified=False
        )
        db.add(challenge)
        db.commit()
        challenge_data["challenge_id"] = challenge.challenge_id  # ensure we have it
        db.close()
        return challenge_data

    async def verify(self, user_id: str, challenge_id: str, response: str) -> bool:
        db = SessionLocal()
        challenge = db.query(models.MFAChallenge).filter_by(challenge_id=challenge_id).first()
        if not challenge or challenge.expires_at < datetime.utcnow():
            db.close()
            return False
        provider = self.providers.get(challenge.provider)
        if not provider:
            db.close()
            return False
        verified = await provider.verify(user_id, challenge_id, response)
        if verified:
            challenge.verified = True
            db.commit()
        db.close()
        return verified
