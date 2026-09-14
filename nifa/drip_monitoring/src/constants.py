"""Constants for IV Drip Monitoring and Telemetry Simulation.

All severity levels and alert statuses strictly align with shared/schemas/event_schema.json.
DEMO/SIMULATION NOTE: Values and thresholds are designed for hackathon demonstration.
"""

from enum import Enum


class SeverityLevel(str, Enum):
    """Event severity levels adhering to shared/schemas/event_schema.json."""
    INFO = "INFO"
    WARNING = "WARNING"
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
    DRIP_FLOW_RATE = "DRIP_FLOW_RATE"
    DRIP_VOLUME_LOW = "DRIP_VOLUME_LOW"
    DRIP_EMPTY = "DRIP_EMPTY"
    DRIP_OCCLUSION = "DRIP_OCCLUSION"
    DRIP_RUNAWAY = "DRIP_RUNAWAY"
    DRIP_AIR_IN_LINE = "DRIP_AIR_IN_LINE"
    DRIP_RATE_DEVIATION = "DRIP_RATE_DEVIATION"


class DropFactor(int, Enum):
    """Standard medical tubing drop factors (drops per mL / gtt per mL)."""
    MACRO_10 = 10
    MACRO_15 = 15
    MACRO_20 = 20
    MICRO_60 = 60


# Monitored Parameter Names
PARAM_DRIP_RATE = "drip_rate"
PARAM_FLOW_RATE = "flow_rate"
PARAM_REMAINING_VOLUME = "remaining_volume_ml"
PARAM_OCCLUSION_STATE = "occlusion_detected"
PARAM_AIR_IN_LINE = "air_in_line"
PARAM_DRIP_STATUS = "drip_status"

# Default Thresholds for Hackathon Demonstration
LOW_VOLUME_PERCENT_THRESHOLD = 15.0  # Alert when remaining volume <= 15%
CRITICAL_VOLUME_THRESHOLD = 0.0     # Bag completely empty
OCCLUSION_FLOW_THRESHOLD_ML_H = 1.0  # Flow dropping below 1 ml/h while uncompleted = occlusion
FLOW_DEVIATION_TOLERANCE_PCT = 20.0  # +/- 20% variation allowed before warning
RUNAWAY_FLOW_MULTIPLIER = 2.0        # > 200% prescribed rate = dangerous runaway

# Units
UNIT_ML_H = "ml/h"
UNIT_GTT_MIN = "gtt/min"
UNIT_ML = "ml"
UNIT_PERCENT = "%"
UNIT_STATUS = "status"
UNIT_BOOLEAN = "boolean"

# Telemetry Sources
SOURCE_DRIP_SENSOR = "drip_sensor"
SOURCE_DRIP_SIMULATOR = "drip_simulator"
