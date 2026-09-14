"""
API Integration tests for SmartPatientCare Backend
"""

import pytest
from starlette.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "Prototype for hackathon demonstration only" in data["disclaimer"]


def test_get_all_patients(client):
    res = client.get("/api/patients")
    assert res.status_code == 200
    patients = res.json()
    assert len(patients) == 4
    ids = [p["patient_id"] for p in patients]
    assert "P001" in ids
    assert "P002" in ids
    assert "P003" in ids
    assert "P004" in ids


def test_get_single_patient(client):
    res = client.get("/api/patients/P001")
    assert res.status_code == 200
    p = res.json()
    assert p["patient_id"] == "P001"
    assert p["name"] == "Eleanor Vance"
    assert "vitals" in p
    assert "iv_drip" in p
    assert "ecg" in p


def test_get_station_stats(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_patients"] == 4
    assert "active_critical_alerts" in stats


def test_simulation_scenario_trigger_and_alert_lifecycle(client):
    # Trigger Low SpO2 on P002
    res = client.post("/api/simulate/LOW_SPO2?patient_id=P002")
    assert res.status_code == 200
    sim_data = res.json()
    assert sim_data["status"] == "SUCCESS"
    assert sim_data["alerts_emitted"] >= 1

    # Verify alert appears in /api/alerts
    res_alerts = client.get("/api/alerts?status=ACTIVE&patient_id=P002")
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["alert_id"]

    # Acknowledge the alert
    ack_res = client.post(f"/api/alerts/{alert_id}/acknowledge", json={"nurse_id": "Nurse Alex"})
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

    # Resolve the alert
    resolve_res = client.post(f"/api/alerts/{alert_id}/resolve", json={"resolution_note": "O2 given"})
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"


def test_external_event_ingestion(client):
    # Ingest event matching shared/schemas/event_schema.json
    payload = {
        "event_id": "ext-test-1",
        "timestamp": "2026-09-14T12:30:00Z",
        "event_type": "FALL_DETECTED",
        "patient_id": "P003",
        "room_id": "ROOM103",
        "source": "cv_monitor",
        "parameter": "fall_state",
        "value": True,
        "unit": "status",
        "severity": "CRITICAL",
        "message": "Patient fall detected by bedside computer vision monitor",
        "status": "ACTIVE",
    }
    res = client.post("/api/events", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["alert"]["parameter"] == "fall_state"


def test_dashboard_frontend_serving(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "SmartPatientCare" in res.text
    # Verify visible disclaimer
    assert "Prototype for hackathon demonstration only. Not medically validated and not intended for clinical decision-making." in res.text
