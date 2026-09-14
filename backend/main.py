"""
SmartPatientCare Central Backend Service
=======================================
FastAPI service orchestrating patient monitoring, real-time WebSocket telemetry,
Sandra's emergency alert engine, and serving the nursing station frontend dashboard.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List
import json
import logging

from backend.api.routes import router, patient_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartpatientcare.backend")

app = FastAPI(
    title="SmartPatientCare Central Monitoring Service",
    description="Hospital patient telemetry, vital sign alerting, IV drip monitoring, and emergency response.",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# WebSocket Connection Manager for real-time dashboard updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to WebSocket: {e}")
                self.disconnect(connection)


ws_manager = ConnectionManager()


@app.websocket("/ws")
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    # Send initial snapshot immediately upon connect
    try:
        initial_data = {
            "type": "SNAPSHOT",
            "stats": patient_service.get_station_stats(),
            "patients": patient_service.get_all_patients(),
            "alerts": patient_service.get_alerts(),
        }
        await websocket.send_json(initial_data)

        while True:
            # Keep receiving pings or client triggers
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "PING":
                    await websocket.send_json({"type": "PONG"})
                elif msg.get("action") == "REFRESH":
                    snapshot = {
                        "type": "SNAPSHOT",
                        "stats": patient_service.get_station_stats(),
                        "patients": patient_service.get_all_patients(),
                        "alerts": patient_service.get_alerts(),
                    }
                    await websocket.send_json(snapshot)
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# Mount frontend/dashboard static files
dashboard_dir = Path(__file__).resolve().parent.parent / "frontend" / "dashboard"
if dashboard_dir.exists():
    app.mount("/", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")
