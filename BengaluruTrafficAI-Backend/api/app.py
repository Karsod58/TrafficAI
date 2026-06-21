"""
BengaluruTrafficAI — FastAPI Application
Component 4d: Main app with REST routes + WebSocket endpoint.

Run with:
    cd bengaluru_traffic_ai
    uvicorn api.app:app --reload --port 8000

Endpoints:
    GET  /                          health check
    GET  /violations                paginated violation list
    GET  /violations/stats          dashboard summary
    POST /violations/ingest         CV pipeline → backend
    PATCH /violations/{id}/review   officer review
    GET  /cameras                   camera list
    WS   /ws                        live violation stream
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import init_db, seed_demo_cameras
from .ws_manager import manager
from .routers import violations, cameras, analytics, upload
from .routers import health as health_router  # NEW: Traffic Health Score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BengaluruTrafficAI API...")
    init_db()
    seed_demo_cameras()
    logger.info("Database ready | Cameras seeded")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="BengaluruTrafficAI",
    description="Real-time traffic violation detection API for Bengaluru",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow React dashboard (localhost:3000) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routers
app.include_router(violations.router)
app.include_router(cameras.router)
app.include_router(analytics.router)
app.include_router(health_router.router)  # NEW: Traffic Health Score API
app.include_router(upload.router)  # NEW: Video Upload API

# Serve evidence images statically
evidence_dir = Path("output/evidence")
evidence_dir.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(evidence_dir)), name="evidence")


@app.get("/")
def health():
    return {
        "service": "BengaluruTrafficAI",
        "status":  "running",
        "ws_clients": manager.connection_count,
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Dashboard connects here to receive live violation events.
    Each new violation is pushed as JSON within ~100ms of detection.

    Message types:
        { "type": "violation",      "data": {...} }
        { "type": "stats",          "data": {...} }
        { "type": "review_update",  "data": {...} }
        { "type": "camera_status",  "camera_id": "cam_01", "status": "online" }
    """
    await manager.connect(ws)
    try:
        while True:
            # Keep connection alive; dashboard can also send pings
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(ws)
