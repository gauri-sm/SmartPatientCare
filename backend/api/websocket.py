"""WebSocket routes for streaming real-time alerts and telemetry to dashboards."""

import logging
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.services.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Stream"])


@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """Centralized alerts WebSocket stream.

    Broadcasts normalized events (including CCTV events with video_source, camera_id, evidence_type)
    to the alert engine, nursing station UI, and other listeners.
    """
    await manager.connect_alerts(websocket)
    try:
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Subscribed to SmartPatientCare /ws/alerts stream"
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_alerts(websocket)
    except Exception as e:
        logger.warning("Alerts WebSocket error: %s", e)
        manager.disconnect_alerts(websocket)


@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(
    websocket: WebSocket,
    room_id: Optional[str] = Query(None, description="Optional room subscription filter")
):
    """Real-time streaming endpoint for Nursing Station dashboard and monitoring clients."""
    await manager.connect(websocket, room_id=room_id)
    try:
        # Send initial welcome / handshake
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to SmartPatientCare Realtime Stream",
            "room_filter": room_id
        })

        while True:
            # Keep connection open and accept incoming client pings or control messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning("Telemetry WebSocket error: %s", e)
        manager.disconnect(websocket)
