"""Anomaly detection algorithms for IV drip monitoring.

Analyzes telemetry to identify clinical and equipment safety events:
- Drip completion (empty IV bag) -> CRITICAL
- Occlusion / line blockage (flow drops to 0 with fluid left) -> CRITICAL EQUIPMENT ALERT
- Runaway flow / uncontrolled infusion -> CRITICAL PATIENT & EQUIPMENT ALERT
- Air in line detection -> CRITICAL EQUIPMENT ALERT
- Low volume warning (<= 15% fluid remaining) -> WARNING
- Flow rate deviation from prescribed rate -> WARNING
- Normal infusion state -> INFO / NORMAL
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .constants import (
    SeverityLevel,
    AlertCategory,
    DripEventType,
    LOW_VOLUME_PERCENT_THRESHOLD,
    CRITICAL_VOLUME_THRESHOLD,
    OCCLUSION_FLOW_THRESHOLD_ML_H,
    FLOW_DEVIATION_TOLERANCE_PCT,
    RUNAWAY_FLOW_MULTIPLIER,
    PARAM_FLOW_RATE,
    PARAM_REMAINING_VOLUME,
    PARAM_OCCLUSION_STATE,
    PARAM_AIR_IN_LINE,
    PARAM_DRIP_STATUS,
    UNIT_ML_H,
    UNIT_ML,
    UNIT_PERCENT,
    UNIT_STATUS,
    UNIT_BOOLEAN,
)


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
        """Evaluate an IV drip status snapshot and return any detected anomalies.

        Ordered by clinical priority (Critical equipment/patient events first).
        """
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
                    event_type=DripEventType.DRIP_EMPTY,
                    severity=SeverityLevel.CRITICAL,
                    category=AlertCategory.PATIENT_AND_EQUIPMENT_ALERT,
                    parameter=PARAM_REMAINING_VOLUME,
                    value=0.0,
                    unit=UNIT_ML,
                    message="CRITICAL: IV bag empty. Infusion cycle completed.",
                    suggested_action="Replace IV container or flush line and discontinue infusion.",
                )
            )
            # If bag is empty, flow is expected to be zero, so return early
            return results

        # 3. CRITICAL: Occlusion / Line Blockage (Flow is zero or near zero, but fluid still remains)
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

        # 4. CRITICAL: Runaway Free-Flow (Dangerous over-infusion > 200% prescribed)
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
                        f"Current flow {current_flow_rate_ml_h:.1f} ml/h exceeds 2x prescribed rate ({prescribed_rate_ml_h:.1f} ml/h)."
                    ),
                    suggested_action="Immediately clamp line and recalibrate infusion pump.",
                )
            )

        # 5. WARNING: Low Volume Warning (Fluid <= 15%)
        volume_pct = (remaining_volume_ml / total_volume_ml * 100.0) if total_volume_ml > 0 else 0.0
        if 0.0 < volume_pct <= self.low_volume_pct:
            results.append(
                AnomalyDetectionResult(
                    is_anomaly=True,
                    event_type=DripEventType.DRIP_VOLUME_LOW,
                    severity=SeverityLevel.WARNING,
                    category=AlertCategory.EQUIPMENT_ALERT,
                    parameter=PARAM_REMAINING_VOLUME,
                    value=round(remaining_volume_ml, 1),
                    unit=UNIT_ML,
                    message=(
                        f"WARNING: IV fluid level low ({volume_pct:.1f}% / {remaining_volume_ml:.1f} ml remaining). "
                        f"Infusion approaching completion."
                    ),
                    suggested_action="Prepare replacement IV fluid container.",
                )
            )

        # 6. WARNING: Flow Rate Deviation (Unintended speed deviation +/- 20%)
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
                        message=(
                            f"WARNING: Flow rate deviation of {deviation_pct:+.1f}% detected "
                            f"(Actual: {current_flow_rate_ml_h:.1f} ml/h, Prescribed: {prescribed_rate_ml_h:.1f} ml/h)."
                        ),
                        suggested_action="Check roller clamp and tubing position to stabilize flow.",
                    )
                )

        # 7. NORMAL: If no warnings or critical events were triggered
        if not results:
            results.append(
                AnomalyDetectionResult(
                    is_anomaly=False,
                    event_type=DripEventType.DRIP_FLOW_RATE,
                    severity=SeverityLevel.INFO,
                    category=AlertCategory.EQUIPMENT_ALERT,
                    parameter=PARAM_DRIP_STATUS,
                    value="NORMAL",
                    unit=UNIT_STATUS,
                    message=f"Normal infusion in progress at {current_flow_rate_ml_h:.1f} ml/h ({volume_pct:.1f}% remaining).",
                    suggested_action="Continue routine monitoring.",
                )
            )

        return results
