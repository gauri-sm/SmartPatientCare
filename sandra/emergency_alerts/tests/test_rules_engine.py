"""
Unit tests for Sandra's Emergency Alerts Rules Engine
"""

import pytest
from sandra.emergency_alerts.src.rules_engine import RulesEngine
from sandra.emergency_alerts.src.models import SeverityLevel


@pytest.fixture
def engine():
    return RulesEngine()


def test_normal_vitals_no_alerts(engine):
    vitals = {
        "heart_rate": 75,
        "spo2": 98,
        "systolic_bp": 115,
        "diastolic_bp": 75,
        "temperature": 36.8,
        "respiratory_rate": 16,
    }
    events = engine.evaluate_vitals("P001", "ROOM101", vitals)
    assert len(events) == 0


def test_critical_low_spo2(engine):
    vitals = {"spo2": 82}
    events = engine.evaluate_vitals("P002", "ROOM102", vitals)
    assert len(events) == 1
    ev = events[0]
    assert ev.parameter == "spo2"
    assert ev.severity == SeverityLevel.CRITICAL
    assert ev.value == 82
    assert "hypoxia" in ev.message.lower()


def test_tachycardia_critical(engine):
    vitals = {"heart_rate": 155}
    events = engine.evaluate_vitals("P004", "ROOM104", vitals)
    assert len(events) == 1
    assert events[0].parameter == "heart_rate"
    assert events[0].severity == SeverityLevel.CRITICAL
    assert "tachycardia" in events[0].message.lower()


def test_bradycardia_critical(engine):
    vitals = {"heart_rate": 40}
    events = engine.evaluate_vitals("P001", "ROOM101", vitals)
    assert len(events) == 1
    assert events[0].severity == SeverityLevel.CRITICAL
    assert "bradycardia" in events[0].message.lower()


def test_hypertensive_crisis(engine):
    vitals = {"systolic_bp": 190, "diastolic_bp": 120}
    events = engine.evaluate_vitals("P004", "ROOM104", vitals)
    assert len(events) == 1
    assert events[0].parameter == "blood_pressure"
    assert events[0].severity == SeverityLevel.CRITICAL
    assert "hypertensive crisis" in events[0].message.lower()


def test_high_temperature(engine):
    vitals = {"temperature": 39.8}
    events = engine.evaluate_vitals("P002", "ROOM102", vitals)
    assert len(events) == 1
    assert events[0].parameter == "temperature"
    assert events[0].severity == SeverityLevel.CRITICAL


def test_iv_drip_empty(engine):
    events = engine.evaluate_iv_drip("P001", "ROOM101", volume_remaining_ml=0.0, flow_rate_ml_h=0.0)
    assert len(events) == 1
    assert events[0].parameter == "iv_drip_volume"
    assert events[0].severity == SeverityLevel.CRITICAL
    assert "empty" in events[0].message.lower()


def test_iv_drip_low_warning(engine):
    events = engine.evaluate_iv_drip("P003", "ROOM103", volume_remaining_ml=45.0, flow_rate_ml_h=100.0)
    assert len(events) == 1
    assert events[0].parameter == "iv_drip_volume"
    assert events[0].severity == SeverityLevel.WARNING


def test_ecg_ventricular_fibrillation(engine):
    events = engine.evaluate_ecg("P004", "ROOM104", rhythm="VENTRICULAR_FIBRILLATION")
    assert len(events) == 1
    assert events[0].parameter == "ecg_rhythm"
    assert events[0].severity == SeverityLevel.CRITICAL
    assert "ventricular fibrillation" in events[0].message.lower()


def test_graceful_handling_of_malformed_data(engine):
    # Should not crash on invalid strings or none values
    vitals = {
        "heart_rate": "invalid_hr",
        "spo2": None,
        "blood_pressure": "corrupted/bp/text",
        "temperature": "not_a_num",
    }
    events = engine.evaluate_vitals("P001", "ROOM101", vitals)
    assert len(events) == 0
