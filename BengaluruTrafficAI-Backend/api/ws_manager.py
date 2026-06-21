"""
BengaluruTrafficAI — WebSocket Manager
Component 4b: Manages live WebSocket connections for real-time dashboard updates.
"""

import json
import asyncio
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger("websocket")


class ConnectionManager:
    """
    Manages all active WebSocket connections.
    Broadcasts violation events to every connected dashboard client.
    """

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"WS connected | total={len(self.active)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"WS disconnected | total={len(self.active)}")

    async def broadcast(self, data: dict):
        """Send JSON payload to all connected clients."""
        if not self.active:
            return
        message = json.dumps(data, default=str)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_violation(self, violation: dict):
        await self.broadcast({"type": "violation", "data": violation})

    async def broadcast_stats(self, stats: dict):
        await self.broadcast({"type": "stats", "data": stats})

    async def broadcast_camera_status(self, camera_id: str, status: str):
        await self.broadcast({"type": "camera_status", "camera_id": camera_id, "status": status})

    @property
    def connection_count(self) -> int:
        return len(self.active)


# Singleton instance shared across the app
manager = ConnectionManager()
