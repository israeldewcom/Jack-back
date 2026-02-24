from sqlalchemy.orm import Session
from ..db import models
import logging

logger = logging.getLogger(__name__)

class GDPRManager:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    def delete_user_data(self, user_id: str):
        """GDPR right to erasure – delete all personal data."""
        db = self.db_session_factory()
        try:
            # Anonymize or delete records
            user = db.query(models.User).filter_by(id=user_id).first()
            if user:
                user.email = f"deleted_{user_id}@example.com"
                user.name = "Deleted User"
                user.is_active = False
                # Also delete telemetry? Or anonymize IPs?
                db.query(models.Telemetry).filter_by(user_id=user_id).update(
                    {"ip_address": "0.0.0.0", "user_id": f"deleted_{user_id}"}
                )
                db.commit()
                logger.info(f"GDPR deletion for user {user_id}")
        except Exception as e:
            logger.error(f"GDPR deletion failed: {e}")
            db.rollback()
        finally:
            db.close()

    def consent_check(self, user_id: str, purpose: str) -> bool:
        """Check if user has given consent for a specific purpose."""
        db = self.db_session_factory()
        consent = db.query(models.Consent).filter_by(
            user_id=user_id, purpose=purpose, revoked=False
        ).first()
        db.close()
        return consent is not None
