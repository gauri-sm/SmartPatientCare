"""
Thresholds & Clinical Logic for Sandra Emergency Alerts
=======================================================
Evaluates raw parameter values against clinical boundaries.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from typing import Tuple, Optional
from shared.constants.thresholds import (
    VITALS_THRESHOLDS,
    IV_DRIP_THRESHOLDS,
    ECG_NORMAL_RHYTHM,
    ECG_ABNORMAL_RHYTHMS,
)
from sandra.emergency_alerts.src.models import SeverityLevel


def evaluate_heart_rate(hr: float) -> Tuple[Optional[SeverityLevel], str, str]:
    """
    Evaluates heart rate.
    Returns: (severity, message, expected_range)
    """
    cfg = VITALS_THRESHOLDS["heart_rate"]
    expected = cfg["expected_range"]
    if hr >= cfg["critical_high"]:
        return SeverityLevel.CRITICAL, f"Severe tachycardia: Heart rate {hr:.0f} bpm exceeds critical limit (> {cfg['critical_high']} bpm)", expected
    if hr <= cfg["critical_low"]:
        return SeverityLevel.CRITICAL, f"Severe bradycardia: Heart rate {hr:.0f} bpm below critical threshold (< {cfg['critical_low']} bpm)", expected
    if hr > cfg["normal_max"]:
        return SeverityLevel.WARNING, f"Elevated heart rate: {hr:.0f} bpm (normal: {expected})", expected
    if hr < cfg["normal_min"]:
        return SeverityLevel.WARNING, f"Low heart rate: {hr:.0f} bpm (normal: {expected})", expected
    return None, "Heart rate normal", expected


def evaluate_spo2(spo2: float) -> Tuple[Optional[SeverityLevel], str, str]:
    """
    Evaluates oxygen saturation.
    Returns: (severity, message, expected_range)
    """
    cfg = VITALS_THRESHOLDS["spo2"]
    expected = cfg["expected_range"]
    if spo2 < cfg["critical_low"]:
        return SeverityLevel.CRITICAL, f"Critical hypoxia: SpO2 {spo2:.0f}% is dangerously low (< {cfg['critical_low']}%)", expected
    if spo2 < cfg["normal_min"]:
        return SeverityLevel.WARNING, f"Sub-optimal oxygen saturation: SpO2 {spo2:.0f}% (normal: {expected})", expected
    return None, "Oxygen saturation normal", expected


def evaluate_blood_pressure(systolic: float, diastolic: float) -> Tuple[Optional[SeverityLevel], str, str]:
    """
    Evaluates blood pressure.
    Returns: (severity, message, expected_range)
    """
    sys_cfg = VITALS_THRESHOLDS["systolic_bp"]
    dia_cfg = VITALS_THRESHOLDS["diastolic_bp"]
    expected = "90-120 / 60-80 mmHg"

    if systolic >= sys_cfg["critical_high"] or diastolic >= dia_cfg["critical_high"]:
        return SeverityLevel.CRITICAL, f"Hypertensive crisis: Blood pressure {systolic:.0f}/{diastolic:.0f} mmHg", expected
    if systolic <= sys_cfg["critical_low"] or diastolic <= dia_cfg["critical_low"]:
        return SeverityLevel.CRITICAL, f"Severe hypotension: Blood pressure {systolic:.0f}/{diastolic:.0f} mmHg", expected
    if systolic > sys_cfg["normal_max"] or diastolic > dia_cfg["normal_max"]:
        return SeverityLevel.WARNING, f"Elevated blood pressure: {systolic:.0f}/{diastolic:.0f} mmHg", expected
    return None, "Blood pressure normal", expected


def evaluate_temperature(temp: float) -> Tuple[Optional[SeverityLevel], str, str]:
    """
    Evaluates body temperature.
    Returns: (severity, message, expected_range)
    """
    cfg = VITALS_THRESHOLDS["temperature"]
    expected = cfg["expected_range"]
    if temp >= cfg["critical_high"]:
        return SeverityLevel.CRITICAL, f"Hyperthermia / high-grade fever: Temperature {temp:.1f} °C", expected
    if temp <= cfg["critical_low"]:
        return SeverityLevel.CRITICAL, f"Hypothermia alert: Temperature {temp:.1f} °C", expected
    if temp > cfg["normal_max"]:
        return SeverityLevel.WARNING, f"Mild pyrexia: Temperature {temp:.1f} °C (normal: {expected})", expected
    return None, "Temperature normal", expected


def evaluate_respiratory_rate(rr: float) -> Tuple[Optional[SeverityLevel], str, str]:
    """
    Evaluates respiratory rate.
    Returns: (severity, message, expected_range)
    """
    cfg = VITALS_THRESHOLDS["respiratory_rate"]
    expected = cfg["expected_range"]
    if rr >= cfg["critical_high"] or rr <= cfg["critical_low"]:
        return SeverityLevel.CRITICAL, f"Critical respiratory rate: {rr:.0f} breaths/min", expected
    if rr > cfg["normal_max"] or rr < cfg["normal_min"]:
        return SeverityLevel.WARNING, f"Abnormal respiratory rate: {rr:.0f} breaths/min (normal: {expected})", expected
    return None, "Respiratory rate normal", expected


def evaluate_iv_drip(volume_ml: float, flow_rate_ml_h: float) -> Tuple[Optional[SeverityLevel], str, str]:
    """
    Evaluates IV drip levels.
    Returns: (severity, message, expected_range)
    """
    expected = "> 100 ml"
    if volume_ml <= IV_DRIP_THRESHOLDS["volume_depleted_ml"]:
        return SeverityLevel.CRITICAL, f"IV Drip Empty: Infusion bag depleted ({volume_ml:.0f} ml remaining). Replace immediately.", expected
    if volume_ml <= IV_DRIP_THRESHOLDS["volume_critical_empty_ml"]:
        return SeverityLevel.CRITICAL, f"IV Drip Critically Low: Only {volume_ml:.0f} ml remaining. Prepare replacement.", expected
    if volume_ml <= IV_DRIP_THRESHOLDS["volume_low_warning_ml"]:
        return SeverityLevel.WARNING, f"IV Drip Near-Empty: {volume_ml:.0f} ml remaining.", expected
    return None, "IV drip level adequate", expected


def evaluate_ecg(rhythm: str) -> Tuple[Optional[SeverityLevel], str, str]:
    """
    Evaluates ECG rhythm.
    Returns: (severity, message, expected_range)
    """
    expected = "Normal Sinus Rhythm"
    rhythm_clean = rhythm.strip().upper()
    if rhythm_clean == ECG_NORMAL_RHYTHM:
        return None, "Normal sinus rhythm", expected
    if rhythm_clean in ECG_ABNORMAL_RHYTHMS:
        info = ECG_ABNORMAL_RHYTHMS[rhythm_clean]
        sev = SeverityLevel(info["severity"])
        return sev, f"ECG Alert: {info['message']} ({rhythm})", expected
    # Fallback for unknown abnormal rhythm
    return SeverityLevel.WARNING, f"ECG Warning: Irregular rhythm detected ({rhythm})", expected
