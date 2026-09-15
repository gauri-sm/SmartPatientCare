"""Event ingestion, persistence, and broadcasting service."""

from datetime import datetime, timezone
import json
import logging
from typing import Dict, List, Optional
import uuid
from sqlalchemy.orm import Session

from backend.models.db_models import EventDB, VitalsReadingDB
from backend.models.schemas import SmartPatientCareEvent, EventCreate
from backend.services.connection_manager import manager

logger = logging.getLogger(__name__)

# In-memory latest vitals cache: patient_id -> {parameter: {value, unit, timestamp}}
latest_vitals_cache: Dict[str, Dict[str, dict]] = {}


class EventService:
    """Service handling telemetry event ingestion and query operations."""

    @staticmethod
    async def ingest_event(db: Session, event_data: EventCreate) -> SmartPatientCareEvent:
        """Validate, persist, cache, and broadcast an incoming event.

        Accepts events from:
        - CCTV / YOLO (with optional video_source, camera_id, evidence_type)
        - Medical device simulator
        - IV / Drip simulator
        - Emergency simulator
        """
        # Convert to dictionary and fill missing fields
        event_dict = event_data.model_dump(exclude_unset=False)

        # Ensure event_id and timestamp defaults if not provided
        if not event_dict.get("event_id"):
            event_dict["event_id"] = f"EVT-{uuid.uuid4().hex[:8].upper()}"
        if not event_dict.get("timestamp"):
            event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Ensure parameter and unit defaults if not supplied
        if not event_dict.get("parameter"):
            event_dict["parameter"] = event_dict.get("event_type", "event").lower()
        if event_dict.get("unit") is None:
            event_dict["unit"] = "status"

        event = SmartPatientCareEvent(**event_dict)

        # Value serialization
        val_str = (
            json.dumps(event.value)
            if not isinstance(event.value, (str, int, float, bool)) and event.value is not None
            else str(event.value) if event.value is not None else None
        )

        db_event = EventDB(
            event_id=event.event_id,
            timestamp=event.timestamp,
            event_type=event.event_type,
            patient_id=event.patient_id,
            room_id=event.room_id,
            source=event.source,
            parameter=event.parameter,
            value_text=val_str,
            unit=event.unit,
            severity=event.severity,
            message=event.message,
            status=event.status,
            video_source=event.video_source,
            camera_id=event.camera_id,
            evidence_type=event.evidence_type,
        )
        db.add(db_event)

        # Update latest vitals cache if it's a vital reading
        patient_id = event.patient_id
        if event.parameter:
            if patient_id not in latest_vitals_cache:
                latest_vitals_cache[patient_id] = {}

            latest_vitals_cache[patient_id][event.parameter] = {
                "value": event.value,
                "unit": event.unit,
                "timestamp": event.timestamp,
                "severity": event.severity,
                "event_type": event.event_type,
            }

        # If it's a vital sign reading, append to vitals timeseries history
        vitals_parameters = ("heart_rate", "spo2", "blood_pressure", "respiratory_rate", "temperature")
        if event.parameter in vitals_parameters or event.event_type in (
            "VITAL_SIGN", "VITALS_READING", "LOW_SPO2", "ABNORMAL_HEART_RATE", "ABNORMAL_BP", "ABNORMAL_TEMPERATURE"
        ):
            reading = VitalsReadingDB(
                timestamp=event.timestamp,
                patient_id=patient_id,
            )
            if event.parameter == "heart_rate" and isinstance(event.value, (int, float)):
                reading.heart_rate = float(event.value)
            elif event.parameter == "spo2" and isinstance(event.value, (int, float)):
                reading.spo2 = float(event.value)
            elif event.parameter == "blood_pressure":
                reading.blood_pressure = str(event.value)
            elif event.parameter == "respiratory_rate" and isinstance(event.value, (int, float)):
                reading.respiratory_rate = float(event.value)
            elif event.parameter == "temperature" and isinstance(event.value, (int, float)):
                reading.temperature = float(event.value)

            db.add(reading)

        db.commit()
        db.refresh(db_event)

        normalized_dict = db_event.to_dict()

        # 1. Broadcast normalized event through /ws/alerts (preserving optional CCTV fields)
        await manager.broadcast_alert(normalized_dict)

        # 2. Also broadcast through /ws/telemetry
        await manager.broadcast({
            "type": "NEW_EVENT",
            "data": normalized_dict
        })

        return event

    @staticmethod
    def get_events(
        db: Session,
        patient_id: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """Query events with optional filters."""
        query = db.query(EventDB)
        if patient_id:
            query = query.filter(EventDB.patient_id == patient_id)
        if severity:
            query = query.filter(EventDB.severity == severity.upper())
        if status:
            query = query.filter(EventDB.status == status.upper())
        if event_type:
            query = query.filter(EventDB.event_type == event_type.upper())

        events = query.order_by(EventDB.timestamp.desc()).limit(limit).all()
        return [e.to_dict() for e in events]

    @staticmethod
    def get_active_events(db: Session, limit: int = 100) -> List[dict]:
        """Retrieve all currently active events and alerts."""
        events = (
            db.query(EventDB)
            .filter(EventDB.status == "ACTIVE")
            .order_by(EventDB.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [e.to_dict() for e in events]

    @staticmethod
    async def update_event_status(
        db: Session,
        event_id: str,
        new_status: str
    ) -> Optional[dict]:
        """Update event status (e.g. ACTIVE -> ACKNOWLEDGED / RESOLVED) and broadcast change."""
        event = db.query(EventDB).filter(EventDB.event_id == event_id).first()
        if not event:
            return None

        event.status = new_status.upper()
        db.commit()
        db.refresh(event)

        updated_dict = event.to_dict()

        # Broadcast status update on both /ws/alerts and /ws/telemetry
        await manager.broadcast_alert(updated_dict)
        await manager.broadcast({
            "type": "EVENT_STATUS_UPDATED",
            "data": updated_dict
        })

        return updated_dict

    @staticmethod
    async def acknowledge_event(db: Session, event_id: str) -> Optional[dict]:
        """Convenience method to acknowledge an alert."""
        return await EventService.update_event_status(db, event_id, "ACKNOWLEDGED")

    @staticmethod
    async def resolve_event(db: Session, event_id: str) -> Optional[dict]:
        """Convenience method to resolve an alert."""
        return await EventService.update_event_status(db, event_id, "RESOLVED")

    @staticmethod
    def get_latest_vitals(patient_id: str) -> dict:
        """Retrieve the in-memory latest vitals cache for a patient."""
        return latest_vitals_cache.get(patient_id, {})
