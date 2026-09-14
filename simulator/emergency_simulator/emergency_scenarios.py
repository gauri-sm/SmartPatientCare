"""
Emergency Simulator Scenarios
=============================
Pre-configured clinical emergency scenarios designed for hackathon demonstration.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from typing import Dict, Any

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "NORMAL_BASELINE": {
        "title": "Normal Patient Baseline",
        "description": "Restores patient telemetry to normal, healthy adult ranges.",
        "target_patient_id": "P001",
        "vitals": {
            "heart_rate": 72.0,
            "blood_pressure": "118/76",
            "systolic_bp": 118.0,
            "diastolic_bp": 76.0,
            "spo2": 98.0,
            "respiratory_rate": 16.0,
            "temperature": 36.8,
        },
        "iv_drip": {
            "volume_remaining_ml": 480.0,
            "flow_rate_ml_h": 100.0,
            "status": "NORMAL",
        },
        "ecg": {
            "rhythm": "NORMAL_SINUS_RHYTHM",
            "status": "NORMAL",
        },
    },
    "LOW_SPO2": {
        "title": "Critical Low SpO2 (Hypoxemia)",
        "description": "Acute drop in oxygen saturation down to 82% requiring urgent oxygenation.",
        "target_patient_id": "P002",
        "vitals": {
            "heart_rate": 112.0,
            "blood_pressure": "135/85",
            "systolic_bp": 135.0,
            "diastolic_bp": 85.0,
            "spo2": 82.0,  # Critical < 85%
            "respiratory_rate": 28.0,
            "temperature": 37.8,
        },
        "iv_drip": {
            "volume_remaining_ml": 310.0,
            "flow_rate_ml_h": 75.0,
            "status": "NORMAL",
        },
        "ecg": {
            "rhythm": "NORMAL_SINUS_RHYTHM",
            "status": "NORMAL",
        },
    },
    "HIGH_HEART_RATE": {
        "title": "Severe Tachycardia",
        "description": "Rapid spike in heart rate to 155 bpm indicative of cardiac distress.",
        "target_patient_id": "P004",
        "vitals": {
            "heart_rate": 155.0,  # Critical > 140 bpm
            "blood_pressure": "148/96",
            "systolic_bp": 148.0,
            "diastolic_bp": 96.0,
            "spo2": 93.0,
            "respiratory_rate": 24.0,
            "temperature": 37.4,
        },
        "iv_drip": {
            "volume_remaining_ml": 250.0,
            "flow_rate_ml_h": 80.0,
            "status": "NORMAL",
        },
        "ecg": {
            "rhythm": "SINUS_TACHYCARDIA",
            "status": "WARNING",
        },
    },
    "LOW_HEART_RATE": {
        "title": "Severe Bradycardia",
        "description": "Dangerous drop in heart rate to 42 bpm requiring immediate pacing/atropine.",
        "target_patient_id": "P001",
        "vitals": {
            "heart_rate": 42.0,  # Critical < 45 bpm
            "blood_pressure": "88/54",
            "systolic_bp": 88.0,
            "diastolic_bp": 54.0,
            "spo2": 94.0,
            "respiratory_rate": 11.0,
            "temperature": 36.4,
        },
        "iv_drip": {
            "volume_remaining_ml": 400.0,
            "flow_rate_ml_h": 50.0,
            "status": "NORMAL",
        },
        "ecg": {
            "rhythm": "SINUS_BRADYCARDIA",
            "status": "WARNING",
        },
    },
    "HYPERTENSIVE_CRISIS": {
        "title": "Hypertensive Crisis",
        "description": "Blood pressure skyrockets to 188/118 mmHg with risk of end-organ damage.",
        "target_patient_id": "P004",
        "vitals": {
            "heart_rate": 108.0,
            "blood_pressure": "188/118",
            "systolic_bp": 188.0,  # Critical >= 180
            "diastolic_bp": 118.0,  # Critical >= 110
            "spo2": 95.0,
            "respiratory_rate": 22.0,
            "temperature": 37.2,
        },
        "iv_drip": {
            "volume_remaining_ml": 190.0,
            "flow_rate_ml_h": 60.0,
            "status": "NORMAL",
        },
        "ecg": {
            "rhythm": "NORMAL_SINUS_RHYTHM",
            "status": "NORMAL",
        },
    },
    "HIGH_TEMPERATURE": {
        "title": "High Grade Pyrexia / Sepsis Alert",
        "description": "Core body temperature jumps to 39.8 °C with rigors and tachycardia.",
        "target_patient_id": "P002",
        "vitals": {
            "heart_rate": 128.0,
            "blood_pressure": "105/65",
            "systolic_bp": 105.0,
            "diastolic_bp": 65.0,
            "spo2": 94.0,
            "respiratory_rate": 26.0,
            "temperature": 39.8,  # Critical >= 39.0 °C
        },
        "iv_drip": {
            "volume_remaining_ml": 180.0,
            "flow_rate_ml_h": 120.0,
            "status": "NORMAL",
        },
        "ecg": {
            "rhythm": "SINUS_TACHYCARDIA",
            "status": "WARNING",
        },
    },
    "DRIP_LOW": {
        "title": "IV Drip Near-Empty",
        "description": "Infusion reservoir down to 35 ml remaining at 100 ml/h.",
        "target_patient_id": "P003",
        "vitals": {
            "heart_rate": 78.0,
            "blood_pressure": "116/74",
            "systolic_bp": 116.0,
            "diastolic_bp": 74.0,
            "spo2": 98.0,
            "respiratory_rate": 15.0,
            "temperature": 36.9,
        },
        "iv_drip": {
            "volume_remaining_ml": 35.0,  # Warning <= 100 ml
            "flow_rate_ml_h": 100.0,
            "status": "LOW",
        },
        "ecg": {
            "rhythm": "NORMAL_SINUS_RHYTHM",
            "status": "NORMAL",
        },
    },
    "DRIP_FINISHED": {
        "title": "IV Drip Finished / Occluded",
        "description": "Infusion bag completely empty (0 ml) with flow stoppage.",
        "target_patient_id": "P001",
        "vitals": {
            "heart_rate": 82.0,
            "blood_pressure": "122/78",
            "systolic_bp": 122.0,
            "diastolic_bp": 78.0,
            "spo2": 97.0,
            "respiratory_rate": 16.0,
            "temperature": 36.8,
        },
        "iv_drip": {
            "volume_remaining_ml": 0.0,  # Critical empty
            "flow_rate_ml_h": 0.0,
            "status": "EMPTY",
        },
        "ecg": {
            "rhythm": "NORMAL_SINUS_RHYTHM",
            "status": "NORMAL",
        },
    },
    "ECG_ARRHYTHMIA": {
        "title": "Cardiac Arrest / Ventricular Fibrillation",
        "description": "Lethal cardiac arrhythmia detected on bedside telemetry.",
        "target_patient_id": "P004",
        "vitals": {
            "heart_rate": 190.0,
            "blood_pressure": "60/30",
            "systolic_bp": 60.0,
            "diastolic_bp": 30.0,
            "spo2": 78.0,
            "respiratory_rate": 6.0,
            "temperature": 36.2,
        },
        "iv_drip": {
            "volume_remaining_ml": 150.0,
            "flow_rate_ml_h": 40.0,
            "status": "NORMAL",
        },
        "ecg": {
            "rhythm": "VENTRICULAR_FIBRILLATION",
            "status": "CRITICAL",
        },
    },
    "EMERGENCY": {
        "title": "Station Emergency / Code Blue Alarm",
        "description": "Bedside acute emergency call for immediate resuscitation team dispatch.",
        "target_patient_id": "P001",
        "event_type": "EMERGENCY",
        "severity": "CRITICAL",
        "parameter": "emergency_code_blue",
        "message": "Bedside EMERGENCY Code Blue trigger activated for immediate clinical resuscitation",
        "vitals": {
            "heart_rate": 180.0,
            "blood_pressure": "70/40",
            "systolic_bp": 70.0,
            "diastolic_bp": 40.0,
            "spo2": 75.0,
            "respiratory_rate": 8.0,
            "temperature": 36.0,
        },
    },
}
