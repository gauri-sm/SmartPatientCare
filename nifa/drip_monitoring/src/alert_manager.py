"""Alert and In-App Notification Manager for IV Drip Monitoring.

Tracks lifecycle of alerts (ACTIVE -> ACKNOWLEDGED -> RESOLVED) and creates
standardized event dictionaries that strictly validate against shared/schemas/event_schema.json.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import json
import os

from .constants import (
    SeverityLevel,
    AlertStatus,
    SOURCE_DRIP_SENSOR,
    SOURCE_DRIP_SIMULATOR,
)


class DripAlertManager:
    """Manages alert creation, lifecycle state transitions, and notification dispatch."""

    def __init__(self, max_history: int = 200):
        self.max_history = max_history
        self._alerts: Dict[str, Dict[str, Any]] = {}  # event_id -> event dict
        self._history: List[Dict[str, Any]] = []

    @staticmethod
    def generate_iso_timestamp() -> str:
        """Return an ISO 8601 UTC timestamp conforming to event_schema.json format."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def create_event(
        self,
        event_type: str,
        patient_id: str,
        room_id: str,
        parameter: str,
        value: Any,
        unit: str,
        severity: SeverityLevel,
        message: str,
        source: str = SOURCE_DRIP_SENSOR,
        status: AlertStatus = AlertStatus.ACTIVE,
        event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct a standardized event dictionary strictly matching shared/schemas/event_schema.json."""
        if not event_id:
            event_id = f"EVT-DRIP-{uuid.uuid4().hex[:8].upper()}"

        # Ensure value type conforms to JSON Schema ["number", "string", "boolean", "null"]
        clean_value = value
        if isinstance(value, float):
            clean_value = round(value, 2)

        event = {
            "event_id": str(event_id),
            "timestamp": self.generate_iso_timestamp(),
            "event_type": str(event_type),
            "patient_id": str(patient_id),
            "room_id": str(room_id),
            "source": str(source),
            "parameter": str(parameter),
            "value": clean_value,
            "unit": str(unit),
            "severity": str(severity.value if hasattr(severity, "value") else severity),
            "message": str(message),
            "status": str(status.value if hasattr(status, "value") else status),
        }
        return event

    def register_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new event. If severity is WARNING or CRITICAL, add to active alerts."""
        event_id = event["event_id"]
        self._alerts[event_id] = event

        # Insert at the top of history
        self._history.insert(0, dict(event))
        if len(self._history) > self.max_history:
            self._history.pop()

        return event

    def acknowledge_alert(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Transition an alert status to ACKNOWLEDGED."""
        if event_id in self._alerts:
            self._alerts[event_id]["status"] = AlertStatus.ACKNOWLEDGED.value
            # Also update in history
            for item in self._history:
                if item["event_id"] == event_id:
                    item["status"] = AlertStatus.ACKNOWLEDGED.value
            return self._alerts[event_id]
        return None

    def resolve_alert(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Transition an alert status to RESOLVED and remove from active list."""
        if event_id in self._alerts:
            self._alerts[event_id]["status"] = AlertStatus.RESOLVED.value
            for item in self._history:
                if item["event_id"] == event_id:
                    item["status"] = AlertStatus.RESOLVED.value
            resolved = self._alerts.pop(event_id)
            return resolved
        return None

    def get_active_alerts(
        self, patient_id: Optional[str] = None, severity: Optional[SeverityLevel] = None
    ) -> List[Dict[str, Any]]:
        """Get list of active or acknowledged alerts, optionally filtered by patient or severity."""
        results = []
        for alert in self._alerts.values():
            if alert["status"] in (AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value):
                if patient_id and alert["patient_id"] != patient_id:
                    continue
                if severity and alert["severity"] != (severity.value if hasattr(severity, "value") else severity):
                    continue
                results.append(alert)
        # Sort so CRITICAL is first, then WARNING, then by timestamp descending
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        results.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["timestamp"]), reverse=False)
        return results

    def get_alert_history(
        self, patient_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve recent alert history."""
        if patient_id:
            filtered = [evt for evt in self._history if evt["patient_id"] == patient_id]
            return filtered[:limit]
        return self._history[:limit]

    def has_active_alert_of_type(self, patient_id: str, event_type: str) -> bool:
        """Deduplication helper: Check if an alert of this type is already active for patient."""
        for alert in self._alerts.values():
            if (
                alert["patient_id"] == patient_id
                and alert["event_type"] == event_type
                and alert["status"] in (AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value)
            ):
                return True
        return False

    def clear_all(self):
        """Reset all active alerts and history."""
        self._alerts.clear()
        self._history.clear()
