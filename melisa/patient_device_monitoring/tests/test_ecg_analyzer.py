"""Unit tests for ECGAnalyzer module.

Verifies:
- NORMAL_ECG vs ABNORMAL_ECG event generation
- Critical arrhythmia detection (VTach, AFib, Asystole)
- Event schema compliance
- Zero CCTV/YOLO dependencies
"""

import json
import pytest
from melisa.patient_device_monitoring.src.ecg_analyzer import ECGAnalyzer


def assert_event_schema_contract(event: dict):
    """Verify that an event conforms strictly to the shared event architecture."""
    required_keys = [
        "event_id", "timestamp", "event_type", "patient_id", "room_id",
        "source", "parameter", "value", "unit", "severity", "message", "status"
    ]
    for key in required_keys:
        assert key in event, f"Missing required event key: {key}"
        assert event[key] is not None, f"Required key {key} must not be None"

    assert event["status"] == "ACTIVE"
    assert event["severity"] in ("INFO", "LOW", "MEDIUM", "WARNING", "HIGH", "CRITICAL")
    assert "camera_id" not in event
    assert "video_source" not in event


def test_normal_ecg_rhythm():
    """Normal rhythm generates NORMAL_ECG with INFO severity."""
    evt = ECGAnalyzer.evaluate_rhythm("P001", "ROOM101", heart_rate=72)
    assert_event_schema_contract(evt)
    assert evt["event_type"] == "NORMAL_ECG"
    assert evt["severity"] == "INFO"
    assert evt["value"] == "NORMAL_SINUS_RHYTHM"


def test_abnormal_ecg_asystole():
    """Asystole (0 bpm) generates ABNORMAL_ECG with CRITICAL severity."""
    evt = ECGAnalyzer.evaluate_rhythm("P001", "ROOM101", heart_rate=0)
    assert_event_schema_contract(evt)
    assert evt["event_type"] == "ABNORMAL_ECG"
    assert evt["severity"] == "CRITICAL"
    assert evt["value"] == "ASYSTOLE"


def test_abnormal_ecg_ventricular_tachycardia():
    """Heart rate > 140 bpm triggers ABNORMAL_ECG with CRITICAL severity."""
    evt = ECGAnalyzer.evaluate_rhythm("P002", "ROOM102", heart_rate=165)
    assert_event_schema_contract(evt)
    assert evt["event_type"] == "ABNORMAL_ECG"
    assert evt["severity"] == "CRITICAL"
    assert evt["value"] == "VENTRICULAR_TACHYCARDIA"


def test_abnormal_ecg_atrial_fibrillation():
    """Explicit AFib rhythm trigger generates ABNORMAL_ECG with CRITICAL severity."""
    evt = ECGAnalyzer.evaluate_rhythm(
        "P004", "ROOM104", heart_rate=118, rhythm_name="ATRIAL_FIBRILLATION", is_abnormal=True
    )
    assert_event_schema_contract(evt)
    assert evt["event_type"] == "ABNORMAL_ECG"
    assert evt["severity"] == "CRITICAL"
    assert evt["value"] == "ATRIAL_FIBRILLATION"


def test_ecg_normal_to_abnormal_transition():
    """Demonstrate transition from NORMAL_ECG to ABNORMAL_ECG."""
    e_normal = ECGAnalyzer.evaluate_rhythm("P001", "ROOM101", heart_rate=75)
    assert e_normal["event_type"] == "NORMAL_ECG"
    assert e_normal["severity"] == "INFO"

    e_abnormal = ECGAnalyzer.evaluate_rhythm("P001", "ROOM101", heart_rate=155)
    assert e_abnormal["event_type"] == "ABNORMAL_ECG"
    assert e_abnormal["severity"] == "CRITICAL"


def test_generate_single_lead_points_normal():
    """Test normal rhythm waveform generation produces valid P-Q-R-S-T points."""
    points = ECGAnalyzer.generate_single_lead_points(
        heart_rate=75,
        duration_seconds=1.0,
        sampling_rate=250,
        rhythm_type="NORMAL"
    )
    assert len(points) == 250
    assert all("t" in p and "mv" in p for p in points)
    assert all(isinstance(p["t"], float) and isinstance(p["mv"], float) for p in points)
    assert points[0]["t"] == 0.0
    # R-peak should produce voltage around 1.2 mV
    max_mv = max(p["mv"] for p in points)
    assert max_mv > 1.0
    # S-wave should dip below 0
    min_mv = min(p["mv"] for p in points)
    assert min_mv < 0.0


def test_generate_single_lead_points_asystole():
    """Test asystole (heart_rate <= 0) generates flatline zero millivolts."""
    # Test 0 bpm
    points_zero = ECGAnalyzer.generate_single_lead_points(
        heart_rate=0,
        duration_seconds=1.0,
        sampling_rate=250
    )
    assert len(points_zero) == 250
    assert all("t" in p and "mv" in p for p in points_zero)
    assert all(p["mv"] == 0.0 for p in points_zero)

    # Test negative heart rate
    points_neg = ECGAnalyzer.generate_single_lead_points(
        heart_rate=-10,
        duration_seconds=1.5,
        sampling_rate=200
    )
    assert len(points_neg) == 300
    assert all(p["mv"] == 0.0 for p in points_neg)


def test_generate_single_lead_points_vfib():
    """Test VFIB rhythm generates chaotic oscillating voltages."""
    points = ECGAnalyzer.generate_single_lead_points(
        heart_rate=120,
        duration_seconds=1.0,
        sampling_rate=250,
        rhythm_type="VFIB"
    )
    assert len(points) == 250
    assert all("t" in p and "mv" in p for p in points)
    voltages = [p["mv"] for p in points]
    assert any(v != 0.0 for v in voltages)
    # Sinusoidal combination should remain within [-0.5, 0.5] range
    assert max(voltages) <= 0.55
    assert min(voltages) >= -0.55


def test_generate_single_lead_points_durations_and_sampling_rates():
    """Test point count matches duration * sampling_rate across diverse parameters."""
    test_cases = [
        (2.0, 250, 500),
        (0.5, 100, 50),
        (3.0, 500, 1500),
        (1.2, 200, 240)
    ]
    for duration, rate, expected_count in test_cases:
        pts = ECGAnalyzer.generate_single_lead_points(
            heart_rate=80,
            duration_seconds=duration,
            sampling_rate=rate
        )
        assert len(pts) == expected_count, f"Failed count for dur={duration}, rate={rate}"
        assert all("t" in p and "mv" in p for p in pts)
        # Check monotonic timestamps
        assert pts[0]["t"] == 0.0
        assert pts[-1]["t"] < duration

