"""
Unit tests for Computer Vision Event Generator
Verifies conformity with shared/schemas/event_schema.json and CCTV metadata.
"""

import unittest
import json
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.event_generator import CVEventGenerator, CCTV_VIDEO_MAPPING, CCTV_CAMERA_MAPPING

class TestCVEventGenerator(unittest.TestCase):

    def setUp(self):
        # Load event schema to verify required fields
        schema_path = os.path.abspath(
            os.path.join(current_dir, "../../../shared/schemas/event_schema.json")
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
        self.required_fields = set(self.schema.get("required", []))

    def _assert_valid_schema(self, event: dict):
        # All required fields present
        for field in self.required_fields:
            self.assertIn(field, event, f"Missing required field '{field}'")

        # Severity in enum
        self.assertIn(event["severity"], ["INFO", "WARNING", "CRITICAL"])
        # Status in enum
        self.assertIn(event["status"], ["ACTIVE", "ACKNOWLEDGED", "RESOLVED"])
        # Source must be computer_vision
        self.assertEqual(event["source"], "computer_vision")

    def test_fall_detected_event_has_cctv(self):
        evt = CVEventGenerator.create_fall_detected_event(
            patient_id="P001",
            room_id="ROOM101",
            confidence=0.95
        )
        self._assert_valid_schema(evt)
        self.assertEqual(evt["event_type"], "FALL_DETECTED")
        self.assertEqual(evt["severity"], "CRITICAL")
        self.assertEqual(evt["patient_id"], "P001")
        self.assertEqual(evt["room_id"], "ROOM101")
        self.assertEqual(evt["parameter"], "fall_state")
        self.assertTrue(evt["value"])

        # CCTV video source and camera ID must be attached
        self.assertIn("video_source", evt)
        self.assertEqual(evt["video_source"], "demo/videos/room101.mp4")
        self.assertEqual(evt["camera_id"], "CAM101")
        self.assertEqual(evt["evidence_type"], "CCTV_VIDEO")

    def test_patient_left_bed_event(self):
        evt = CVEventGenerator.create_patient_left_bed_event(
            patient_id="P003",
            room_id="ROOM103"
        )
        self._assert_valid_schema(evt)
        self.assertEqual(evt["event_type"], "PATIENT_ABNORMALITY")
        self.assertEqual(evt["severity"], "WARNING")
        self.assertEqual(evt["parameter"], "bed_occupancy")
        self.assertEqual(evt["patient_id"], "P003")
        self.assertEqual(evt["room_id"], "ROOM103")

    def test_abnormal_movement_event(self):
        evt = CVEventGenerator.create_abnormal_movement_event(
            patient_id="P002",
            room_id="ROOM102",
            motion_score=88.5
        )
        self._assert_valid_schema(evt)
        self.assertEqual(evt["event_type"], "PATIENT_ABNORMALITY")
        self.assertEqual(evt["severity"], "WARNING")
        self.assertEqual(evt["value"], 88.5)
        self.assertIn("Unusual patient movement", evt["message"])

    def test_unusual_position_event(self):
        evt = CVEventGenerator.create_unusual_position_event(
            patient_id="P004",
            room_id="ROOM104",
            posture_description="slumped_edge"
        )
        self._assert_valid_schema(evt)
        self.assertEqual(evt["event_type"], "PATIENT_ABNORMALITY")
        self.assertEqual(evt["severity"], "WARNING")
        self.assertEqual(evt["value"], "slumped_edge")

if __name__ == "__main__":
    unittest.main()
