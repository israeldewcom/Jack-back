"""
Duo MFA provider implementation.
"""
import os
import duo_client
from ..base import MFAProvider
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class DuoMFAProvider(MFAProvider):
    def __init__(self):
        self.ikey = os.getenv("DUO_IKEY")
        self.skey = os.getenv("DUO_SKEY")
        self.host = os.getenv("DUO_API_HOST")
        if not all([self.ikey, self.skey, self.host]):
            raise ValueError("Duo credentials not fully configured")
        self.client = duo_client.Auth(
            ikey=self.ikey,
            skey=self.skey,
            host=self.host
        )
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def challenge(self, user_id: str, session_id: str) -> dict:
        # Duo's client is synchronous, so run in thread pool
        loop = asyncio.get_event_loop()
        try:
            resp = await loop.run_in_executor(
                self.executor,
                self.client.auth,
                username=user_id,
                factor="push",
                device="auto",
                async_txn=True
            )
            if resp["result"] == "allow":
                return {"success": True, "txid": resp["txid"]}
            else:
                logger.warning(f"Duo challenge failed for {user_id}: {resp}")
                return {"success": False, "error": resp.get("status_msg")}
        except Exception as e:
            logger.exception(f"Duo challenge exception for {user_id}")
            return {"success": False, "error": str(e)}

    async def verify(self, user_id: str, challenge_id: str, response: str) -> bool:
        # For push, response is usually not needed; we poll status
        loop = asyncio.get_event_loop()
        try:
            resp = await loop.run_in_executor(
                self.executor,
                self.client.auth_status,
                txid=challenge_id
            )
            return resp.get("result") == "allow"
        except Exception as e:
            logger.exception(f"Duo verification exception for {user_id}")
            return False
