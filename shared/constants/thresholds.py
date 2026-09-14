"""
Shared Clinical Thresholds and Reference Ranges
===============================================
SmartPatientCare standard definitions for vital signs, IV infusion parameters,
and device states based on standard clinical adult reference ranges.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from typing import Dict, Any

# Clinical reference ranges for standard adult telemetry
VITALS_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "heart_rate": {
        "unit": "bpm",
        "normal_min": 60,
        "normal_max": 100,
        "warning_low": 50,
        "warning_high": 120,
        "critical_low": 45,
        "critical_high": 140,
        "expected_range": "60 - 100 bpm",
    },
    "spo2": {
        "unit": "%",
        "normal_min": 95,
        "normal_max": 100,
        "warning_low": 90,
        "critical_low": 85,
        "expected_range": "95 - 100%",
    },
    "systolic_bp": {
        "unit": "mmHg",
        "normal_min": 90,
        "normal_max": 120,
        "warning_high": 140,
        "critical_high": 180,
        "critical_low": 80,
        "expected_range": "90 - 120 mmHg",
    },
    "diastolic_bp": {
        "unit": "mmHg",
        "normal_min": 60,
        "normal_max": 80,
        "warning_high": 90,
        "critical_high": 110,
        "critical_low": 50,
        "expected_range": "60 - 80 mmHg",
    },
    "temperature": {
        "unit": "°C",
        "normal_min": 36.5,
        "normal_max": 37.5,
        "warning_high": 38.0,
        "critical_high": 39.0,
        "critical_low": 35.0,
        "expected_range": "36.5 - 37.5 °C",
    },
    "respiratory_rate": {
        "unit": "breaths/min",
        "normal_min": 12,
        "normal_max": 20,
        "warning_low": 10,
        "warning_high": 24,
        "critical_low": 8,
        "critical_high": 28,
        "expected_range": "12 - 20 breaths/min",
    },
}

# IV Drip monitoring reference bounds
IV_DRIP_THRESHOLDS: Dict[str, Any] = {
    "volume_low_warning_ml": 100.0,
    "volume_critical_empty_ml": 25.0,
    "volume_depleted_ml": 5.0,
    "flow_rate_stopped_threshold": 2.0,  # ml/h
    "expected_range": "> 100 ml",
}

# ECG States
ECG_NORMAL_RHYTHM = "NORMAL_SINUS_RHYTHM"
ECG_ABNORMAL_RHYTHMS = {
    "SINUS_TACHYCARDIA": {"severity": "WARNING", "message": "Elevated sinus rate detected"},
    "SINUS_BRADYCARDIA": {"severity": "WARNING", "message": "Depressed sinus rate detected"},
    "VENTRICULAR_FIBRILLATION": {"severity": "CRITICAL", "message": "Ventricular Fibrillation - immediate resuscitation required"},
    "ASYSTOLE": {"severity": "CRITICAL", "message": "Asystole detected - code blue alert"},
    "LEAD_DISCONNECTED": {"severity": "WARNING", "message": "ECG leads detached or impedance fault"},
}
