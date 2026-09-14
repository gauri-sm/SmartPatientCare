"""
Emergency Alerts Rules Engine
=============================
Evaluates multi-source telemetry against clinical rules and returns standardized
SmartPatientCareEvent objects.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import logging

from sandra.emergency_alerts.src.models import (
    SmartPatientCareEvent,
    SeverityLevel,
    AlertStatus,
    EventType,
)
from sandra.emergency_alerts.src.thresholds import (
    evaluate_heart_rate,
    evaluate_spo2,
    evaluate_blood_pressure,
    evaluate_temperature,
    evaluate_respiratory_rate,
    evaluate_iv_drip,
    evaluate_ecg,
)

logger = logging.getLogger("sandra.rules_engine")

# Centralized, configurable default severity classification table
DEFAULT_SEVERITY_MAPPING: Dict[str, SeverityLevel] = {
    "FALL_DETECTED": SeverityLevel.CRITICAL,
    "EMERGENCY": SeverityLevel.CRITICAL,
    "EMERGENCY_TRIGGER": SeverityLevel.CRITICAL,
    "ABNORMAL_ECG": SeverityLevel.CRITICAL,
    "LOW_SPO2": SeverityLevel.CRITICAL,
    "DRIP_FINISHED": SeverityLevel.HIGH,
    "PATIENT_LEFT_BED": SeverityLevel.HIGH,
    "ABNORMAL_MOVEMENT": SeverityLevel.HIGH,
    "VENTILATOR_ALERT": SeverityLevel.HIGH,
    "VENTILATOR_RECOMMENDATION": SeverityLevel.HIGH,
    "ABNORMAL_BP": SeverityLevel.HIGH,
    "ABNORMAL_HEART_RATE": SeverityLevel.HIGH,
    "ABNORMAL_TEMPERATURE": SeverityLevel.HIGH,
    "UNUSUAL_POSITION": SeverityLevel.MEDIUM,
    "DRIP_LOW": SeverityLevel.MEDIUM,
    "DRIP_ALERT": SeverityLevel.WARNING,
    "VITAL_SIGN": SeverityLevel.WARNING,
}


class RulesEngine:
    """
    Evaluates patient telemetry and produces prioritized clinical alerts.
    """

    def __init__(self, severity_mapping: Optional[Dict[str, SeverityLevel]] = None):
        self.severity_mapping = dict(DEFAULT_SEVERITY_MAPPING)
        if severity_mapping:
            self.severity_mapping.update(severity_mapping)

    def normalize_event(self, raw_data: Dict[str, Any]) -> SmartPatientCareEvent:
        """
        Normalizes any incoming event from CCTV/YOLO, Medical Devices, IV Drip,
        or Emergency triggers into a validated, schema-compliant SmartPatientCareEvent.
        Preserves optional CCTV evidence fields and captures extra teammate metadata.
        """
        raw = dict(raw_data)
        event_type_str = str(raw.get("event_type", "SYSTEM")).strip().upper()
        patient_id = str(raw.get("patient_id", "UNKNOWN")).strip()
        room_id = str(raw.get("room_id", "UNKNOWN")).strip()
        source = str(raw.get("source", "EXTERNAL_MONITOR")).strip()

        # Severity resolution
        raw_sev = raw.get("severity")
        if raw_sev is not None:
            sev_clean = str(raw_sev).strip().upper()
            try:
                severity = SeverityLevel(sev_clean)
            except ValueError:
                # Map unknown string to closest known severity or default
                if "CRIT" in sev_clean:
                    severity = SeverityLevel.CRITICAL
                elif "HIGH" in sev_clean:
                    severity = SeverityLevel.HIGH
                elif "WARN" in sev_clean:
                    severity = SeverityLevel.WARNING
                elif "MED" in sev_clean:
                    severity = SeverityLevel.MEDIUM
                elif "LOW" in sev_clean:
                    severity = SeverityLevel.LOW
                else:
                    severity = SeverityLevel.INFO
        else:
            severity = self.severity_mapping.get(event_type_str, SeverityLevel.WARNING)

        # Parameter & values
        param = raw.get("parameter")
        if not param:
            param = event_type_str.lower()

        val = raw.get("value")
        if val is None and "value" not in raw:
            val = "DETECTED"

        unit = raw.get("unit")
        if not unit:
            unit = "status"

        message = raw.get("message")
        if not message:
            message = f"{event_type_str.replace('_', ' ').title()} recorded for patient {patient_id}"

        # Status
        raw_status = raw.get("status", "ACTIVE")
        try:
            status = AlertStatus(str(raw_status).upper())
        except ValueError:
            status = AlertStatus.ACTIVE

        # Optional CCTV / Evidence Fields
        video_source = raw.get("video_source")
        camera_id = raw.get("camera_id")
        evidence_type = raw.get("evidence_type")

        # Collect additional arbitrary teammate telemetry fields
        standard_keys = {
            "event_id", "timestamp", "event_type", "patient_id", "room_id",
            "source", "parameter", "value", "unit", "severity", "message",
            "status", "video_source", "camera_id", "evidence_type"
        }
        extra_telemetry = {k: v for k, v in raw.items() if k not in standard_keys}

        return SmartPatientCareEvent(
            event_id=str(raw.get("event_id") or uuid.uuid4()),
            timestamp=str(raw.get("timestamp") or datetime.now(timezone.utc).isoformat()),
            event_type=event_type_str,
            patient_id=patient_id,
            room_id=room_id,
            source=source,
            parameter=str(param),
            value=val,
            unit=str(unit),
            severity=severity,
            message=str(message),
            status=status,
            video_source=video_source,
            camera_id=camera_id,
            evidence_type=evidence_type,
            extra_telemetry=extra_telemetry,
        )

    def evaluate_vitals(
        self,
        patient_id: str,
        room_id: str,
        vitals: Dict[str, Any],
        source: str = "device_simulator",
    ) -> List[SmartPatientCareEvent]:
        """
        Evaluates a patient's vital signs and returns any generated alert events.
        """
        events: List[SmartPatientCareEvent] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Heart Rate
        if "heart_rate" in vitals and vitals["heart_rate"] is not None:
            try:
                hr = float(vitals["heart_rate"])
                sev, msg, _ = evaluate_heart_rate(hr)
                if sev is not None:
                    events.append(
                        SmartPatientCareEvent(
                            event_id=str(uuid.uuid4()),
                            timestamp=now_iso,
                            event_type=EventType.VITAL_SIGN.value,
                            patient_id=patient_id,
                            room_id=room_id,
                            source=source,
                            parameter="heart_rate",
                            value=hr,
                            unit="bpm",
                            severity=sev,
                            message=msg,
                            status=AlertStatus.ACTIVE,
                        )
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Malformed heart_rate for patient {patient_id}: {e}")

        # 2. SpO2
        if "spo2" in vitals and vitals["spo2"] is not None:
            try:
                spo2 = float(vitals["spo2"])
                sev, msg, _ = evaluate_spo2(spo2)
                if sev is not None:
                    events.append(
                        SmartPatientCareEvent(
                            event_id=str(uuid.uuid4()),
                            timestamp=now_iso,
                            event_type=EventType.VITAL_SIGN.value,
                            patient_id=patient_id,
                            room_id=room_id,
                            source=source,
                            parameter="spo2",
                            value=spo2,
                            unit="%",
                            severity=sev,
                            message=msg,
                            status=AlertStatus.ACTIVE,
                        )
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Malformed spo2 for patient {patient_id}: {e}")

        # 3. Blood Pressure
        sys_val = vitals.get("systolic_bp")
        dia_val = vitals.get("diastolic_bp")
        bp_str = vitals.get("blood_pressure")

        if (sys_val is None or dia_val is None) and bp_str and "/" in str(bp_str):
            try:
                parts = str(bp_str).split("/")
                sys_val = float(parts[0].strip())
                dia_val = float(parts[1].strip())
            except Exception:
                pass

        if sys_val is not None and dia_val is not None:
            try:
                sys_f = float(sys_val)
                dia_f = float(dia_val)
                sev, msg, _ = evaluate_blood_pressure(sys_f, dia_f)
                if sev is not None:
                    events.append(
                        SmartPatientCareEvent(
                            event_id=str(uuid.uuid4()),
                            timestamp=now_iso,
                            event_type=EventType.VITAL_SIGN.value,
                            patient_id=patient_id,
                            room_id=room_id,
                            source=source,
                            parameter="blood_pressure",
                            value=f"{sys_f:.0f}/{dia_f:.0f}",
                            unit="mmHg",
                            severity=sev,
                            message=msg,
                            status=AlertStatus.ACTIVE,
                        )
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Malformed blood_pressure for patient {patient_id}: {e}")

        # 4. Temperature
        if "temperature" in vitals and vitals["temperature"] is not None:
            try:
                temp = float(vitals["temperature"])
                sev, msg, _ = evaluate_temperature(temp)
                if sev is not None:
                    events.append(
                        SmartPatientCareEvent(
                            event_id=str(uuid.uuid4()),
                            timestamp=now_iso,
                            event_type=EventType.VITAL_SIGN.value,
                            patient_id=patient_id,
                            room_id=room_id,
                            source=source,
                            parameter="temperature",
                            value=temp,
                            unit="°C",
                            severity=sev,
                            message=msg,
                            status=AlertStatus.ACTIVE,
                        )
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Malformed temperature for patient {patient_id}: {e}")

        # 5. Respiratory Rate
        if "respiratory_rate" in vitals and vitals["respiratory_rate"] is not None:
            try:
                rr = float(vitals["respiratory_rate"])
                sev, msg, _ = evaluate_respiratory_rate(rr)
                if sev is not None:
                    events.append(
                        SmartPatientCareEvent(
                            event_id=str(uuid.uuid4()),
                            timestamp=now_iso,
                            event_type=EventType.VITAL_SIGN.value,
                            patient_id=patient_id,
                            room_id=room_id,
                            source=source,
                            parameter="respiratory_rate",
                            value=rr,
                            unit="breaths/min",
                            severity=sev,
                            message=msg,
                            status=AlertStatus.ACTIVE,
                        )
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Malformed respiratory_rate for patient {patient_id}: {e}")

        return events

    def evaluate_iv_drip(
        self,
        patient_id: str,
        room_id: str,
        volume_remaining_ml: float,
        flow_rate_ml_h: float = 100.0,
        source: str = "drip_sensor",
    ) -> List[SmartPatientCareEvent]:
        """
        Evaluates IV drip levels.
        """
        events: List[SmartPatientCareEvent] = []
        sev, msg, _ = evaluate_iv_drip(volume_remaining_ml, flow_rate_ml_h)
        if sev is not None:
            events.append(
                SmartPatientCareEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event_type=EventType.DRIP_ALERT.value,
                    patient_id=patient_id,
                    room_id=room_id,
                    source=source,
                    parameter="iv_drip_volume",
                    value=float(volume_remaining_ml),
                    unit="ml",
                    severity=sev,
                    message=msg,
                    status=AlertStatus.ACTIVE,
                )
            )
        return events

    def evaluate_ecg(
        self,
        patient_id: str,
        room_id: str,
        rhythm: str,
        source: str = "device_simulator",
    ) -> List[SmartPatientCareEvent]:
        """
        Evaluates ECG rhythm.
        """
        events: List[SmartPatientCareEvent] = []
        sev, msg, _ = evaluate_ecg(rhythm)
        if sev is not None:
            events.append(
                SmartPatientCareEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event_type=EventType.ECG_ABNORMAL.value,
                    patient_id=patient_id,
                    room_id=room_id,
                    source=source,
                    parameter="ecg_rhythm",
                    value=rhythm,
                    unit="status",
                    severity=sev,
                    message=msg,
                    status=AlertStatus.ACTIVE,
                )
            )
        return events
