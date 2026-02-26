import hmac
import hashlib
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..db import models
import logging

logger = logging.getLogger(__name__)

class AuditLogger:
    def __init__(self, secret_key: str, db_session_factory):
        self.secret_key = secret_key.encode()
        self.db_session_factory = db_session_factory

    def _hash(self, data: dict) -> str:
        message = json.dumps(data, sort_keys=True).encode()
        return hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()

    def log(self, event_type: str, user_id: str, details: dict, session_id: str = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "details": details,
        }
        signature = self._hash(entry)
        entry["signature"] = signature

        db = self.db_session_factory()
        try:
            audit = models.AuditLog(
                timestamp=datetime.utcnow(),
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                details=details,
                signature=signature
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            db.rollback()
        finally:
            db.close()

    def verify_log(self, log_entry: dict) -> bool:
        original_sig = log_entry.pop("signature", None)
        if not original_sig:
            return False
        computed = self._hash(log_entry)
        return hmac.compare_digest(computed, original_sig)
