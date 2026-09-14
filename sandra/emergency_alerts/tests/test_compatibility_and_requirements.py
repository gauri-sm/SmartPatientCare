"""
Comprehensive Compatibility and Alert Engine Tests for Sandra
==============================================================
Validates all requirements specified for Sandra's centralized Alert Engine:
1. FALL_DETECTED
2. LOW_SPO2
3. DRIP_FINISHED
4. EMERGENCY
5. Event normalization
6. Severity classification
7. ACTIVE state
8. ACKNOWLEDGED state
9. RESOLVED state
10. Preservation of optional CCTV evidence fields (video_source, camera_id, evidence_type)
11. Acceptance of non-CCTV events without video_source/camera_id/evidence_type
12. Duplicate prevention for repeated CCTV frames
"""

import pytest
from sandra.emergency_alerts.src.models import (
    SmartPatientCareEvent,
    SeverityLevel,
    AlertStatus,
    EventType,
)
from sandra.emergency_alerts.src.rules_engine import RulesEngine, DEFAULT_SEVERITY_MAPPING
from sandra.emergency_alerts.src.deduplicator import AlertDeduplicator
from sandra.emergency_alerts.src.priority_queue import PriorityAlertManager
from simulator.emergency_simulator.scenario_runner import ScenarioRunner
from backend.services.patient_service import PatientService
from starlette.testclient import TestClient
from backend.main import app


@pytest.fixture
def rules_engine():
    return RulesEngine()


@pytest.fixture
def deduplicator():
    return AlertDeduplicator(cooldown_seconds=15.0)


@pytest.fixture
def alert_manager():
    return PriorityAlertManager()


@pytest.fixture
def patient_service():
    return PatientService()


@pytest.fixture
def client():
    return TestClient(app)


# 1. FALL_DETECTED
def test_req_1_fall_detected(rules_engine, alert_manager):
    raw = {
        "event_type": "FALL_DETECTED",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "CCTV",
        "message": "Patient fell from bed",
        "video_source": "demo/videos/room101.mp4",
        "camera_id": "CAM101",
        "evidence_type": "CCTV_DEMO_VIDEO",
    }
    event = rules_engine.normalize_event(raw)
    assert event.event_type == "FALL_DETECTED"
    assert event.severity == SeverityLevel.CRITICAL
    alert = alert_manager.ingest_event(event, "Eleanor Vance")
    assert alert.severity == SeverityLevel.CRITICAL
    assert alert.video_source == "demo/videos/room101.mp4"
    assert alert.camera_id == "CAM101"
    assert alert.evidence_type == "CCTV_DEMO_VIDEO"


# 2. LOW_SPO2
def test_req_2_low_spo2(rules_engine, alert_manager):
    raw = {
        "event_type": "LOW_SPO2",
        "patient_id": "P002",
        "room_id": "ROOM102",
        "source": "DEVICE_MONITOR",
        "parameter": "spo2",
        "value": 82,
        "unit": "%",
        "severity": "CRITICAL",
        "message": "Oxygen saturation dropped to 82%",
    }
    event = rules_engine.normalize_event(raw)
    assert event.event_type == "LOW_SPO2"
    assert event.value == 82
    assert event.video_source is None
    alert = alert_manager.ingest_event(event, "Marcus Brody")
    assert alert.severity == SeverityLevel.CRITICAL
    assert alert.video_source is None


# 3. DRIP_FINISHED
def test_req_3_drip_finished(rules_engine, alert_manager):
    raw = {
        "event_type": "DRIP_FINISHED",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "DRIP_MONITOR",
        "message": "IV Bag depleted",
    }
    event = rules_engine.normalize_event(raw)
    assert event.event_type == "DRIP_FINISHED"
    assert event.severity == SeverityLevel.HIGH
    alert = alert_manager.ingest_event(event, "Eleanor Vance")
    assert alert.severity == SeverityLevel.HIGH


# 4. EMERGENCY
def test_req_4_emergency(rules_engine, alert_manager):
    raw = {
        "event_type": "EMERGENCY",
        "patient_id": "P004",
        "room_id": "ROOM104",
        "source": "EMERGENCY_BUTTON",
        "message": "Code Blue button pressed at bedside",
    }
    event = rules_engine.normalize_event(raw)
    assert event.event_type == "EMERGENCY"
    assert event.severity == SeverityLevel.CRITICAL
    alert = alert_manager.ingest_event(event, "David Sterling")
    assert alert.severity == SeverityLevel.CRITICAL


# 5. Event Normalization
def test_req_5_event_normalization(rules_engine):
    minimal_raw = {
        "event_type": "abnormal_movement",
        "patient_id": "P003",
        "room_id": "ROOM103",
    }
    event = rules_engine.normalize_event(minimal_raw)
    assert event.event_type == "ABNORMAL_MOVEMENT"
    assert event.event_id is not None
    assert event.timestamp is not None
    assert event.severity == SeverityLevel.HIGH
    assert event.parameter == "abnormal_movement"
    assert event.value == "DETECTED"
    assert event.unit == "status"
    assert event.status == AlertStatus.ACTIVE


# 6. Severity Classification
def test_req_6_severity_classification(rules_engine):
    assert DEFAULT_SEVERITY_MAPPING["FALL_DETECTED"] == SeverityLevel.CRITICAL
    assert DEFAULT_SEVERITY_MAPPING["EMERGENCY"] == SeverityLevel.CRITICAL
    assert DEFAULT_SEVERITY_MAPPING["ABNORMAL_ECG"] == SeverityLevel.CRITICAL
    assert DEFAULT_SEVERITY_MAPPING["LOW_SPO2"] == SeverityLevel.CRITICAL
    assert DEFAULT_SEVERITY_MAPPING["DRIP_FINISHED"] == SeverityLevel.HIGH
    assert DEFAULT_SEVERITY_MAPPING["PATIENT_LEFT_BED"] == SeverityLevel.HIGH
    assert DEFAULT_SEVERITY_MAPPING["ABNORMAL_MOVEMENT"] == SeverityLevel.HIGH
    assert DEFAULT_SEVERITY_MAPPING["UNUSUAL_POSITION"] == SeverityLevel.MEDIUM


# 7, 8, 9. Alert States: ACTIVE, ACKNOWLEDGED, RESOLVED
def test_req_7_8_9_alert_states(rules_engine, alert_manager):
    raw = {
        "event_type": "PATIENT_LEFT_BED",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "CCTV",
    }
    event = rules_engine.normalize_event(raw)
    alert = alert_manager.ingest_event(event, "Eleanor Vance")

    # 7. ACTIVE
    assert alert.status == AlertStatus.ACTIVE

    # 8. ACKNOWLEDGED
    ack = alert_manager.acknowledge_alert(alert.alert_id, acknowledged_by="Nurse Alex")
    assert ack.status == AlertStatus.ACKNOWLEDGED
    assert ack.acknowledged_by == "Nurse Alex"
    assert ack.acknowledged_at is not None

    # 9. RESOLVED
    res = alert_manager.resolve_alert(alert.alert_id, resolution_note="Patient assisted back to bed")
    assert res.status == AlertStatus.RESOLVED
    assert res.resolution_note == "Patient assisted back to bed"
    assert res.resolved_at is not None


# 10. Critical Compatibility Test: FALL_DETECTED with CCTV fields preserved
def test_req_10_cctv_fields_preserved(rules_engine, alert_manager):
    cctv_event = {
        "event_type": "FALL_DETECTED",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "CCTV",
        "severity": "CRITICAL",
        "message": "Possible patient fall detected",
        "video_source": "demo/videos/room101.mp4",
        "camera_id": "CAM101",
        "evidence_type": "CCTV_DEMO_VIDEO",
        "status": "ACTIVE",
    }
    event = rules_engine.normalize_event(cctv_event)
    assert event.video_source == "demo/videos/room101.mp4"
    assert event.camera_id == "CAM101"
    assert event.evidence_type == "CCTV_DEMO_VIDEO"

    alert = alert_manager.ingest_event(event, "Eleanor Vance")
    assert alert.video_source == "demo/videos/room101.mp4"
    assert alert.camera_id == "CAM101"
    assert alert.evidence_type == "CCTV_DEMO_VIDEO"


# 11. Critical Compatibility Test: LOW_SPO2 without CCTV fields accepted normally
def test_req_11_device_event_without_cctv_fields(rules_engine, alert_manager):
    device_event = {
        "event_type": "LOW_SPO2",
        "patient_id": "P002",
        "room_id": "ROOM102",
        "source": "DEVICE_MONITOR",
        "severity": "CRITICAL",
        "message": "Low SpO2 detected",
        "video_source": None,
    }
    event = rules_engine.normalize_event(device_event)
    assert event.video_source is None
    assert event.camera_id is None
    assert event.evidence_type is None

    alert = alert_manager.ingest_event(event, "Marcus Brody")
    assert alert.status == AlertStatus.ACTIVE
    assert alert.severity == SeverityLevel.CRITICAL


# 12. Duplicate Prevention: Repeated video frames from CCTV do not flood alerts
def test_req_12_duplicate_prevention_cctv_frames(rules_engine, deduplicator, alert_manager):
    frame_base = {
        "event_type": "FALL_DETECTED",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "CCTV",
        "severity": "CRITICAL",
        "message": "Fall detected on camera",
        "video_source": "demo/videos/fall.mp4",
        "camera_id": "CAM101",
    }

    # Frame 1: Emitted
    ev1 = rules_engine.normalize_event(frame_base)
    emit1, r1 = deduplicator.should_emit(ev1)
    assert emit1 is True
    assert r1 == "new_alert"
    alert1 = alert_manager.ingest_event(ev1, "Eleanor Vance")
    initial_alert_count = len(alert_manager.get_all_alerts())

    # Frames 2 - 30: Repeated video frames over next seconds
    for frame_idx in range(2, 31):
        frame = dict(frame_base)
        ev_frame = rules_engine.normalize_event(frame)
        should_emit, reason = deduplicator.should_emit(ev_frame)
        assert should_emit is False, f"Frame {frame_idx} should be throttled"
        assert "throttled" in reason

    # Alert count must remain 1 (no duplicate alert flood)
    final_alert_count = len(alert_manager.get_all_alerts())
    assert final_alert_count == initial_alert_count


# API Integration: Verify Endpoints (POST /api/events, GET /api/events, GET /api/events/active)
def test_api_endpoints_unified_pipeline(client):
    # Ingest CCTV fall event
    cctv_payload = {
        "event_type": "FALL_DETECTED",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "CCTV",
        "severity": "CRITICAL",
        "message": "Bedside fall confirmed",
        "video_source": "demo/cctv_feed.mp4",
        "camera_id": "CAM_ROOM101",
    }
    post_res = client.post("/api/events", json=cctv_payload)
    assert post_res.status_code == 200
    res_data = post_res.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["event"]["camera_id"] == "CAM_ROOM101"
    assert res_data["event"]["video_source"] == "demo/cctv_feed.mp4"

    # Query GET /api/events
    all_res = client.get("/api/events")
    assert all_res.status_code == 200
    all_events = all_res.json()
    assert any(e["parameter"] == "fall_detected" for e in all_events)

    # Query GET /api/events/active
    active_res = client.get("/api/events/active")
    assert active_res.status_code == 200
    active_events = active_res.json()
    assert any(e["status"] == "ACTIVE" for e in active_events)
