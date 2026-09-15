"""Integration tests for SmartPatientCare backend.

Verifies:
- CCTV events with video_source, camera_id, evidence_type
- Medical device events without video_source
- IV drip events without video_source
- Emergency / Code Blue events
- GET /api/events and GET /api/events/active
- GET /api/patients and GET /api/patients/{id}
- POST /api/events/{id}/acknowledge
- POST /api/events/{id}/resolve
- WebSocket /ws/alerts real-time broadcast and preservation of CCTV fields
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.seeder import init_db
from backend.database.database import SessionLocal
from backend.models.db_models import EventDB, PatientDB


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initialize test database and seed initial mock patients."""
    init_db()


@pytest.fixture
def client():
    """FastAPI test client instance."""
    with TestClient(app) as test_client:
        yield test_client


def test_cctv_event_with_video_source(client):
    """Test CCTV event containing optional video_source, camera_id, and evidence_type."""
    payload = {
        "event_type": "FALL_DETECTED",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "CCTV",
        "severity": "CRITICAL",
        "message": "Possible patient fall detected",
        "video_source": "demo/videos/room101.mp4",
        "camera_id": "CAM101",
        "evidence_type": "CCTV_DEMO_VIDEO",
        "status": "ACTIVE"
    }

    response = client.post("/api/events", json=payload)
    assert response.status_code == 201, f"Failed: {response.text}"

    data = response.json()
    assert data["event_type"] == "FALL_DETECTED"
    assert data["patient_id"] == "P001"
    assert data["source"] == "CCTV"
    assert data["severity"] == "CRITICAL"
    assert data["video_source"] == "demo/videos/room101.mp4"
    assert data["camera_id"] == "CAM101"
    assert data["evidence_type"] == "CCTV_DEMO_VIDEO"
    assert data["status"] == "ACTIVE"
    assert "event_id" in data
    assert "timestamp" in data


def test_device_event_without_video_source(client):
    """Test medical device event without optional CCTV fields."""
    payload = {
        "event_type": "LOW_SPO2",
        "patient_id": "P002",
        "room_id": "ROOM102",
        "source": "DEVICE_MONITOR",
        "severity": "CRITICAL",
        "message": "SpO2 below configured threshold",
        "status": "ACTIVE"
    }

    response = client.post("/api/events", json=payload)
    assert response.status_code == 201, f"Failed: {response.text}"

    data = response.json()
    assert data["event_type"] == "LOW_SPO2"
    assert data["patient_id"] == "P002"
    assert data["source"] == "DEVICE_MONITOR"
    assert data["severity"] == "CRITICAL"
    assert data.get("video_source") is None
    assert data.get("camera_id") is None
    assert data["status"] == "ACTIVE"


def test_drip_event_without_video_source(client):
    """Test IV / drip simulator event ingestion."""
    payload = {
        "event_type": "DRIP_EMPTY",
        "patient_id": "P003",
        "room_id": "ROOM103",
        "source": "drip_sensor",
        "parameter": "drip_level",
        "value": 0,
        "unit": "ml",
        "severity": "CRITICAL",
        "message": "IV Drip chamber empty! Replace infusion bag immediately.",
        "status": "ACTIVE"
    }

    response = client.post("/api/events", json=payload)
    assert response.status_code == 201, f"Failed: {response.text}"

    data = response.json()
    assert data["event_type"] == "DRIP_EMPTY"
    assert data["source"] == "drip_sensor"
    assert data["value"] == 0
    assert data["unit"] == "ml"
    assert data["severity"] == "CRITICAL"


def test_emergency_event(client):
    """Test emergency simulator alert ingestion."""
    payload = {
        "event_type": "CODE_BLUE",
        "patient_id": "P004",
        "room_id": "ROOM104",
        "source": "emergency_simulator",
        "severity": "CRITICAL",
        "message": "Cardiac arrest alert triggered! Response team dispatched.",
        "status": "ACTIVE"
    }

    response = client.post("/api/events", json=payload)
    assert response.status_code == 201, f"Failed: {response.text}"

    data = response.json()
    assert data["event_type"] == "CODE_BLUE"
    assert data["severity"] == "CRITICAL"


def test_get_active_events(client):
    """Test GET /api/events/active returns active alerts."""
    response = client.get("/api/events/active")
    assert response.status_code == 200

    events = response.json()
    assert isinstance(events, list)
    for event in events:
        assert event["status"] == "ACTIVE"


def test_acknowledge_event(client):
    """Test POST /api/events/{id}/acknowledge transitions status to ACKNOWLEDGED."""
    # Create an event to acknowledge
    create_resp = client.post("/api/events", json={
        "event_type": "LOW_SPO2",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "device_simulator",
        "severity": "HIGH",
        "message": "Patient SpO2 dropped to 91%",
        "status": "ACTIVE"
    })
    assert create_resp.status_code == 201
    event_id = create_resp.json()["event_id"]

    # Acknowledge the event
    ack_resp = client.post(f"/api/events/{event_id}/acknowledge")
    assert ack_resp.status_code == 200

    data = ack_resp.json()
    assert data["event_id"] == event_id
    assert data["status"] == "ACKNOWLEDGED"


def test_resolve_event(client):
    """Test POST /api/events/{id}/resolve transitions status to RESOLVED."""
    # Create an event to resolve
    create_resp = client.post("/api/events", json={
        "event_type": "ABNORMAL_HEART_RATE",
        "patient_id": "P002",
        "room_id": "ROOM102",
        "source": "device_simulator",
        "severity": "HIGH",
        "message": "Tachycardia 110 bpm",
        "status": "ACTIVE"
    })
    assert create_resp.status_code == 201
    event_id = create_resp.json()["event_id"]

    # Resolve the event
    res_resp = client.post(f"/api/events/{event_id}/resolve")
    assert res_resp.status_code == 200

    data = res_resp.json()
    assert data["event_id"] == event_id
    assert data["status"] == "RESOLVED"


def test_patient_endpoints(client):
    """Test GET /api/patients and GET /api/patients/{id}."""
    # List patients
    resp = client.get("/api/patients")
    assert resp.status_code == 200
    patients = resp.json()
    assert len(patients) >= 4

    # Single patient
    resp_p = client.get("/api/patients/P001")
    assert resp_p.status_code == 200
    p = resp_p.json()
    assert p["patient_id"] == "P001"
    assert p["room_id"] == "ROOM101"
    assert "devices_connected" in p


def test_websocket_alerts_delivery(client):
    """Test WebSocket /ws/alerts delivers normalized events with optional CCTV fields."""
    with client.websocket_connect("/ws/alerts") as websocket:
        # Handshake verification
        greeting = websocket.receive_json()
        assert greeting["type"] == "CONNECTION_ESTABLISHED"

        # Ingest a CCTV event via HTTP
        cctv_payload = {
            "event_type": "FALL_DETECTED",
            "patient_id": "P001",
            "room_id": "ROOM101",
            "source": "CCTV",
            "severity": "CRITICAL",
            "message": "Bedside fall detected by camera",
            "video_source": "demo/videos/room101.mp4",
            "camera_id": "CAM101",
            "evidence_type": "CCTV_DEMO_VIDEO",
            "status": "ACTIVE"
        }
        post_resp = client.post("/api/events", json=cctv_payload)
        assert post_resp.status_code == 201

        # Receive real-time alert via WebSocket
        ws_msg = websocket.receive_json()
        assert ws_msg["event_type"] == "FALL_DETECTED"
        assert ws_msg["patient_id"] == "P001"
        assert ws_msg["video_source"] == "demo/videos/room101.mp4"
        assert ws_msg["camera_id"] == "CAM101"
        assert ws_msg["evidence_type"] == "CCTV_DEMO_VIDEO"
        assert ws_msg["severity"] == "CRITICAL"


def test_get_ecg_waveform_success(client):
    """Test GET /api/vitals/ecg/P001 returns 200 with all expected fields and correct point count."""
    response = client.get("/api/vitals/ecg/P001?duration_seconds=2.0&sampling_rate=250")
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "P001"
    assert "heart_rate" in data
    assert isinstance(data["heart_rate"], (int, float))
    assert "rhythm" in data
    assert isinstance(data["rhythm"], str)
    assert data["sampling_rate"] == 250
    assert data["duration_seconds"] == 2.0
    assert "points" in data
    assert isinstance(data["points"], list)
    expected_points = int(2.0 * 250)
    assert len(data["points"]) == expected_points
    # Check individual point structure
    for pt in data["points"][:5]:
        assert "t" in pt
        assert "mv" in pt
        assert isinstance(pt["t"], float)
        assert isinstance(pt["mv"], float)


def test_get_ecg_waveform_unknown_patient(client):
    """Test GET /api/vitals/ecg/{id} returns 404 for unknown patient."""
    response = client.get("/api/vitals/ecg/NON_EXISTENT_PATIENT")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_get_ecg_waveform_uses_live_heart_rate(client):
    """Test GET /api/vitals/ecg/P001 uses current/live heart rate when available."""
    # Ingest a live heart rate event for P001 with 142.0 bpm
    hr_payload = {
        "event_type": "ABNORMAL_HEART_RATE",
        "patient_id": "P001",
        "room_id": "ROOM101",
        "source": "device_simulator",
        "parameter": "heart_rate",
        "value": 142.0,
        "unit": "bpm",
        "severity": "HIGH",
        "message": "Elevated heart rate 142 bpm",
        "status": "ACTIVE"
    }
    post_resp = client.post("/api/events", json=hr_payload)
    assert post_resp.status_code == 201

    # Request waveform and verify live heart rate was used
    ecg_resp = client.get("/api/vitals/ecg/P001")
    assert ecg_resp.status_code == 200
    ecg_data = ecg_resp.json()
    assert ecg_data["patient_id"] == "P001"
    assert ecg_data["heart_rate"] == 142.0

