"""Comprehensive unit tests for VitalsProcessor module.

Verifies:
- Normal vital values
- Abnormal values (LOW_SPO2, ABNORMAL_HEART_RATE, ABNORMAL_BP, ABNORMAL_TEMPERATURE)
- NORMAL -> ABNORMAL threshold transitions
- Required fields and contract conformance
- Zero CCTV/YOLO dependency
- Configurable threshold support
"""

import json
try:
    import pytest
except ImportError:
    pytest = None
from melisa.patient_device_monitoring.src.vitals_processor import (
    VitalsProcessor,
    VitalsThresholdConfig,
    default_vitals_processor,
)


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

    # Verify no CCTV-specific keys are forced into medical-device telemetry
    cctv_keys = ["camera_id", "video_source", "bounding_box", "yolo_confidence"]
    for c_key in cctv_keys:
        assert c_key not in event, f"Device event must not contain CCTV field: {c_key}"

    # Verify JSON serializability for HTTP/API transmission
    json_str = json.dumps(event)
    assert len(json_str) > 0


def test_normal_vitals():
    """Verify normal vital readings produce INFO severity and VITAL_SIGN event_type."""
    processor = VitalsProcessor()

    # SpO2 normal
    e_spo2 = processor.evaluate_spo2("P001", "ROOM101", 98.0)
    assert_event_schema_contract(e_spo2)
    assert e_spo2["event_type"] == "VITAL_SIGN"
    assert e_spo2["severity"] == "INFO"
    assert e_spo2["value"] == 98.0

    # Heart rate normal
    e_hr = processor.evaluate_heart_rate("P001", "ROOM101", 75.0)
    assert_event_schema_contract(e_hr)
    assert e_hr["event_type"] == "VITAL_SIGN"
    assert e_hr["severity"] == "INFO"

    # BP normal
    e_bp = processor.evaluate_blood_pressure("P001", "ROOM101", "120/80")
    assert_event_schema_contract(e_bp)
    assert e_bp["event_type"] == "VITAL_SIGN"
    assert e_bp["severity"] == "INFO"

    # Temp normal
    e_temp = processor.evaluate_temperature("P001", "ROOM101", 36.8)
    assert_event_schema_contract(e_temp)
    assert e_temp["event_type"] == "VITAL_SIGN"
    assert e_temp["severity"] == "INFO"

    # Respiratory rate normal (12-20 breaths/min)
    e_rr = processor.evaluate_respiratory_rate("P001", "ROOM101", 16.0)
    assert_event_schema_contract(e_rr)
    assert e_rr["event_type"] == "VITAL_SIGN"
    assert e_rr["severity"] == "INFO"
    assert e_rr["parameter"] == "respiratory_rate"
    assert e_rr["value"] == 16.0
    assert e_rr["unit"] == "breaths/min"


def test_abnormal_low_spo2():
    """Verify LOW_SPO2 event generation and severity levels."""
    processor = VitalsProcessor()

    # Critical SpO2 (<= 90%)
    crit = processor.evaluate_spo2("P002", "ROOM102", 88.0)
    assert_event_schema_contract(crit)
    assert crit["event_type"] == "LOW_SPO2"
    assert crit["severity"] == "CRITICAL"
    assert crit["patient_id"] == "P002"
    assert crit["room_id"] == "ROOM102"

    # High / Warning SpO2 (91% - 94%)
    high = processor.evaluate_spo2("P002", "ROOM102", 92.0)
    assert_event_schema_contract(high)
    assert high["event_type"] == "LOW_SPO2"
    assert high["severity"] == "HIGH"


def test_abnormal_heart_rate():
    """Verify ABNORMAL_HEART_RATE for tachycardia and bradycardia."""
    processor = VitalsProcessor()

    # Tachycardia critical (> 120)
    crit_tach = processor.evaluate_heart_rate("P004", "ROOM104", 128.0)
    assert_event_schema_contract(crit_tach)
    assert crit_tach["event_type"] == "ABNORMAL_HEART_RATE"
    assert crit_tach["severity"] == "CRITICAL"

    # Tachycardia high (101 - 120)
    high_tach = processor.evaluate_heart_rate("P004", "ROOM104", 110.0)
    assert_event_schema_contract(high_tach)
    assert high_tach["event_type"] == "ABNORMAL_HEART_RATE"
    assert high_tach["severity"] == "HIGH"

    # Bradycardia high (< 60)
    high_brady = processor.evaluate_heart_rate("P001", "ROOM101", 52.0)
    assert_event_schema_contract(high_brady)
    assert high_brady["event_type"] == "ABNORMAL_HEART_RATE"
    assert high_brady["severity"] == "HIGH"


def test_abnormal_bp():
    """Verify ABNORMAL_BP for hypertensive crisis and hypertension."""
    processor = VitalsProcessor()

    # Hypertensive crisis (>= 180 / 120)
    crit_bp = processor.evaluate_blood_pressure("P004", "ROOM104", "185/125")
    assert_event_schema_contract(crit_bp)
    assert crit_bp["event_type"] == "ABNORMAL_BP"
    assert crit_bp["severity"] == "CRITICAL"

    # Hypertension high (>= 140 / 90)
    high_bp = processor.evaluate_blood_pressure("P004", "ROOM104", "150/95")
    assert_event_schema_contract(high_bp)
    assert high_bp["event_type"] == "ABNORMAL_BP"
    assert high_bp["severity"] == "HIGH"


def test_abnormal_temperature():
    """Verify ABNORMAL_TEMPERATURE for fever and hyperpyrexia."""
    processor = VitalsProcessor()

    # Fever (>= 38.0) -> MEDIUM
    fever = processor.evaluate_temperature("P002", "ROOM102", 38.5)
    assert_event_schema_contract(fever)
    assert fever["event_type"] == "ABNORMAL_TEMPERATURE"
    assert fever["severity"] == "MEDIUM"

    # Hyperpyrexia (>= 39.5) -> HIGH
    hyper = processor.evaluate_temperature("P002", "ROOM102", 39.8)
    assert_event_schema_contract(hyper)
    assert hyper["event_type"] == "ABNORMAL_TEMPERATURE"
    assert hyper["severity"] == "HIGH"


def test_threshold_transitions():
    """Test NORMAL -> ABNORMAL progression through stepwise values."""
    processor = VitalsProcessor()

    # SpO2 descending: 98 -> 97 -> 96 -> 94 -> 92 -> 90 -> 88
    spo2_steps = [98.0, 97.0, 96.0, 94.0, 92.0, 90.0, 88.0]
    events = [processor.evaluate_spo2("P001", "ROOM101", s) for s in spo2_steps]

    # Initial steps should be INFO / normal
    assert events[0]["severity"] == "INFO"
    assert events[1]["severity"] == "INFO"
    assert events[2]["severity"] == "INFO"

    # 94% & 92% trigger HIGH LOW_SPO2
    assert events[3]["event_type"] == "LOW_SPO2"
    assert events[3]["severity"] == "HIGH"
    assert events[4]["event_type"] == "LOW_SPO2"
    assert events[4]["severity"] == "HIGH"

    # 90% and 88% trigger CRITICAL LOW_SPO2
    assert events[5]["event_type"] == "LOW_SPO2"
    assert events[5]["severity"] == "CRITICAL"
    assert events[6]["event_type"] == "LOW_SPO2"
    assert events[6]["severity"] == "CRITICAL"


def test_custom_configurable_thresholds():
    """Test that custom thresholds can be supplied and honored."""
    custom_cfg = VitalsThresholdConfig(
        spo2_critical=85.0,  # Custom: only critical below 85
        spo2_high=90.0,      # Custom: warning below 90
        hr_high=115.0        # Custom: warning above 115
    )
    custom_processor = VitalsProcessor(thresholds=custom_cfg)

    # 88% SpO2 with custom config should be HIGH (not CRITICAL)
    evt = custom_processor.evaluate_spo2("P001", "ROOM101", 88.0)
    assert evt["event_type"] == "LOW_SPO2"
    assert evt["severity"] == "HIGH"

    # 110 bpm with custom config should be INFO (not HIGH, since threshold is 115)
    evt_hr = custom_processor.evaluate_heart_rate("P001", "ROOM101", 110.0)
    assert evt_hr["event_type"] == "VITAL_SIGN"
    assert evt_hr["severity"] == "INFO"


def test_abnormal_respiratory_rate_high():
    """Verify ABNORMAL_RESPIRATORY_RATE for elevated rates (tachypnea)."""
    processor = VitalsProcessor()

    # High / warning tachypnea (> 20 breaths/min, e.g. 24)
    high_rr = processor.evaluate_respiratory_rate("P002", "ROOM102", 24.0)
    assert_event_schema_contract(high_rr)
    assert high_rr["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert high_rr["severity"] == "HIGH"
    assert high_rr["parameter"] == "respiratory_rate"
    assert high_rr["value"] == 24.0
    assert high_rr["unit"] == "breaths/min"

    # Critical tachypnea (>= 30 breaths/min, e.g. 32)
    crit_rr = processor.evaluate_respiratory_rate("P002", "ROOM102", 32.0)
    assert_event_schema_contract(crit_rr)
    assert crit_rr["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert crit_rr["severity"] == "CRITICAL"
    assert crit_rr["parameter"] == "respiratory_rate"
    assert crit_rr["value"] == 32.0


def test_abnormal_respiratory_rate_low():
    """Verify ABNORMAL_RESPIRATORY_RATE for depressed rates (bradypnea)."""
    processor = VitalsProcessor()

    # Low / warning bradypnea (< 12 breaths/min, e.g. 10)
    low_rr = processor.evaluate_respiratory_rate("P001", "ROOM101", 10.0)
    assert_event_schema_contract(low_rr)
    assert low_rr["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert low_rr["severity"] == "HIGH"
    assert low_rr["parameter"] == "respiratory_rate"
    assert low_rr["value"] == 10.0
    assert low_rr["unit"] == "breaths/min"

    # Critical bradypnea (<= 8 breaths/min, e.g. 6)
    crit_low_rr = processor.evaluate_respiratory_rate("P001", "ROOM101", 6.0)
    assert_event_schema_contract(crit_low_rr)
    assert crit_low_rr["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert crit_low_rr["severity"] == "CRITICAL"
    assert crit_low_rr["parameter"] == "respiratory_rate"
    assert crit_low_rr["value"] == 6.0


def test_respiratory_rate_batch_processing():
    """Verify batch evaluation of vital signs including respiratory_rate."""
    processor = VitalsProcessor()

    vitals_batch = {
        "spo2": 98,
        "heart_rate": 75,
        "blood_pressure": "120/80",
        "temperature": 36.8,
        "respiratory_rate": 16
    }
    events = processor.evaluate_all("P001", "ROOM101", vitals_batch)
    assert len(events) == 5

    # Find and verify the respiratory_rate event
    rr_event = next(e for e in events if e["parameter"] == "respiratory_rate")
    assert_event_schema_contract(rr_event)
    assert rr_event["event_type"] == "VITAL_SIGN"
    assert rr_event["severity"] == "INFO"
    assert rr_event["value"] == 16.0
    assert rr_event["unit"] == "breaths/min"
    assert rr_event["patient_id"] == "P001"
    assert rr_event["room_id"] == "ROOM101"

    # Abnormal batch test
    abnormal_batch = {
        "spo2": 88,
        "heart_rate": 130,
        "blood_pressure": "190/125",
        "temperature": 39.8,
        "respiratory_rate": 34
    }
    abnormal_events = processor.evaluate_all("P002", "ROOM102", abnormal_batch)
    assert len(abnormal_events) == 5
    rr_abnormal = next(e for e in abnormal_events if e["parameter"] == "respiratory_rate")
    assert_event_schema_contract(rr_abnormal)
    assert rr_abnormal["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert rr_abnormal["severity"] == "CRITICAL"


def test_respiratory_rate_threshold_transitions():
    """Verify NORMAL -> HIGH -> CRITICAL threshold transitions for respiratory rate."""
    processor = VitalsProcessor()

    # Stepwise increasing: 16 -> 18 -> 20 -> 22 -> 28 -> 30 -> 35
    rr_asc = [16.0, 18.0, 20.0, 22.0, 28.0, 30.0, 35.0]
    asc_events = [processor.evaluate_respiratory_rate("P001", "ROOM101", r) for r in rr_asc]

    # Normal range (<= 20) -> INFO
    assert asc_events[0]["severity"] == "INFO"
    assert asc_events[1]["severity"] == "INFO"
    assert asc_events[2]["severity"] == "INFO"

    # High tachypnea (20 < rr < 30) -> HIGH
    assert asc_events[3]["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert asc_events[3]["severity"] == "HIGH"
    assert asc_events[4]["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert asc_events[4]["severity"] == "HIGH"

    # Critical tachypnea (rr >= 30) -> CRITICAL
    assert asc_events[5]["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert asc_events[5]["severity"] == "CRITICAL"
    assert asc_events[6]["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert asc_events[6]["severity"] == "CRITICAL"

    # Stepwise decreasing: 16 -> 14 -> 12 -> 10 -> 8 -> 5
    rr_desc = [16.0, 14.0, 12.0, 10.0, 8.0, 5.0]
    desc_events = [processor.evaluate_respiratory_rate("P001", "ROOM101", r) for r in rr_desc]

    # Normal range (>= 12) -> INFO
    assert desc_events[0]["severity"] == "INFO"
    assert desc_events[1]["severity"] == "INFO"
    assert desc_events[2]["severity"] == "INFO"

    # High bradypnea (8 < rr < 12) -> HIGH
    assert desc_events[3]["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert desc_events[3]["severity"] == "HIGH"

    # Critical bradypnea (rr <= 8) -> CRITICAL
    assert desc_events[4]["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert desc_events[4]["severity"] == "CRITICAL"
    assert desc_events[5]["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
    assert desc_events[5]["severity"] == "CRITICAL"
