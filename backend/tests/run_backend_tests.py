"""Standalone test runner for backend integration.

Can be run with:
  python -m backend.tests.run_backend_tests
"""

import asyncio
import json
import os
import sys

# Add repo root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.database.database import SessionLocal, Base, engine
from backend.database.seeder import init_db
from backend.models.db_models import EventDB, PatientDB
from backend.models.schemas import EventCreate
from backend.services.event_service import EventService
from backend.services.connection_manager import manager


class MockAlertWebSocket:
    """Mock WebSocket client to verify alert delivery and payload retention."""
    def __init__(self):
        self.received_messages = []

    async def accept(self):
        pass

    async def send_text(self, text: str):
        self.received_messages.append(json.loads(text))


async def run_integration_tests():
    print("==================================================")
    print("Running SmartPatientCare Backend Integration Tests")
    print("==================================================")

    init_db()
    db = SessionLocal()
    tests_run = 0
    tests_passed = 0

    # 1. Setup mock WebSocket listener on /ws/alerts
    mock_ws = MockAlertWebSocket()
    await manager.connect_alerts(mock_ws)

    # Test 1: CCTV event with video_source, camera_id, evidence_type
    tests_run += 1
    try:
        cctv_in = EventCreate(
            event_type="FALL_DETECTED",
            patient_id="P001",
            room_id="ROOM101",
            source="CCTV",
            severity="CRITICAL",
            message="Possible patient fall detected",
            video_source="demo/videos/room101.mp4",
            camera_id="CAM101",
            evidence_type="CCTV_DEMO_VIDEO",
            status="ACTIVE"
        )
        ingested = await EventService.ingest_event(db, cctv_in)
        assert ingested.video_source == "demo/videos/room101.mp4"
        assert ingested.camera_id == "CAM101"
        assert ingested.evidence_type == "CCTV_DEMO_VIDEO"

        # Check DB persistence
        db_rec = db.query(EventDB).filter(EventDB.event_id == ingested.event_id).first()
        assert db_rec is not None
        assert db_rec.video_source == "demo/videos/room101.mp4"
        assert db_rec.camera_id == "CAM101"
        assert db_rec.evidence_type == "CCTV_DEMO_VIDEO"

        print(" [PASS] 1. CCTV event with optional video_source & camera_id accepted and persisted")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 1. CCTV event: {e}")

    # Test 2: Medical device event without video_source
    tests_run += 1
    try:
        device_in = EventCreate(
            event_type="LOW_SPO2",
            patient_id="P002",
            room_id="ROOM102",
            source="DEVICE_MONITOR",
            severity="CRITICAL",
            message="SpO2 below configured threshold",
            status="ACTIVE"
        )
        dev_ingested = await EventService.ingest_event(db, device_in)
        assert dev_ingested.video_source is None
        assert dev_ingested.camera_id is None
        assert dev_ingested.evidence_type is None
        assert dev_ingested.status == "ACTIVE"

        print(" [PASS] 2. Medical device event without video_source accepted")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 2. Medical device event: {e}")

    # Test 3: IV drip simulator event
    tests_run += 1
    try:
        drip_in = EventCreate(
            event_type="DRIP_EMPTY",
            patient_id="P003",
            room_id="ROOM103",
            source="drip_sensor",
            parameter="drip_level",
            value=0,
            unit="ml",
            severity="CRITICAL",
            message="IV Drip chamber empty! Replace infusion bag immediately.",
            status="ACTIVE"
        )
        drip_ingested = await EventService.ingest_event(db, drip_in)
        assert drip_ingested.event_type == "DRIP_EMPTY"
        assert drip_ingested.severity == "CRITICAL"

        print(" [PASS] 3. IV drip simulator event accepted")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 3. IV drip event: {e}")

    # Test 4: Emergency simulator event
    tests_run += 1
    try:
        emerg_in = EventCreate(
            event_type="CODE_BLUE",
            patient_id="P004",
            room_id="ROOM104",
            source="emergency_simulator",
            severity="CRITICAL",
            message="Cardiac arrest alert triggered!",
            status="ACTIVE"
        )
        emerg_ingested = await EventService.ingest_event(db, emerg_in)
        assert emerg_ingested.event_type == "CODE_BLUE"
        assert emerg_ingested.severity == "CRITICAL"

        print(" [PASS] 4. Emergency Code Blue event accepted")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 4. Emergency event: {e}")

    # Test 5: Acknowledge event
    tests_run += 1
    try:
        ack_res = await EventService.acknowledge_event(db, ingested.event_id)
        assert ack_res is not None
        assert ack_res["status"] == "ACKNOWLEDGED"

        # Verify in DB
        refreshed = db.query(EventDB).filter(EventDB.event_id == ingested.event_id).first()
        assert refreshed.status == "ACKNOWLEDGED"

        print(" [PASS] 5. Event acknowledgment status update (POST /api/events/{id}/acknowledge)")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 5. Acknowledge event: {e}")

    # Test 6: Resolve event
    tests_run += 1
    try:
        res_res = await EventService.resolve_event(db, dev_ingested.event_id)
        assert res_res is not None
        assert res_res["status"] == "RESOLVED"

        refreshed_dev = db.query(EventDB).filter(EventDB.event_id == dev_ingested.event_id).first()
        assert refreshed_dev.status == "RESOLVED"

        print(" [PASS] 6. Event resolution status update (POST /api/events/{id}/resolve)")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 6. Resolve event: {e}")

    # Test 7: GET active events
    tests_run += 1
    try:
        active_list = EventService.get_active_events(db)
        assert isinstance(active_list, list)
        for act in active_list:
            assert act["status"] == "ACTIVE"

        print(" [PASS] 7. Active events query (GET /api/events/active)")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 7. Active events query: {e}")

    # Test 8: WebSocket alert delivery and CCTV preservation
    tests_run += 1
    try:
        # Check messages received by mock WebSocket
        cctv_ws_messages = [m for m in mock_ws.received_messages if m.get("event_type") == "FALL_DETECTED"]
        assert len(cctv_ws_messages) > 0, "No CCTV message received on /ws/alerts"
        first_cctv_msg = cctv_ws_messages[0]
        assert first_cctv_msg["video_source"] == "demo/videos/room101.mp4"
        assert first_cctv_msg["camera_id"] == "CAM101"
        assert first_cctv_msg["evidence_type"] == "CCTV_DEMO_VIDEO"

        print(" [PASS] 8. WebSocket /ws/alerts delivered normalized event with CCTV fields preserved")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 8. WebSocket alert delivery: {e}")

    # Test 9: GET /api/vitals/ecg/{patient_id} simulated waveform endpoint
    tests_run += 1
    try:
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            resp = client.get("/api/vitals/ecg/P001?duration_seconds=2.0&sampling_rate=250")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert data["patient_id"] == "P001"
            assert "heart_rate" in data
            assert "rhythm" in data
            assert len(data["points"]) == 500
            assert all("t" in p and "mv" in p for p in data["points"][:5])

            # Test 404 for unknown patient
            resp_404 = client.get("/api/vitals/ecg/UNKNOWN_PATIENT")
            assert resp_404.status_code == 404

        print(" [PASS] 9. ECG waveform endpoint (GET /api/vitals/ecg/P001, point count & 404 handled)")
        tests_passed += 1
    except Exception as e:
        print(f" [FAIL] 9. ECG waveform endpoint: {e}")

    # Cleanup
    manager.disconnect_alerts(mock_ws)
    db.close()

    print("==================================================")
    print(f"Integration Tests Completed: {tests_passed}/{tests_run} Passed")
    print("==================================================")
    return tests_passed == tests_run


if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    sys.exit(0 if success else 1)
