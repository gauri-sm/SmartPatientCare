"""Constants for IV Drip Monitoring and Telemetry Simulation.

All severity levels and alert statuses align with shared/schemas/event_schema.json.
Configurable via environment variables for multi-laptop hackathon deployment.
"""

import os
from enum import Enum


class SeverityLevel(str, Enum):
    """Event severity levels."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    """Event lifecycle statuses adhering to shared/schemas/event_schema.json."""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertCategory(str, Enum):
    """Indicates whether an alert is equipment-related, patient-related, or both."""
    EQUIPMENT_ALERT = "EQUIPMENT ALERT"
    PATIENT_ALERT = "PATIENT ALERT"
    PATIENT_AND_EQUIPMENT_ALERT = "PATIENT & EQUIPMENT ALERT"


class DripEventType(str, Enum):
    """Standardized event types for IV drip telemetry."""
    DRIP_LOW = "DRIP_LOW"
    DRIP_FINISHED = "DRIP_FINISHED"
    DRIP_NORMAL = "DRIP_NORMAL"
    DRIP_FLOW_RATE = "DRIP_FLOW_RATE"
    DRIP_VOLUME_LOW = "DRIP_VOLUME_LOW"
    DRIP_EMPTY = "DRIP_EMPTY"
    DRIP_OCCLUSION = "DRIP_OCCLUSION"
    DRIP_RUNAWAY = "DRIP_RUNAWAY"
    DRIP_AIR_IN_LINE = "DRIP_AIR_IN_LINE"
    DRIP_RATE_DEVIATION = "DRIP_RATE_DEVIATION"


class DripStatus(str, Enum):
    """IV Drip clinical dashboard status values."""
    NORMAL = "NORMAL"
    LOW = "LOW"
    FINISHED = "FINISHED"


class DropFactor(int, Enum):
    """Standard medical tubing drop factors (drops per mL / gtt per mL)."""
    MACRO_10 = 10
    MACRO_15 = 15
    MACRO_20 = 20
    MICRO_60 = 60


# Standard Source Name (As specified for centralized alert engine integration)
SOURCE_DRIP_MONITOR = "DRIP_MONITOR"
SOURCE_DRIP_SENSOR = "drip_sensor"
SOURCE_DRIP_SIMULATOR = "drip_simulator"

# Monitored Parameter Names
PARAM_DRIP_STATUS = "drip_status"
PARAM_REMAINING_VOLUME_PCT = "remaining_volume_pct"
PARAM_REMAINING_VOLUME = "remaining_volume_ml"
PARAM_FLOW_RATE = "flow_rate"
PARAM_OCCLUSION_STATE = "occlusion_detected"
PARAM_AIR_IN_LINE = "air_in_line"

# Units
UNIT_STATUS = "status"
UNIT_PERCENT = "%"
UNIT_ML = "ml"
UNIT_ML_H = "ml/h"
UNIT_GTT_MIN = "gtt/min"
UNIT_BOOLEAN = "boolean"

# Configurable defaults (via environment variables)
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEFAULT_LOW_THRESHOLD_PCT = float(os.getenv("DRIP_LOW_THRESHOLD_PCT", "15.0"))
DEFAULT_LOW_SEVERITY = os.getenv("DRIP_LOW_SEVERITY", "HIGH")
DEFAULT_FINISHED_SEVERITY = os.getenv("DRIP_FINISHED_SEVERITY", "HIGH")
DEFAULT_COOLDOWN_SECONDS = float(os.getenv("DRIP_COOLDOWN_SECONDS", "30.0"))

# Legacy constants for compatibility
LOW_VOLUME_PERCENT_THRESHOLD = DEFAULT_LOW_THRESHOLD_PCT
CRITICAL_VOLUME_THRESHOLD = 0.0
OCCLUSION_FLOW_THRESHOLD_ML_H = 1.0
FLOW_DEVIATION_TOLERANCE_PCT = 20.0
RUNAWAY_FLOW_MULTIPLIER = 2.0
