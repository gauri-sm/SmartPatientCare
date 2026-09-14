"""Unit tests for JSON Schema compliance against shared/schemas/event_schema.json."""

import unittest
import jsonschema
from simulator.drip_simulator.telemetry_generator import DripTelemetryGenerator
from nifa.drip_monitoring.src.constants import SeverityLevel, AlertStatus


class TestTelemetrySchemaCompliance(unittest.TestCase):
    """Verifies that all events produced strictly adhere to shared/schemas/event_schema.json."""

    def setUp(self):
        self.generator = DripTelemetryGenerator()

    def test_valid_event_passes_schema(self):
        event = self.generator.build_event(
            event_type="DRIP_FLOW_RATE",
            patient_id="P001",
            room_id="ROOM101",
            source="drip_simulator",
            parameter="flow_rate",
            value=100.0,
            unit="ml/h",
            severity=SeverityLevel.INFO.value,
            message="Normal flow",
            status=AlertStatus.ACTIVE.value,
        )
        is_valid, err = self.generator.is_valid(event)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_missing_required_field_fails(self):
        event = {
            "event_id": "EVT-001",
            # missing "timestamp"
            "event_type": "DRIP_FLOW_RATE",
            "patient_id": "P001",
            "room_id": "ROOM101",
            "source": "drip_simulator",
            "parameter": "flow_rate",
            "value": 100.0,
            "unit": "ml/h",
            "severity": "INFO",
            "message": "Missing timestamp",
            "status": "ACTIVE",
        }
        is_valid, err = self.generator.is_valid(event)
        self.assertFalse(is_valid)
        self.assertIn("timestamp", err)

    def test_invalid_severity_fails(self):
        event = {
            "event_id": "EVT-001",
            "timestamp": "2026-09-14T12:00:00Z",
            "event_type": "DRIP_FLOW_RATE",
            "patient_id": "P001",
            "room_id": "ROOM101",
            "source": "drip_simulator",
            "parameter": "flow_rate",
            "value": 100.0,
            "unit": "ml/h",
            "severity": "FATAL",  # Not in ["INFO", "WARNING", "CRITICAL"]
            "message": "Invalid severity",
            "status": "ACTIVE",
        }
        is_valid, err = self.generator.is_valid(event)
        self.assertFalse(is_valid)
        self.assertIn("'FATAL' is not one of", err)

    def test_invalid_status_fails(self):
        event = {
            "event_id": "EVT-001",
            "timestamp": "2026-09-14T12:00:00Z",
            "event_type": "DRIP_FLOW_RATE",
            "patient_id": "P001",
            "room_id": "ROOM101",
            "source": "drip_simulator",
            "parameter": "flow_rate",
            "value": 100.0,
            "unit": "ml/h",
            "severity": "INFO",
            "message": "Invalid status",
            "status": "UNKNOWN",  # Not in ["ACTIVE", "ACKNOWLEDGED", "RESOLVED"]
        }
        is_valid, err = self.generator.is_valid(event)
        self.assertFalse(is_valid)
        self.assertIn("'UNKNOWN' is not one of", err)


    def test_additional_property_fails(self):
        # Schema specifies "additionalProperties": false
        event = {
            "event_id": "EVT-001",
            "timestamp": "2026-09-14T12:00:00Z",
            "event_type": "DRIP_FLOW_RATE",
            "patient_id": "P001",
            "room_id": "ROOM101",
            "source": "drip_simulator",
            "parameter": "flow_rate",
            "value": 100.0,
            "unit": "ml/h",
            "severity": "INFO",
            "message": "Extra property test",
            "status": "ACTIVE",
            "extra_field_not_allowed": 123,
        }
        is_valid, err = self.generator.is_valid(event)
        self.assertFalse(is_valid)
        self.assertIn("extra_field_not_allowed", err)


if __name__ == "__main__":
    unittest.main()
