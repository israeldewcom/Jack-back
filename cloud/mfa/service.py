from .providers.duo import DuoMFAProvider
from .providers.totp import TOTPProvider
from .providers.sms import SMSProvider
from ..db.database import SessionLocal
from ..db import models
import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MFAService:
    def __init__(self):
        self.providers = {
            "duo": DuoMFAProvider(),
            "totp": TOTPProvider(),
            "sms": SMSProvider()
        }

    async def challenge(self, user_id: str, session_id: str, provider: str = "duo") -> dict:
        if provider not in self.providers:
            raise ValueError(f"Unknown provider {provider}")
        provider_instance = self.providers[provider]
        challenge_data = await provider_instance.challenge(user_id, session_id)
        # Store challenge in DB
        db = SessionLocal()
        challenge = models.MFAChallenge(
            user_id=user_id,
            session_id=session_id,
            provider=provider,
            challenge_id=challenge_data["txid"],
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.add(challenge)
        db.commit()
        return challenge_data

    async def verify(self, user_id: str, challenge_id: str, response: str) -> bool:
        db = SessionLocal()
        challenge = db.query(models.MFAChallenge).filter_by(challenge_id=challenge_id).first()
        if not challenge or challenge.expires_at < datetime.utcnow():
            return False
        provider = self.providers[challenge.provider]
        verified = await provider.verify(user_id, challenge_id, response)
        if verified:
            challenge.verified = True
            db.commit()
        return verified
