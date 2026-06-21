"""
BengaluruTrafficAI — WebSocket Router
ws://localhost:8000/ws  — dashboard connects here for live events
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..ws_manager import ws_manager

logger = logging.getLogger("api.ws")
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Dashboard connects to this endpoint.
    On connect: receives a welcome ping.
    Stays open: receives every violation event in real time.
    """
    await ws_manager.connect(ws)
    await ws_manager.send_personal(ws, "connected", {
        "message":      "BengaluruTrafficAI live feed connected",
        "clients_online": ws_manager.client_count,
    })

    try:
        while True:
            # Keep connection alive — client can send "ping"
            data = await ws.receive_text()
            if data == "ping":
                await ws_manager.send_personal(ws, "pong", {})
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
        logger.info("Dashboard client disconnected")
