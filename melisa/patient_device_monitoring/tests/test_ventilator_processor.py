"""Unit tests for VentilatorProcessor module.

Verifies:
- Normal ventilator monitoring telemetry (INFO severity)
- Acute clinical advisory alerts (HIGH_PRESSURE, CIRCUIT_DISCONNECT, APNEA)
- Required schema contract conformance
- Zero CCTV/YOLO dependencies
- Configurable threshold support
"""

import json
try:
    import pytest
except ImportError:
    pytest = None

from melisa.patient_device_monitoring.src.ventilator_processor import (
    VentilatorProcessor,
    VentilatorThresholdConfig,
    default_ventilator_processor,
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
    assert event["source"] == "ventilator_monitor"
    assert event["severity"] in ("INFO", "LOW", "MEDIUM", "WARNING", "HIGH", "CRITICAL")

    # Verify no CCTV-specific keys are forced into ventilator telemetry
    cctv_keys = ["camera_id", "video_source", "bounding_box", "yolo_confidence"]
    for c_key in cctv_keys:
        assert c_key not in event, f"Ventilator event must not contain CCTV field: {c_key}"

    # Verify JSON serializability
    json_str = json.dumps(event)
    assert len(json_str) > 0


def test_normal_telemetry():
    """Verify normal ventilator telemetry produces INFO severity and VENTILATOR_TELEMETRY event_type."""
    processor = VentilatorProcessor()
    event = processor.evaluate_telemetry("P002", "ROOM102", pip=22.0, peep=6.0, tidal_volume=480.0)

    assert_event_schema_contract(event)
    assert event["event_type"] == "VENTILATOR_TELEMETRY"
    assert event["severity"] == "INFO"
    assert event["parameter"] == "peak_inspiratory_pressure"
    assert event["value"] == 22.0
    assert event["unit"] == "cmH2O"
    assert "PIP 22.0 cmH2O" in event["message"]


def test_high_pressure_alert():
    """Verify elevated PIP (>= 35.0 cmH2O) generates CRITICAL VENTILATOR_ALERT."""
    processor = VentilatorProcessor()

    # Elevated PIP
    event = processor.evaluate_pip("P002", "ROOM102", pip=41.5)
    assert_event_schema_contract(event)
    assert event["event_type"] == "VENTILATOR_ALERT"
    assert event["severity"] == "CRITICAL"
    assert event["parameter"] == "peak_inspiratory_pressure"
    assert event["value"] == 41.5
    assert event["unit"] == "cmH2O"
    assert "Peak Inspiratory Pressure elevated" in event["message"]

    # Normal PIP (< 35.0 cmH2O)
    normal_pip = processor.evaluate_pip("P002", "ROOM102", pip=21.5)
    assert_event_schema_contract(normal_pip)
    assert normal_pip["event_type"] == "VENTILATOR_TELEMETRY"
    assert normal_pip["severity"] == "INFO"
    assert normal_pip["value"] == 21.5


def test_circuit_disconnect_alert():
    """Verify low PEEP (<= 2.0 cmH2O) generates CRITICAL VENTILATOR_ALERT."""
    processor = VentilatorProcessor()

    # Low PEEP alert
    event = processor.evaluate_peep("P002", "ROOM102", peep=1.2)
    assert_event_schema_contract(event)
    assert event["event_type"] == "VENTILATOR_ALERT"
    assert event["severity"] == "CRITICAL"
    assert event["parameter"] == "peep"
    assert event["value"] == 1.2
    assert event["unit"] == "cmH2O"
    assert "Low PEEP" in event["message"]

    # Normal PEEP
    normal_peep = processor.evaluate_peep("P002", "ROOM102", peep=6.0)
    assert_event_schema_contract(normal_peep)
    assert normal_peep["event_type"] == "VENTILATOR_TELEMETRY"
    assert normal_peep["severity"] == "INFO"
    assert normal_peep["value"] == 6.0


def test_apnea_alert():
    """Verify apnea alarm generates CRITICAL VENTILATOR_ALERT."""
    processor = VentilatorProcessor()

    # Apnea detected
    event = processor.evaluate_apnea("P004", "ROOM104", apnea_detected=True)
    assert_event_schema_contract(event)
    assert event["event_type"] == "VENTILATOR_ALERT"
    assert event["severity"] == "CRITICAL"
    assert event["parameter"] == "apnea_alarm"
    assert event["value"] is True
    assert event["unit"] == "status"
    assert "Apnea detected" in event["message"]

    # Apnea resolved / normal breathing
    normal_breath = processor.evaluate_apnea("P004", "ROOM104", apnea_detected=False)
    assert_event_schema_contract(normal_breath)
    assert normal_breath["event_type"] == "VENTILATOR_TELEMETRY"
    assert normal_breath["severity"] == "INFO"
    assert normal_breath["value"] is False


def test_scenarios():
    """Verify scenario dispatch matching ventilator simulator options."""
    processor = VentilatorProcessor()

    # HIGH_PRESSURE scenario
    evt_hp = processor.evaluate_scenario("P002", "ROOM102", "HIGH_PRESSURE")
    assert_event_schema_contract(evt_hp)
    assert evt_hp["event_type"] == "VENTILATOR_ALERT"
    assert evt_hp["severity"] == "CRITICAL"
    assert evt_hp["parameter"] == "peak_inspiratory_pressure"
    assert evt_hp["value"] == 41.5

    # CIRCUIT_DISCONNECT scenario
    evt_cd = processor.evaluate_scenario("P002", "ROOM102", "CIRCUIT_DISCONNECT")
    assert_event_schema_contract(evt_cd)
    assert evt_cd["event_type"] == "VENTILATOR_ALERT"
    assert evt_cd["severity"] == "CRITICAL"
    assert evt_cd["parameter"] == "peep"
    assert evt_cd["value"] == 1.2

    # APNEA scenario
    evt_ap = processor.evaluate_scenario("P004", "ROOM104", "APNEA")
    assert_event_schema_contract(evt_ap)
    assert evt_ap["event_type"] == "VENTILATOR_ALERT"
    assert evt_ap["severity"] == "CRITICAL"
    assert evt_ap["parameter"] == "apnea_alarm"
    assert evt_ap["value"] is True

    # NORMAL scenario
    evt_norm = processor.evaluate_scenario("P002", "ROOM102", "NORMAL")
    assert_event_schema_contract(evt_norm)
    assert evt_norm["event_type"] == "VENTILATOR_TELEMETRY"
    assert evt_norm["severity"] == "INFO"


def test_custom_thresholds():
    """Verify custom ventilator threshold configuration."""
    custom_cfg = VentilatorThresholdConfig(
        pip_threshold=45.0,     # Higher PIP threshold
        peep_min_threshold=1.0  # Lower PEEP disconnect threshold
    )
    custom_proc = VentilatorProcessor(thresholds=custom_cfg)

    # 40.0 cmH2O is under custom 45.0 threshold -> INFO
    evt_pip = custom_proc.evaluate_pip("P002", "ROOM102", 40.0)
    assert evt_pip["event_type"] == "VENTILATOR_TELEMETRY"
    assert evt_pip["severity"] == "INFO"

    # 1.5 cmH2O is above custom 1.0 threshold -> INFO
    evt_peep = custom_proc.evaluate_peep("P002", "ROOM102", 1.5)
    assert evt_peep["event_type"] == "VENTILATOR_TELEMETRY"
    assert evt_peep["severity"] == "INFO"
