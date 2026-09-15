"""ECG waveform generation and arrhythmia analysis module.

Maintained by Melisa. Part of patient device monitoring.
Supports simulated monitoring for ABNORMAL_ECG and NORMAL_ECG transitions.
Completely independent of CCTV / YOLO implementations.
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
import uuid


class ECGAnalyzer:
    """Simulates physiological ECG lead data and detects cardiac arrhythmias."""

    @staticmethod
    def generate_single_lead_points(
        heart_rate: int = 75,
        duration_seconds: float = 1.0,
        sampling_rate: int = 250,
        rhythm_type: str = "NORMAL"
    ) -> List[Dict[str, float]]:
        """Generate synthetic ECG voltage points (mV) over time for monitor streaming."""
        if heart_rate <= 0:
            # Asystole (flatline)
            total_samples = int(duration_seconds * sampling_rate)
            return [{"t": round(i / sampling_rate, 3), "mv": 0.0} for i in range(total_samples)]

        rr_interval = 60.0 / heart_rate
        total_samples = int(duration_seconds * sampling_rate)
        points = []

        # P, Q, R, S, T waves: (name, amplitude, offset_from_R, width)
        waves = [
            ("P", 0.15, -0.16, 0.025),
            ("Q", -0.15, -0.05, 0.012),
            ("R", 1.20, 0.00, 0.015),
            ("S", -0.25, 0.05, 0.015),
            ("T", 0.30, 0.20, 0.040),
        ]

        for i in range(total_samples):
            t = i / sampling_rate
            cycle_pos = (t % rr_interval) - (rr_interval * 0.3)

            voltage = 0.0
            if rhythm_type == "VFIB":
                voltage = 0.3 * math.sin(2 * math.pi * 7 * t) + 0.2 * math.sin(2 * math.pi * 13 * t)
            else:
                for _, amp, offset, width in waves:
                    diff = cycle_pos - offset
                    voltage += amp * math.exp(-0.5 * (diff / width) ** 2)

            points.append({
                "t": round(t, 3),
                "mv": round(voltage, 4)
            })

        return points

    @classmethod
    def evaluate_rhythm(
        cls,
        patient_id: str,
        room_id: str,
        heart_rate: float,
        rhythm_name: str = "NORMAL_SINUS_RHYTHM",
        is_abnormal: bool = False
    ) -> Dict[str, Any]:
        """Evaluate ECG rhythm and generate standard event payload.

        Generates ABNORMAL_ECG (CRITICAL) if arrhythmia or irregularity detected,
        or NORMAL_ECG (INFO) when rhythm is normal.
        """
        # Auto-detect abnormality based on rate or explicit flag
        if is_abnormal or rhythm_name in ("VENTRICULAR_TACHYCARDIA", "VFIB", "ASYSTOLE", "ATRIAL_FIBRILLATION"):
            abnormal = True
        elif heart_rate == 0 or heart_rate > 140 or heart_rate < 40:
            abnormal = True
        else:
            abnormal = False

        if abnormal:
            event_type = "ABNORMAL_ECG"
            severity = "CRITICAL"
            if heart_rate == 0 or rhythm_name == "ASYSTOLE":
                rhythm_val = "ASYSTOLE"
                message = "CRITICAL ECG ALERT: Asystole / Cardiac Arrest detected!"
            elif heart_rate > 140 or rhythm_name == "VENTRICULAR_TACHYCARDIA":
                rhythm_val = "VENTRICULAR_TACHYCARDIA"
                message = f"CRITICAL ECG ALERT: Ventricular Tachycardia suspected at {heart_rate:.0f} bpm."
            elif rhythm_name == "ATRIAL_FIBRILLATION":
                rhythm_val = "ATRIAL_FIBRILLATION"
                message = f"CRITICAL ECG ALERT: Atrial Fibrillation detected at {heart_rate:.0f} bpm."
            else:
                rhythm_val = "ARRHYTHMIA"
                message = f"CRITICAL ECG ALERT: Cardiac arrhythmia detected at {heart_rate:.0f} bpm."
        else:
            event_type = "NORMAL_ECG"
            severity = "INFO"
            rhythm_val = rhythm_name or "NORMAL_SINUS_RHYTHM"
            message = f"ECG rhythm normal: {rhythm_val} ({heart_rate:.0f} bpm)."

        return {
            "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "patient_id": patient_id,
            "room_id": room_id,
            "source": "device_simulator",
            "parameter": "ecg_rhythm",
            "value": rhythm_val,
            "unit": "status",
            "severity": severity,
            "message": message,
            "status": "ACTIVE"
        }
