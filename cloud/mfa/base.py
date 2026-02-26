from abc import ABC, abstractmethod

class MFAProvider(ABC):
    @abstractmethod
    async def challenge(self, user_id: str, session_id: str) -> dict:
        """Initiate MFA challenge, return challenge data (e.g., transaction ID)."""
        pass

    @abstractmethod
    async def verify(self, user_id: str, challenge_id: str, response: str) -> bool:
        """Verify the MFA response."""
        pass
