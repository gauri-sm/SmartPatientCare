"""Vital signs clinical threshold evaluation and event generation module.

Maintained by Melisa. Supports simulated device monitoring for:
- LOW_SPO2
- ABNORMAL_HEART_RATE
- ABNORMAL_BP
- ABNORMAL_TEMPERATURE
- ABNORMAL_RESPIRATORY_RATE

Fully compatible with SmartPatientCare alert engine and shared event schemas.
Completely independent from CCTV / YOLO logic.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class VitalsThresholdConfig:
    """Configurable thresholds for medical device telemetry alerts."""
    # SpO2 thresholds (%)
    spo2_critical: float = 90.0   # Below this is CRITICAL LOW_SPO2
    spo2_high: float = 94.0       # Below this is HIGH LOW_SPO2

    # Heart rate thresholds (bpm)
    hr_critical_high: float = 120.0  # Above this is CRITICAL ABNORMAL_HEART_RATE
    hr_high: float = 100.0           # Above this is HIGH ABNORMAL_HEART_RATE
    hr_critical_low: float = 45.0    # Below this is CRITICAL ABNORMAL_HEART_RATE
    hr_low: float = 60.0             # Below this is HIGH ABNORMAL_HEART_RATE

    # Blood pressure thresholds (mmHg)
    bp_sys_critical_high: float = 180.0  # CRITICAL ABNORMAL_BP
    bp_dia_critical_high: float = 120.0  # CRITICAL ABNORMAL_BP
    bp_sys_high: float = 140.0           # HIGH ABNORMAL_BP
    bp_dia_high: float = 90.0            # HIGH ABNORMAL_BP
    bp_sys_low: float = 90.0             # HIGH ABNORMAL_BP (Hypotension)
    bp_sys_shock: float = 70.0           # CRITICAL ABNORMAL_BP (Shock)

    # Temperature thresholds (°C)
    temp_critical_high: float = 39.5  # HIGH ABNORMAL_TEMPERATURE
    temp_high: float = 38.0           # MEDIUM ABNORMAL_TEMPERATURE
    temp_low: float = 35.5            # MEDIUM ABNORMAL_TEMPERATURE (Hypothermia)

    # Respiratory rate thresholds (breaths/min)
    rr_critical_high: float = 30.0    # CRITICAL ABNORMAL_RESPIRATORY_RATE (Severe Tachypnea)
    rr_high: float = 20.0             # HIGH ABNORMAL_RESPIRATORY_RATE (Tachypnea)
    rr_critical_low: float = 8.0      # CRITICAL ABNORMAL_RESPIRATORY_RATE (Severe Bradypnea)
    rr_low: float = 12.0              # HIGH ABNORMAL_RESPIRATORY_RATE (Bradypnea)


class VitalsProcessor:
    """Processes physiological telemetry, classifies clinical severity, and formats events."""

    def __init__(self, thresholds: Optional[VitalsThresholdConfig] = None):
        self.thresholds = thresholds or VitalsThresholdConfig()

    @staticmethod
    def _create_event(
        patient_id: str,
        room_id: str,
        event_type: str,
        parameter: str,
        value: Any,
        unit: str,
        severity: str,
        message: str,
        source: str = "device_simulator"
    ) -> Dict[str, Any]:
        """Format an event dictionary conforming strictly to the shared event architecture.

        Does not require or include CCTV-specific fields (video_source, camera_id, etc.).
        """
        return {
            "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "patient_id": patient_id,
            "room_id": room_id,
            "source": source,
            "parameter": parameter,
            "value": value,
            "unit": unit,
            "severity": severity,
            "message": message,
            "status": "ACTIVE"
        }

    def evaluate_spo2(self, patient_id: str, room_id: str, spo2: float) -> Dict[str, Any]:
        """Evaluate oxygen saturation and generate LOW_SPO2 if sub-threshold."""
        t = self.thresholds
        if spo2 <= t.spo2_critical:
            event_type = "LOW_SPO2"
            severity = "CRITICAL"
            message = f"Severe Hypoxemia: SpO2 critically low at {spo2:.1f}%."
        elif spo2 <= t.spo2_high:
            event_type = "LOW_SPO2"
            severity = "HIGH"
            message = f"Hypoxia alert: SpO2 dropped to {spo2:.1f}%."
        else:
            event_type = "VITAL_SIGN"
            severity = "INFO"
            message = f"SpO2 normal: {spo2:.1f}%."

        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type=event_type,
            parameter="spo2",
            value=round(spo2, 1),
            unit="%",
            severity=severity,
            message=message
        )

    def evaluate_heart_rate(self, patient_id: str, room_id: str, hr: float) -> Dict[str, Any]:
        """Evaluate heart rate and generate ABNORMAL_HEART_RATE if sub-threshold or elevated."""
        t = self.thresholds
        if hr >= t.hr_critical_high:
            event_type = "ABNORMAL_HEART_RATE"
            severity = "CRITICAL"
            message = f"Critical Tachycardia: Heart rate spiked to {hr:.0f} bpm."
        elif hr > t.hr_high:
            event_type = "ABNORMAL_HEART_RATE"
            severity = "HIGH"
            message = f"Tachycardia detected: Heart rate elevated at {hr:.0f} bpm."
        elif hr <= t.hr_critical_low:
            event_type = "ABNORMAL_HEART_RATE"
            severity = "CRITICAL"
            message = f"Severe Bradycardia: Heart rate critically low at {hr:.0f} bpm."
        elif hr < t.hr_low:
            event_type = "ABNORMAL_HEART_RATE"
            severity = "HIGH"
            message = f"Bradycardia detected: Heart rate is low at {hr:.0f} bpm."
        else:
            event_type = "VITAL_SIGN"
            severity = "INFO"
            message = f"Heart rate normal: {hr:.0f} bpm."

        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type=event_type,
            parameter="heart_rate",
            value=round(hr, 1),
            unit="bpm",
            severity=severity,
            message=message
        )

    def evaluate_blood_pressure(self, patient_id: str, room_id: str, bp: str) -> Dict[str, Any]:
        """Evaluate blood pressure (systolic/diastolic) and generate ABNORMAL_BP if out of range."""
        t = self.thresholds
        try:
            sys_str, dia_str = bp.split("/")
            systolic = float(sys_str)
            diastolic = float(dia_str)
        except Exception:
            return self._create_event(
                patient_id=patient_id,
                room_id=room_id,
                event_type="ABNORMAL_BP",
                parameter="blood_pressure",
                value=bp,
                unit="mmHg",
                severity="HIGH",
                message=f"Malformed blood pressure reading: {bp}"
            )

        if systolic >= t.bp_sys_critical_high or diastolic >= t.bp_dia_critical_high:
            event_type = "ABNORMAL_BP"
            severity = "CRITICAL"
            message = f"Hypertensive Crisis: Blood pressure reached dangerous level {bp} mmHg."
        elif systolic <= t.bp_sys_shock:
            event_type = "ABNORMAL_BP"
            severity = "CRITICAL"
            message = f"Circulatory Shock / Severe Hypotension: Blood pressure {bp} mmHg."
        elif systolic >= t.bp_sys_high or diastolic >= t.bp_dia_high:
            event_type = "ABNORMAL_BP"
            severity = "HIGH"
            message = f"Hypertension alert: Elevated blood pressure {bp} mmHg."
        elif systolic < t.bp_sys_low:
            event_type = "ABNORMAL_BP"
            severity = "HIGH"
            message = f"Hypotension alert: Low blood pressure {bp} mmHg."
        else:
            event_type = "VITAL_SIGN"
            severity = "INFO"
            message = f"Blood pressure within normal limits: {bp} mmHg."

        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type=event_type,
            parameter="blood_pressure",
            value=bp,
            unit="mmHg",
            severity=severity,
            message=message
        )

    def evaluate_temperature(self, patient_id: str, room_id: str, temp: float) -> Dict[str, Any]:
        """Evaluate body temperature and generate ABNORMAL_TEMPERATURE if febrile or hypothermic."""
        t = self.thresholds
        if temp >= t.temp_critical_high:
            event_type = "ABNORMAL_TEMPERATURE"
            severity = "HIGH"
            message = f"Hyperpyrexia alert: Core body temperature reached {temp:.1f} °C."
        elif temp >= t.temp_high:
            event_type = "ABNORMAL_TEMPERATURE"
            severity = "MEDIUM"
            message = f"Pyrexia / Fever: Body temperature elevated at {temp:.1f} °C."
        elif temp <= t.temp_low:
            event_type = "ABNORMAL_TEMPERATURE"
            severity = "MEDIUM"
            message = f"Hypothermia alert: Body temperature dropped to {temp:.1f} °C."
        else:
            event_type = "VITAL_SIGN"
            severity = "INFO"
            message = f"Body temperature normal: {temp:.1f} °C."

        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type=event_type,
            parameter="temperature",
            value=round(temp, 1),
            unit="°C",
            severity=severity,
            message=message
        )

    def evaluate_respiratory_rate(self, patient_id: str, room_id: str, respiratory_rate: float) -> Dict[str, Any]:
        """Evaluate respiratory rate and generate ABNORMAL_RESPIRATORY_RATE if out of range."""
        t = self.thresholds
        rr = float(respiratory_rate)
        if rr >= t.rr_critical_high:
            event_type = "ABNORMAL_RESPIRATORY_RATE"
            severity = "CRITICAL"
            message = f"Critical Tachypnea: Respiratory rate dangerously high at {rr:.0f} breaths/min."
        elif rr > t.rr_high:
            event_type = "ABNORMAL_RESPIRATORY_RATE"
            severity = "HIGH"
            message = f"Tachypnea alert: Elevated respiratory rate at {rr:.0f} breaths/min."
        elif rr <= t.rr_critical_low:
            event_type = "ABNORMAL_RESPIRATORY_RATE"
            severity = "CRITICAL"
            message = f"Severe Bradypnea: Respiratory rate critically low at {rr:.0f} breaths/min."
        elif rr < t.rr_low:
            event_type = "ABNORMAL_RESPIRATORY_RATE"
            severity = "HIGH"
            message = f"Bradypnea alert: Low respiratory rate at {rr:.0f} breaths/min."
        else:
            event_type = "VITAL_SIGN"
            severity = "INFO"
            message = f"Respiratory rate normal: {rr:.0f} breaths/min."

        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type=event_type,
            parameter="respiratory_rate",
            value=round(rr, 1),
            unit="breaths/min",
            severity=severity,
            message=message
        )

    def evaluate_all(
        self,
        patient_id: str,
        room_id: str,
        vitals: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Evaluate a batch of vitals and return schema-compliant events."""
        events = []
        if "spo2" in vitals and vitals["spo2"] is not None:
            events.append(self.evaluate_spo2(patient_id, room_id, float(vitals["spo2"])))
        if "heart_rate" in vitals and vitals["heart_rate"] is not None:
            events.append(self.evaluate_heart_rate(patient_id, room_id, float(vitals["heart_rate"])))
        if "blood_pressure" in vitals and vitals["blood_pressure"]:
            events.append(self.evaluate_blood_pressure(patient_id, room_id, str(vitals["blood_pressure"])))
        if "temperature" in vitals and vitals["temperature"] is not None:
            events.append(self.evaluate_temperature(patient_id, room_id, float(vitals["temperature"])))
        if "respiratory_rate" in vitals and vitals["respiratory_rate"] is not None:
            events.append(self.evaluate_respiratory_rate(patient_id, room_id, float(vitals["respiratory_rate"])))
        return events


# Default singleton instance
default_vitals_processor = VitalsProcessor()
