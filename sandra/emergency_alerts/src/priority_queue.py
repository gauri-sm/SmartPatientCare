"""
Priority Alert Manager & Queue
==============================
Maintains alerts prioritized by clinical severity and operational lifecycle status.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone
import threading
import uuid

from sandra.emergency_alerts.src.models import (
    AlertItem,
    SmartPatientCareEvent,
    SeverityLevel,
    AlertStatus,
)


class PriorityAlertManager:
    """
    Thread-safe Priority Alert Manager.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # alert_id -> AlertItem
        self._alerts: Dict[str, AlertItem] = {}

    def ingest_event(
        self,
        event: SmartPatientCareEvent,
        patient_name: str,
        expected_range: str = "Normal",
    ) -> AlertItem:
        """
        Creates or updates an alert item from a SmartPatientCareEvent.
        """
        with self._lock:
            # Check if there is already an ACTIVE alert for this patient and parameter
            existing_active = None
            for alert in self._alerts.values():
                if (
                    alert.patient_id == event.patient_id
                    and alert.parameter == event.parameter
                    and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
                ):
                    existing_active = alert
                    break

            if existing_active:
                # Update existing alert
                existing_active.value = event.value
                existing_active.severity = event.severity
                existing_active.message = event.message
                existing_active.unit = event.unit
                existing_active.expected_range = expected_range
                if event.video_source:
                    existing_active.video_source = event.video_source
                if event.camera_id:
                    existing_active.camera_id = event.camera_id
                if event.evidence_type:
                    existing_active.evidence_type = event.evidence_type
                if event.extra_telemetry:
                    existing_active.extra_telemetry.update(event.extra_telemetry)
                return existing_active

            # Create fresh alert
            new_alert = AlertItem(
                alert_id=str(uuid.uuid4()),
                event_id=event.event_id,
                patient_id=event.patient_id,
                patient_name=patient_name,
                room_id=event.room_id,
                event_type=event.event_type,
                parameter=event.parameter,
                value=event.value,
                unit=event.unit,
                severity=event.severity,
                expected_range=expected_range,
                message=event.message,
                status=AlertStatus.ACTIVE,
                created_at=datetime.now(timezone.utc).isoformat(),
                video_source=event.video_source,
                camera_id=event.camera_id,
                evidence_type=event.evidence_type,
                extra_telemetry=event.extra_telemetry,
            )
            self._alerts[new_alert.alert_id] = new_alert
            return new_alert

    def get_all_alerts(
        self,
        status: Optional[AlertStatus] = None,
        patient_id: Optional[str] = None,
        severity: Optional[SeverityLevel] = None,
    ) -> List[AlertItem]:
        """
        Returns alerts ordered by:
        1. Severity: CRITICAL (1) > HIGH (2) > WARNING (3) > MEDIUM (4) > LOW (5) > INFO (6)
        2. Status: ACTIVE (1) > ACKNOWLEDGED (2) > RESOLVED (3)
        3. Created timestamp: Newest first
        """
        with self._lock:
            result = list(self._alerts.values())

        # Filtering
        if status is not None:
            result = [a for a in result if a.status == status]
        if patient_id is not None:
            result = [a for a in result if a.patient_id == patient_id]
        if severity is not None:
            result = [a for a in result if a.severity == severity]

        sev_order = {
            SeverityLevel.CRITICAL: 1,
            SeverityLevel.HIGH: 2,
            SeverityLevel.WARNING: 3,
            SeverityLevel.MEDIUM: 4,
            SeverityLevel.LOW: 5,
            SeverityLevel.INFO: 6,
        }
        status_order = {AlertStatus.ACTIVE: 1, AlertStatus.ACKNOWLEDGED: 2, AlertStatus.RESOLVED: 3}

        # Sort
        result.sort(
            key=lambda a: (
                sev_order.get(a.severity, 99),
                status_order.get(a.status, 99),
                -datetime.fromisoformat(a.created_at.replace("Z", "+00:00")).timestamp(),
            )
        )
        return result

    def get_alert(self, alert_id: str) -> Optional[AlertItem]:
        with self._lock:
            return self._alerts.get(alert_id)

    def acknowledge_alert(
        self, alert_id: str, acknowledged_by: str = "Nurse On Duty"
    ) -> Optional[AlertItem]:
        """
        Transitions alert to ACKNOWLEDGED.
        """
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert and alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
                alert.acknowledged_by = acknowledged_by
                return alert
            return alert

    def resolve_alert(
        self, alert_id: str, resolution_note: str = "Resolved by clinical staff"
    ) -> Optional[AlertItem]:
        """
        Transitions alert to RESOLVED.
        """
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                alert.resolution_note = resolution_note
                return alert
            return None

    def resolve_alerts_for_patient_parameter(self, patient_id: str, parameter: str):
        """
        Resolves any active/acknowledged alerts for a patient parameter once returned to normal.
        """
        with self._lock:
            for alert in self._alerts.values():
                if (
                    alert.patient_id == patient_id
                    and alert.parameter == parameter
                    and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]
                ):
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now(timezone.utc).isoformat()
                    alert.resolution_note = "Condition normalized automatically"

    def clear_all(self):
        with self._lock:
            self._alerts.clear()
