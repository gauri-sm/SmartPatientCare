"""Anomaly detection and state-transition monitoring algorithms for IV drip systems.

Supports the central SmartPatientCare alert sequence:
NORMAL DRIP -> DRIP LOW -> DRIP FINISHED

Features:
- State machine tracking: NORMAL, LOW, FINISHED
- Configurable low threshold percentage (e.g. 15% or 10%)
- Configurable severity (e.g. HIGH)
- Strict duplicate event prevention via state transition gating and cooldown
- Telemetry format conforming strictly to shared event schema with source="DRIP_MONITOR"
- Zero CCTV / video dependencies
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .constants import (
    SeverityLevel,
    AlertStatus,
    AlertCategory,
    DripEventType,
    DripStatus,
    SOURCE_DRIP_MONITOR,
    PARAM_DRIP_STATUS,
    PARAM_REMAINING_VOLUME_PCT,
    PARAM_REMAINING_VOLUME,
    PARAM_FLOW_RATE,
    PARAM_OCCLUSION_STATE,
    PARAM_AIR_IN_LINE,
    UNIT_STATUS,
    UNIT_PERCENT,
    UNIT_ML,
    UNIT_ML_H,
    UNIT_BOOLEAN,
    DEFAULT_LOW_THRESHOLD_PCT,
    DEFAULT_LOW_SEVERITY,
    DEFAULT_FINISHED_SEVERITY,
    DEFAULT_COOLDOWN_SECONDS,
    LOW_VOLUME_PERCENT_THRESHOLD,
    CRITICAL_VOLUME_THRESHOLD,
    OCCLUSION_FLOW_THRESHOLD_ML_H,
    FLOW_DEVIATION_TOLERANCE_PCT,
    RUNAWAY_FLOW_MULTIPLIER,
)


def generate_iso_timestamp() -> str:
    """Generate ISO 8601 UTC timestamp format conforming to event_schema.json."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DripStateMonitor:
    """Monitors IV drip percentage level transitions and generates state-gated events.

    Guarantees no duplicate event spam while transitioning:
    NORMAL -> DRIP_LOW -> DRIP_FINISHED
    """

    def __init__(
        self,
        patient_id: str = "P001",
        room_id: str = "ROOM101",
        low_threshold_pct: float = DEFAULT_LOW_THRESHOLD_PCT,
        low_severity: str = DEFAULT_LOW_SEVERITY,
        finished_severity: str = DEFAULT_FINISHED_SEVERITY,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        source: str = SOURCE_DRIP_MONITOR,
    ):
        self.patient_id = patient_id
        self.room_id = room_id
        self.low_threshold_pct = low_threshold_pct
        self.low_severity = low_severity
        self.finished_severity = finished_severity
        self.cooldown_seconds = cooldown_seconds
        self.source = source

        self.current_state: DripStatus = DripStatus.NORMAL
        self.last_event_time: float = 0.0
        self.last_emitted_event_type: Optional[str] = None

    def process_level_pct(self, level_pct: float) -> Optional[Dict[str, Any]]:
        """Evaluate current fluid percentage and return an event only on state transition.

        Returns None if no state change occurred (duplicate suppression).
        """
        now = time.time()

        # 1. Check for FINISHED (0% remaining)
        if level_pct <= 0.0:
            if self.current_state != DripStatus.FINISHED:
                self.current_state = DripStatus.FINISHED
                self.last_event_time = now
                self.last_emitted_event_type = DripEventType.DRIP_FINISHED.value
                return self._build_event(
                    event_type=DripEventType.DRIP_FINISHED.value,
                    status_value=DripStatus.FINISHED.value,
                    severity=self.finished_severity,
                    message=f"IV drip FINISHED (0% remaining) for patient {self.patient_id}. Infusion completed.",
                )
            return None  # Suppress duplicate FINISHED events

        # 2. Check for LOW (crossed low threshold)
        elif level_pct <= self.low_threshold_pct:
            if self.current_state != DripStatus.LOW and self.current_state != DripStatus.FINISHED:
                self.current_state = DripStatus.LOW
                self.last_event_time = now
                self.last_emitted_event_type = DripEventType.DRIP_LOW.value
                return self._build_event(
                    event_type=DripEventType.DRIP_LOW.value,
                    status_value=DripStatus.LOW.value,
                    severity=self.low_severity,
                    message=(
                        f"IV drip level LOW ({level_pct:.0f}% remaining, threshold <= {self.low_threshold_pct:.0f}%) "
                        f"for patient {self.patient_id}. Prepare replacement bag."
                    ),
                )
            return None  # Suppress duplicate LOW events (e.g. 10% -> 5%)

        # 3. NORMAL level (> low threshold)
        else:
            if self.current_state != DripStatus.NORMAL:
                # Bag was refilled or reset
                self.current_state = DripStatus.NORMAL
                self.last_emitted_event_type = None
            return None  # Normal level produces no alert event

    def _build_event(
        self, event_type: str, status_value: str, severity: str, message: str
    ) -> Dict[str, Any]:
        """Build standard event dictionary matching shared/schemas/event_schema.json."""
        event_id = f"EVT-DRIP-{uuid.uuid4().hex[:8].upper()}"
        return {
            "event_id": event_id,
            "timestamp": generate_iso_timestamp(),
            "event_type": event_type,
            "patient_id": self.patient_id,
            "room_id": self.room_id,
            "source": self.source,
            "parameter": PARAM_DRIP_STATUS,
            "value": status_value,
            "unit": UNIT_STATUS,
            "severity": severity,
            "message": message,
            "status": AlertStatus.ACTIVE.value,
        }

    def reset(self):
        """Reset state monitor to NORMAL state (e.g. on new bag hang)."""
        self.current_state = DripStatus.NORMAL
        self.last_event_time = 0.0
        self.last_emitted_event_type = None


@dataclass
class AnomalyDetectionResult:
    """Standard container for an anomaly detection outcome."""
    is_anomaly: bool
    event_type: DripEventType
    severity: SeverityLevel
    category: AlertCategory
    parameter: str
    value: Any
    unit: str
    message: str
    suggested_action: str


class DripAnomalyDetector:
    """Evaluates telemetry snapshots and continuous drip flow to detect anomalies."""

    def __init__(
        self,
        low_volume_pct: float = LOW_VOLUME_PERCENT_THRESHOLD,
        occlusion_flow_limit: float = OCCLUSION_FLOW_THRESHOLD_ML_H,
        flow_deviation_pct: float = FLOW_DEVIATION_TOLERANCE_PCT,
        runaway_multiplier: float = RUNAWAY_FLOW_MULTIPLIER,
    ):
        self.low_volume_pct = low_volume_pct
        self.occlusion_flow_limit = occlusion_flow_limit
        self.flow_deviation_pct = flow_deviation_pct
        self.runaway_multiplier = runaway_multiplier

    def evaluate(
        self,
        remaining_volume_ml: float,
        total_volume_ml: float,
        current_flow_rate_ml_h: float,
        prescribed_rate_ml_h: float,
        air_in_line_detected: bool = False,
        clamp_closed: bool = False,
    ) -> List[AnomalyDetectionResult]:
        """Evaluate an IV drip status snapshot and return any detected anomalies."""
        results: List[AnomalyDetectionResult] = []

        # 1. CRITICAL: Air-in-line detected (High embolus risk - Equipment Alert)
        if air_in_line_detected:
            results.append(
                AnomalyDetectionResult(
                    is_anomaly=True,
                    event_type=DripEventType.DRIP_AIR_IN_LINE,
                    severity=SeverityLevel.CRITICAL,
                    category=AlertCategory.EQUIPMENT_ALERT,
                    parameter=PARAM_AIR_IN_LINE,
                    value=True,
                    unit=UNIT_BOOLEAN,
                    message="CRITICAL EQUIPMENT ALERT: Air bubble detected in IV infusion line.",
                    suggested_action="Clamp line immediately and prime chamber to purge air.",
                )
            )

        # 2. CRITICAL: Bag completely empty / IV Completed
        if remaining_volume_ml <= CRITICAL_VOLUME_THRESHOLD:
            results.append(
                AnomalyDetectionResult(
                    is_anomaly=True,
                    event_type=DripEventType.DRIP_FINISHED,
                    severity=SeverityLevel.HIGH,
                    category=AlertCategory.PATIENT_AND_EQUIPMENT_ALERT,
                    parameter=PARAM_DRIP_STATUS,
                    value=DripStatus.FINISHED.value,
                    unit=UNIT_STATUS,
                    message="CRITICAL: IV bag empty. Infusion cycle completed.",
                    suggested_action="Replace IV container or flush line and discontinue infusion.",
                )
            )
            return results

        # 3. CRITICAL: Occlusion / Line Blockage
        if (current_flow_rate_ml_h <= self.occlusion_flow_limit or clamp_closed) and remaining_volume_ml > 5.0:
            results.append(
                AnomalyDetectionResult(
                    is_anomaly=True,
                    event_type=DripEventType.DRIP_OCCLUSION,
                    severity=SeverityLevel.CRITICAL,
                    category=AlertCategory.EQUIPMENT_ALERT,
                    parameter=PARAM_OCCLUSION_STATE,
                    value=True,
                    unit=UNIT_BOOLEAN,
                    message=(
                        f"CRITICAL EQUIPMENT ALERT: IV line occlusion or blockage detected. "
                        f"Flow rate is {current_flow_rate_ml_h} ml/h while {remaining_volume_ml} ml remains."
                    ),
                    suggested_action="Inspect tubing for kinks, check catheter insertion site, or open roller clamp.",
                )
            )

        # 4. CRITICAL: Runaway Free-Flow
        if prescribed_rate_ml_h > 0 and current_flow_rate_ml_h >= (prescribed_rate_ml_h * self.runaway_multiplier):
            results.append(
                AnomalyDetectionResult(
                    is_anomaly=True,
                    event_type=DripEventType.DRIP_RUNAWAY,
                    severity=SeverityLevel.CRITICAL,
                    category=AlertCategory.PATIENT_AND_EQUIPMENT_ALERT,
                    parameter=PARAM_FLOW_RATE,
                    value=round(current_flow_rate_ml_h, 1),
                    unit=UNIT_ML_H,
                    message=(
                        f"CRITICAL PATIENT ALERT: Dangerous free-flow runaway detected! "
                        f"Current flow {current_flow_rate_ml_h:.1f} ml/h exceeds 2x prescribed rate."
                    ),
                    suggested_action="Immediately clamp line and recalibrate infusion pump.",
                )
            )

        # 5. WARNING: Low Volume Warning (Fluid <= low_volume_pct)
        volume_pct = (remaining_volume_ml / total_volume_ml * 100.0) if total_volume_ml > 0 else 0.0
        if 0.0 < volume_pct <= self.low_volume_pct:
            results.append(
                AnomalyDetectionResult(
                    is_anomaly=True,
                    event_type=DripEventType.DRIP_LOW,
                    severity=SeverityLevel.HIGH,
                    category=AlertCategory.EQUIPMENT_ALERT,
                    parameter=PARAM_DRIP_STATUS,
                    value=DripStatus.LOW.value,
                    unit=UNIT_STATUS,
                    message=(
                        f"WARNING: IV fluid level low ({volume_pct:.1f}% remaining). "
                        f"Infusion approaching completion."
                    ),
                    suggested_action="Prepare replacement IV fluid container.",
                )
            )

        # 6. WARNING: Flow Rate Deviation
        if prescribed_rate_ml_h > 0 and current_flow_rate_ml_h > self.occlusion_flow_limit:
            deviation_pct = ((current_flow_rate_ml_h - prescribed_rate_ml_h) / prescribed_rate_ml_h) * 100.0
            if abs(deviation_pct) >= self.flow_deviation_pct and not any(
                r.event_type == DripEventType.DRIP_RUNAWAY for r in results
            ):
                results.append(
                    AnomalyDetectionResult(
                        is_anomaly=True,
                        event_type=DripEventType.DRIP_RATE_DEVIATION,
                        severity=SeverityLevel.WARNING,
                        category=AlertCategory.EQUIPMENT_ALERT,
                        parameter=PARAM_FLOW_RATE,
                        value=round(current_flow_rate_ml_h, 1),
                        unit=UNIT_ML_H,
                        message=f"WARNING: Flow rate deviation of {deviation_pct:+.1f}% detected.",
                        suggested_action="Check roller clamp and tubing position to stabilize flow.",
                    )
                )

        # 7. NORMAL
        if not results:
            results.append(
                AnomalyDetectionResult(
                    is_anomaly=False,
                    event_type=DripEventType.DRIP_FLOW_RATE,
                    severity=SeverityLevel.INFO,
                    category=AlertCategory.EQUIPMENT_ALERT,
                    parameter=PARAM_DRIP_STATUS,
                    value=DripStatus.NORMAL.value,
                    unit=UNIT_STATUS,
                    message=f"Normal infusion in progress at {current_flow_rate_ml_h:.1f} ml/h ({volume_pct:.1f}% remaining).",
                    suggested_action="Continue routine monitoring.",
                )
            )

        return results
