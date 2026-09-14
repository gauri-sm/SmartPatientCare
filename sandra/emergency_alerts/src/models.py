"""
Data Models for SmartPatientCare Alerts and Telemetry
=====================================================
Strictly complies with shared/schemas/event_schema.json.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Union, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    WARNING = "WARNING"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class EventType(str, Enum):
    # Core Vitals
    VITAL_SIGN = "VITAL_SIGN"
    LOW_SPO2 = "LOW_SPO2"
    ABNORMAL_HEART_RATE = "ABNORMAL_HEART_RATE"
    ABNORMAL_BP = "ABNORMAL_BP"
    ABNORMAL_TEMPERATURE = "ABNORMAL_TEMPERATURE"
    
    # Computer Vision / CCTV
    FALL_DETECTED = "FALL_DETECTED"
    PATIENT_LEFT_BED = "PATIENT_LEFT_BED"
    ABNORMAL_MOVEMENT = "ABNORMAL_MOVEMENT"
    UNUSUAL_POSITION = "UNUSUAL_POSITION"

    # Bedside Medical Devices
    ABNORMAL_ECG = "ABNORMAL_ECG"
    ECG_ABNORMAL = "ECG_ABNORMAL"
    VENTILATOR_ALERT = "VENTILATOR_ALERT"
    VENTILATOR_RECOMMENDATION = "VENTILATOR_RECOMMENDATION"
    DRIP_ALERT = "DRIP_ALERT"
    DRIP_LOW = "DRIP_LOW"
    DRIP_FINISHED = "DRIP_FINISHED"

    # Emergency Call & System
    EMERGENCY = "EMERGENCY"
    EMERGENCY_TRIGGER = "EMERGENCY_TRIGGER"
    SYSTEM = "SYSTEM"


class SmartPatientCareEvent(BaseModel):
    """
    Standardized event format adhering to shared/schemas/event_schema.json,
    with optional CCTV/evidence fields and safe capture of teammate telemetry extensions.
    """
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the event")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of the event"
    )
    event_type: str = Field(..., min_length=1, description="Category or type of event")
    patient_id: str = Field(..., min_length=1, description="Patient identifier (e.g., P001)")
    room_id: str = Field(..., min_length=1, description="Room identifier (e.g., ROOM101)")
    source: str = Field(..., min_length=1, description="Originating source of the event")
    parameter: str = Field(default="status", description="Specific monitored parameter")
    value: Optional[Union[float, int, str, bool]] = Field(None, description="Current reading or parameter value")
    unit: str = Field(default="status", description="Measurement unit")
    severity: SeverityLevel = Field(..., description="Severity level of the event")
    message: str = Field(..., min_length=1, description="Human-readable summary or message")
    status: AlertStatus = Field(default=AlertStatus.ACTIVE, description="Lifecycle status")

    # Optional CCTV / Computer Vision Evidence Fields
    video_source: Optional[str] = Field(None, description="Path or URL to video evidence clip")
    camera_id: Optional[str] = Field(None, description="Identifier of originating CCTV camera")
    evidence_type: Optional[str] = Field(None, description="Type of visual evidence (e.g. CCTV_DEMO_VIDEO)")
    extra_telemetry: Dict[str, Any] = Field(default_factory=dict, description="Safe storage for additional teammate telemetry")


class AlertItem(BaseModel):
    """
    Dashboard alert representation with extra UI convenience fields.
    """
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    patient_id: str
    patient_name: str
    room_id: str
    event_type: str
    parameter: str
    value: Optional[Union[float, int, str, bool]] = None
    unit: str
    severity: SeverityLevel
    expected_range: str
    message: str
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_note: Optional[str] = None

    # Optional CCTV / Computer Vision Evidence Fields preserved in dashboard alert
    video_source: Optional[str] = None
    camera_id: Optional[str] = None
    evidence_type: Optional[str] = None
    extra_telemetry: Dict[str, Any] = Field(default_factory=dict)


class VitalSigns(BaseModel):
    heart_rate: Optional[float] = None
    blood_pressure: Optional[str] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[float] = None
    temperature: Optional[float] = None
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IVDripState(BaseModel):
    volume_remaining_ml: float = 500.0
    flow_rate_ml_h: float = 100.0
    status: str = "NORMAL"  # NORMAL, LOW, EMPTY, OCCLUDED
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ECGState(BaseModel):
    rhythm: str = "NORMAL_SINUS_RHYTHM"
    status: str = "NORMAL"  # NORMAL, WARNING, CRITICAL
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PatientRecord(BaseModel):
    patient_id: str
    room_id: str
    name: str
    age: int
    gender: str
    admission_date: str
    condition: str
    status: str  # Stable, Observation, Critical
    assigned_doctor: str
    assigned_nurse: str
    devices_connected: List[str]
    vitals: VitalSigns
    iv_drip: IVDripState
    ecg: ECGState
    active_alerts: List[AlertItem] = []
