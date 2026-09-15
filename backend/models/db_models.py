"""SQLAlchemy ORM models for patients, events/alerts, and vitals history."""

import json
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from backend.database.database import Base


class PatientDB(Base):
    """Database model for admitted patients."""
    __tablename__ = "patients"

    patient_id = Column(String(32), primary_key=True, index=True)
    room_id = Column(String(32), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(32), nullable=False)
    admission_date = Column(String(64), nullable=False)
    condition = Column(String(256), nullable=False)
    status = Column(String(64), nullable=False)
    assigned_doctor = Column(String(128), nullable=False)
    assigned_nurse = Column(String(128), nullable=False)
    _devices_connected = Column("devices_connected", Text, nullable=False)
    _baseline_vitals = Column("baseline_vitals", Text, nullable=False)

    @property
    def devices_connected(self):
        """Deserialize devices list from JSON text."""
        return json.loads(self._devices_connected) if self._devices_connected else []

    @devices_connected.setter
    def devices_connected(self, value):
        self._devices_connected = json.dumps(value)

    @property
    def baseline_vitals(self):
        """Deserialize baseline vitals dict from JSON text."""
        return json.loads(self._baseline_vitals) if self._baseline_vitals else {}

    @baseline_vitals.setter
    def baseline_vitals(self, value):
        self._baseline_vitals = json.dumps(value)

    def to_dict(self):
        """Convert model instance to dictionary representation."""
        return {
            "patient_id": self.patient_id,
            "room_id": self.room_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "admission_date": self.admission_date,
            "condition": self.condition,
            "status": self.status,
            "assigned_doctor": self.assigned_doctor,
            "assigned_nurse": self.assigned_nurse,
            "devices_connected": self.devices_connected,
            "baseline_vitals": self.baseline_vitals,
        }


class EventDB(Base):
    """Database model for all ingested telemetry events and emergency alerts."""
    __tablename__ = "events"

    event_id = Column(String(64), primary_key=True, index=True)
    timestamp = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    patient_id = Column(String(32), nullable=False, index=True)
    room_id = Column(String(32), nullable=False, index=True)
    source = Column(String(64), nullable=False)
    parameter = Column(String(64), nullable=True)
    value_text = Column(String(256), nullable=True)  # JSON-encoded or raw string
    unit = Column(String(32), nullable=True)
    severity = Column(String(32), nullable=False, index=True)  # INFO, WARNING, CRITICAL, etc.
    message = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="ACTIVE", index=True)  # ACTIVE, ACKNOWLEDGED, RESOLVED

    # Optional CCTV fields
    video_source = Column(String(256), nullable=True)
    camera_id = Column(String(64), nullable=True)
    evidence_type = Column(String(64), nullable=True)

    def to_dict(self):
        """Convert event ORM record to dict matching event_schema.json and preserving CCTV fields."""
        raw_val = self.value_text
        # Parse value type
        parsed_val = None
        if raw_val is not None:
            try:
                parsed_val = json.loads(raw_val)
            except Exception:
                parsed_val = raw_val

        data = {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "patient_id": self.patient_id,
            "room_id": self.room_id,
            "source": self.source,
            "parameter": self.parameter,
            "value": parsed_val,
            "unit": self.unit,
            "severity": self.severity,
            "message": self.message,
            "status": self.status,
        }
        if self.video_source is not None:
            data["video_source"] = self.video_source
        if self.camera_id is not None:
            data["camera_id"] = self.camera_id
        if self.evidence_type is not None:
            data["evidence_type"] = self.evidence_type

        return data


class VitalsReadingDB(Base):
    """Timeseries history of patient vital sign readings."""
    __tablename__ = "vitals_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String(64), nullable=False, index=True)
    patient_id = Column(String(32), nullable=False, index=True)
    heart_rate = Column(Float, nullable=True)
    spo2 = Column(Float, nullable=True)
    blood_pressure = Column(String(32), nullable=True)
    respiratory_rate = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "patient_id": self.patient_id,
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "blood_pressure": self.blood_pressure,
            "respiratory_rate": self.respiratory_rate,
            "temperature": self.temperature,
        }
