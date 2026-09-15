"""Pydantic schemas for SmartPatientCare system.

These schemas strictly adhere to the contract in shared/schemas/event_schema.json
and patient mock data in shared/mock_data/patients.json.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
import uuid
from pydantic import BaseModel, Field, model_validator


class BaselineVitals(BaseModel):
    """Patient baseline vitals structure."""
    heart_rate: int = Field(..., description="Baseline heart rate in bpm")
    blood_pressure: str = Field(..., description="Baseline blood pressure (e.g., '120/80')")
    spo2: int = Field(..., description="Baseline blood oxygen saturation in %")
    respiratory_rate: int = Field(..., description="Baseline respiratory rate in breaths/min")
    temperature: float = Field(..., description="Baseline body temperature in Celsius")


class PatientBase(BaseModel):
    """Patient base model matching shared mock data schema."""
    patient_id: str
    room_id: str
    name: str
    age: int
    gender: str
    admission_date: str
    condition: str
    status: str
    assigned_doctor: str
    assigned_nurse: str
    devices_connected: List[str]
    baseline_vitals: BaselineVitals


class PatientResponse(PatientBase):
    """API response model for patient information."""
    model_config = {"from_attributes": True}


class SmartPatientCareEvent(BaseModel):
    """Standardized event telemetry payload conforming to shared/schemas/event_schema.json."""
    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def populate_defaults_if_missing(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Auto-generate event_id if not provided or None
            if not data.get("event_id"):
                data["event_id"] = f"EVT-{uuid.uuid4().hex[:8].upper()}"
            # Auto-generate timestamp if not provided or None
            if not data.get("timestamp"):
                data["timestamp"] = datetime.now(timezone.utc).isoformat()
            # Default parameter to event_type.lower() if not provided
            if not data.get("parameter") and data.get("event_type"):
                data["parameter"] = str(data["event_type"]).lower()
            # Default unit to "status" if not provided
            if data.get("unit") is None:
                data["unit"] = "status"
            # Default status to "ACTIVE" if not provided
            if not data.get("status"):
                data["status"] = "ACTIVE"
        return data

    event_id: str = Field(
        default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}",
        description="Unique identifier for the event"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of the event"
    )
    event_type: str = Field(
        ...,
        description="Category or type of event (e.g., VITAL_SIGN, LOW_SPO2, ABNORMAL_ECG, ABNORMAL_HEART_RATE, ABNORMAL_BP, ABNORMAL_TEMPERATURE, FALL_DETECTED)"
    )
    patient_id: str = Field(..., description="Patient identifier (e.g., P001)")
    room_id: str = Field(..., description="Room identifier (e.g., ROOM101)")
    source: str = Field(
        ...,
        description="Originating source (e.g., CCTV, device_simulator, drip_sensor, ventilator_monitor)"
    )
    parameter: Optional[str] = Field(
        None,
        description="Specific monitored parameter (e.g., heart_rate, spo2, drip_rate, fall_state)"
    )
    value: Optional[Union[float, int, str, bool]] = Field(
        None,
        description="Current reading or parameter value"
    )
    unit: Optional[str] = Field(
        None,
        description="Measurement unit (e.g., bpm, %, ml/h, status)"
    )
    severity: Literal["INFO", "LOW", "MEDIUM", "WARNING", "HIGH", "CRITICAL"] = Field(
        ...,
        description="Severity level of the event"
    )
    message: str = Field(
        ...,
        description="Human-readable summary or message describing the event"
    )
    status: Literal["ACTIVE", "ACKNOWLEDGED", "RESOLVED"] = Field(
        default="ACTIVE",
        description="Current lifecycle status of the event or alert"
    )
    # Optional CCTV fields (strictly optional)
    video_source: Optional[str] = Field(None, description="Optional CCTV video file path or stream URI")
    camera_id: Optional[str] = Field(None, description="Optional CCTV camera identifier")
    evidence_type: Optional[str] = Field(None, description="Optional CCTV evidence classification")


class EventCreate(BaseModel):
    """Input model for ingesting events; accepts device, drip, emergency, and CCTV events."""
    model_config = {"extra": "allow"}

    event_id: Optional[str] = None
    timestamp: Optional[str] = None
    event_type: str
    patient_id: str
    room_id: str
    source: str
    parameter: Optional[str] = None
    value: Optional[Union[float, int, str, bool]] = None
    unit: Optional[str] = None
    severity: Literal["INFO", "LOW", "MEDIUM", "WARNING", "HIGH", "CRITICAL"]
    message: str
    status: Literal["ACTIVE", "ACKNOWLEDGED", "RESOLVED"] = "ACTIVE"
    video_source: Optional[str] = None
    camera_id: Optional[str] = None
    evidence_type: Optional[str] = None



class EventStatusUpdate(BaseModel):
    """Payload to update an alert/event status."""
    status: Literal["ACTIVE", "ACKNOWLEDGED", "RESOLVED"]


class VitalsSnapshot(BaseModel):
    """Current vital signs snapshot for a patient."""
    patient_id: str
    timestamp: str
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    blood_pressure: Optional[str] = None
    respiratory_rate: Optional[float] = None
    temperature: Optional[float] = None


class ECGPoint(BaseModel):
    """Single ECG waveform time-voltage point."""
    t: float = Field(..., description="Time offset in seconds")
    mv: float = Field(..., description="Voltage in millivolts")


class ECGWaveformResponse(BaseModel):
    """Response model for simulated ECG waveform lead data."""
    patient_id: str = Field(..., description="Patient identifier")
    heart_rate: float = Field(..., description="Current or baseline heart rate in bpm")
    rhythm: str = Field(..., description="ECG rhythm classification")
    sampling_rate: int = Field(..., description="Sampling rate in Hz")
    duration_seconds: float = Field(..., description="Duration of waveform in seconds")
    points: List[ECGPoint] = Field(..., description="List of time-voltage points")

