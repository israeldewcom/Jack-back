"""
TOTP MFA provider (Google Authenticator, etc.)
"""
import pyotp
from ..base import MFAProvider
from ...db.database import SessionLocal
from ...db import models
import logging
import secrets

logger = logging.getLogger(__name__)

class TOTPProvider(MFAProvider):
    async def challenge(self, user_id: str, session_id: str) -> dict:
        # Generate a new TOTP secret if user doesn't have one
        db = SessionLocal()
        user = db.query(models.User).filter_by(username=user_id).first()
        if not user:
            db.close()
            return {"success": False, "error": "User not found"}
        if not user.mfa_secret:
            # First time: generate and store secret
            secret = pyotp.random_base32()
            user.mfa_secret = secret
            db.commit()
        else:
            secret = user.mfa_secret
        db.close()

        # Return provisioning URI (for QR code) and a challenge ID
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=user_id, issuer_name="CITP")
        challenge_id = secrets.token_urlsafe(16)
        return {
            "success": True,
            "challenge_id": challenge_id,
            "provisioning_uri": provisioning_uri,
            "message": "Scan QR code with Google Authenticator"
        }

    async def verify(self, user_id: str, challenge_id: str, response: str) -> bool:
        # response is the OTP code
        db = SessionLocal()
        user = db.query(models.User).filter_by(username=user_id).first()
        if not user or not user.mfa_secret:
            db.close()
            return False
        totp = pyotp.TOTP(user.mfa_secret)
        valid = totp.verify(response)
        db.close()
        return valid
