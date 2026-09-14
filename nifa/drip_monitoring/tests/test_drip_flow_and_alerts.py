"""Test suite covering the 9 specific requirements for SmartPatientCare IV Drip Monitoring:

1. normal drip
2. low threshold
3. finished state
4. event generation
5. duplicate prevention
6. patient_id
7. room_id
8. severity
9. API payload
"""

import unittest
from unittest.mock import patch, MagicMock
import requests
import jsonschema

from simulator.drip_simulator.drip_simulator import IVDripSimulator
from simulator.drip_simulator.telemetry_generator import DripTelemetryGenerator
from nifa.drip_monitoring.src.constants import (
    DripEventType,
    DripStatus,
    SOURCE_DRIP_MONITOR,
    PARAM_DRIP_STATUS,
    UNIT_STATUS,
)


class TestDripFlowAndAlerts(unittest.TestCase):
    """Verifies all 9 core requirements for IV Drip simulation and alert engine integration."""

    def setUp(self):
        self.generator = DripTelemetryGenerator()

    # 1. Normal Drip
    def test_normal_drip(self):
        """Verify normal levels (100% -> 20%) keep status NORMAL and generate no alert events."""
        sim = IVDripSimulator(patient_id="P001", room_id="ROOM101", post_to_backend=False)
        for level in [100.0, 80.0, 60.0, 40.0, 20.0]:
            event = sim.set_level_pct(level)
            self.assertIsNone(event, f"Normal level {level}% should not emit an alert event.")
            self.assertEqual(sim.current_state, DripStatus.NORMAL)

    # 2. Low Threshold
    def test_low_threshold(self):
        """Verify crossing configured low threshold triggers DRIP_LOW."""
        sim = IVDripSimulator(
            patient_id="P001",
            room_id="ROOM101",
            low_threshold_pct=15.0,
            post_to_backend=False,
        )
        # Above threshold -> None
        self.assertIsNone(sim.set_level_pct(20.0))

        # At or below threshold (10.0%) -> DRIP_LOW event
        event = sim.set_level_pct(10.0)
        self.assertIsNotNone(event)
        self.assertEqual(event["event_type"], DripEventType.DRIP_LOW.value)
        self.assertEqual(event["value"], DripStatus.LOW.value)
        self.assertEqual(sim.current_state, DripStatus.LOW)

    # 3. Finished State
    def test_finished_state(self):
        """Verify reaching 0% triggers DRIP_FINISHED."""
        sim = IVDripSimulator(patient_id="P001", room_id="ROOM101", post_to_backend=False)
        sim.set_level_pct(10.0)  # Move to LOW first

        event = sim.set_level_pct(0.0)
        self.assertIsNotNone(event)
        self.assertEqual(event["event_type"], DripEventType.DRIP_FINISHED.value)
        self.assertEqual(event["value"], DripStatus.FINISHED.value)
        self.assertEqual(sim.current_state, DripStatus.FINISHED)

    # 4. Event Generation
    def test_event_generation(self):
        """Verify that generated events contain all required fields and validate against schema."""
        sim = IVDripSimulator(patient_id="P001", room_id="ROOM101", post_to_backend=False)
        event = sim.set_level_pct(10.0)
        self.assertIsNotNone(event)

        required_keys = [
            "event_id",
            "timestamp",
            "event_type",
            "patient_id",
            "room_id",
            "source",
            "parameter",
            "value",
            "unit",
            "severity",
            "message",
            "status",
        ]
        for key in required_keys:
            self.assertIn(key, event, f"Missing required event field: {key}")

        # Strict JSON Schema validation
        self.generator.validate(event)

        # Confirm exact source identifier
        self.assertEqual(event["source"], SOURCE_DRIP_MONITOR)
        self.assertEqual(event["status"], "ACTIVE")

    # 5. Duplicate Prevention
    def test_duplicate_prevention(self):
        """Verify state-transition gating prevents duplicate alerts when staying in the same state."""
        sim = IVDripSimulator(patient_id="P001", room_id="ROOM101", low_threshold_pct=15.0, post_to_backend=False)

        # First transition into LOW -> Emits DRIP_LOW
        first_low_event = sim.set_level_pct(10.0)
        self.assertIsNotNone(first_low_event)
        self.assertEqual(first_low_event["event_type"], DripEventType.DRIP_LOW.value)

        # Subsequent level drops while still in LOW state -> Suppressed (None)
        self.assertIsNone(sim.set_level_pct(8.0), "Duplicate DRIP_LOW at 8% was not suppressed!")
        self.assertIsNone(sim.set_level_pct(5.0), "Duplicate DRIP_LOW at 5% was not suppressed!")
        self.assertIsNone(sim.set_level_pct(2.0), "Duplicate DRIP_LOW at 2% was not suppressed!")

        # Transition into FINISHED -> Emits DRIP_FINISHED
        finished_event = sim.set_level_pct(0.0)
        self.assertIsNotNone(finished_event)
        self.assertEqual(finished_event["event_type"], DripEventType.DRIP_FINISHED.value)

        # Subsequent 0.0% updates -> Suppressed (None)
        self.assertIsNone(sim.set_level_pct(0.0), "Duplicate DRIP_FINISHED was not suppressed!")

    # 6. Patient ID
    def test_patient_id(self):
        """Verify patient_id is properly propagated to generated events."""
        sim = IVDripSimulator(patient_id="P003", room_id="ROOM103", post_to_backend=False)
        event = sim.set_level_pct(10.0)
        self.assertEqual(event["patient_id"], "P003")

    # 7. Room ID
    def test_room_id(self):
        """Verify room_id is properly propagated to generated events."""
        sim = IVDripSimulator(patient_id="P004", room_id="ROOM104", post_to_backend=False)
        event = sim.set_level_pct(10.0)
        self.assertEqual(event["room_id"], "ROOM104")

    # 8. Severity Configuration
    def test_severity(self):
        """Verify configurable severity applies to DRIP_LOW and DRIP_FINISHED."""
        # Case A: Default HIGH
        sim_high = IVDripSimulator(
            patient_id="P001",
            room_id="ROOM101",
            low_severity="HIGH",
            finished_severity="HIGH",
            post_to_backend=False,
        )
        evt_low = sim_high.set_level_pct(10.0)
        self.assertEqual(evt_low["severity"], "HIGH")
        evt_fin = sim_high.set_level_pct(0.0)
        self.assertEqual(evt_fin["severity"], "HIGH")

        # Case B: Custom WARNING & CRITICAL
        sim_custom = IVDripSimulator(
            patient_id="P002",
            room_id="ROOM102",
            low_severity="WARNING",
            finished_severity="CRITICAL",
            post_to_backend=False,
        )
        evt_custom_low = sim_custom.set_level_pct(10.0)
        self.assertEqual(evt_custom_low["severity"], "WARNING")
        evt_custom_fin = sim_custom.set_level_pct(0.0)
        self.assertEqual(evt_custom_fin["severity"], "CRITICAL")

    # 9. API Payload and POST /api/events Dispatch
    @patch("requests.post")
    def test_api_payload(self, mock_post):
        """Verify that events are sent to POST /api/events with correct payload and headers."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        sim = IVDripSimulator(
            patient_id="P001",
            room_id="ROOM101",
            backend_url="http://192.168.1.100:8000",
            post_to_backend=True,
        )

        # Trigger DRIP_LOW
        event = sim.set_level_pct(10.0)
        self.assertIsNotNone(event)

        # Verify POST call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://192.168.1.100:8000/api/events")
        self.assertEqual(kwargs["headers"], {"Content-Type": "application/json"})
        self.assertEqual(kwargs["json"], event)

    @patch("requests.post")
    def test_api_payload_offline_resilience(self, mock_post):
        """Verify simulator does not crash if backend is unreachable."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        sim = IVDripSimulator(
            patient_id="P001",
            room_id="ROOM101",
            backend_url="http://offline-host:8000",
            post_to_backend=True,
        )

        # Must not raise an exception
        event = sim.set_level_pct(10.0)
        self.assertIsNotNone(event)
        self.assertEqual(event["event_type"], DripEventType.DRIP_LOW.value)


if __name__ == "__main__":
    unittest.main()
