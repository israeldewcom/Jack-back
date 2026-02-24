from fastapi import WebSocket
from typing import List, Dict
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # org_id -> list

    async def connect(self, websocket: WebSocket, org_id: str):
        await websocket.accept()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = []
        self.active_connections[org_id].append(websocket)
        logger.info(f"WebSocket connected for org {org_id}")

    def disconnect(self, websocket: WebSocket, org_id: str):
        if org_id in self.active_connections:
            self.active_connections[org_id].remove(websocket)

    async def broadcast_to_org(self, org_id: str, message: dict):
        if org_id in self.active_connections:
            for connection in self.active_connections[org_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass  # connection closed

manager = ConnectionManager()

async def notify_risk_update(org_id: str, user_id: str, new_risk: float):
    await manager.broadcast_to_org(org_id, {
        "type": "risk_update",
        "user_id": user_id,
        "risk_score": new_risk,
        "timestamp": datetime.utcnow().isoformat()
    })
