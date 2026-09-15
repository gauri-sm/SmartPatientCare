"""WebSocket connection manager for real-time telemetry and alerts streaming."""

import json
import logging
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections across /ws/alerts and /ws/telemetry."""

    def __init__(self):
        # General / telemetry connections
        self.active_connections: List[WebSocket] = []
        # Dedicated /ws/alerts connections
        self.alert_connections: List[WebSocket] = []
        # Room-specific client subscriptions
        self.room_subscriptions: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: Optional[str] = None):
        """Accept a telemetry WebSocket connection and register it."""
        await websocket.accept()
        self.active_connections.append(websocket)
        if room_id:
            if room_id not in self.room_subscriptions:
                self.room_subscriptions[room_id] = []
            self.room_subscriptions[room_id].append(websocket)
        logger.info("WebSocket telemetry client connected. Total telemetry: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Unregister a disconnected telemetry client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for room_id, clients in list(self.room_subscriptions.items()):
            if websocket in clients:
                clients.remove(websocket)
                if not clients:
                    del self.room_subscriptions[room_id]
        logger.info("WebSocket telemetry client disconnected. Remaining: %d", len(self.active_connections))

    async def connect_alerts(self, websocket: WebSocket):
        """Accept a dedicated alerts WebSocket connection (/ws/alerts)."""
        await websocket.accept()
        self.alert_connections.append(websocket)
        logger.info("WebSocket alerts client connected. Total alert clients: %d", len(self.alert_connections))

    def disconnect_alerts(self, websocket: WebSocket):
        """Unregister an alerts WebSocket client."""
        if websocket in self.alert_connections:
            self.alert_connections.remove(websocket)
        logger.info("WebSocket alerts client disconnected. Remaining alert clients: %d", len(self.alert_connections))

    async def broadcast_alert(self, normalized_event: dict):
        """Broadcast the normalized event directly to all /ws/alerts clients.

        Preserves optional CCTV fields (video_source, camera_id, evidence_type).
        """
        text = json.dumps(normalized_event)
        disconnected = []
        for connection in self.alert_connections:
            try:
                await connection.send_text(text)
            except Exception as e:
                logger.warning("Failed to send alert to /ws/alerts client: %s", e)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect_alerts(conn)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected telemetry clients."""
        text = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(text)
            except Exception as e:
                logger.warning("Failed to send message to client: %s", e)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_room(self, room_id: str, message: dict):
        """Broadcast a message specifically to room subscribers."""
        text = json.dumps(message)
        clients = self.room_subscriptions.get(room_id, [])
        disconnected = []
        for connection in clients:
            try:
                await connection.send_text(text)
            except Exception as e:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


# Singleton manager instance
manager = ConnectionManager()
