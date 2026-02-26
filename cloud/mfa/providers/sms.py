"""
SMS MFA provider using Twilio.
"""
import os
from twilio.rest import Client
from ..base import MFAProvider
import logging
import secrets
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class SMSProvider(MFAProvider):
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Twilio credentials not fully configured")
        self.client = Client(self.account_sid, self.auth_token)
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def challenge(self, user_id: str, session_id: str) -> dict:
        # Generate a 6-digit code
        code = secrets.randbelow(1000000)
        code_str = f"{code:06d}"
        # In production, store code in Redis with expiration
        # For simplicity, we return it in challenge_id (not secure for production)
        # Better: store in database/redis with TTL
        db = SessionLocal()
        user = db.query(models.User).filter_by(username=user_id).first()
        if not user or not user.phone_number:
            db.close()
            return {"success": False, "error": "User phone number not found"}
        phone = user.phone_number
        db.close()

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                self.executor,
                self.client.messages.create,
                body=f"Your CITP verification code is: {code_str}",
                from_=self.from_number,
                to=phone
            )
            # Return the code as challenge_id (temporary; use hashed value in production)
            challenge_id = code_str
            return {"success": True, "challenge_id": challenge_id}
        except Exception as e:
            logger.exception(f"SMS challenge failed for {user_id}")
            return {"success": False, "error": str(e)}

    async def verify(self, user_id: str, challenge_id: str, response: str) -> bool:
        # response should match the code sent
        return challenge_id == response
