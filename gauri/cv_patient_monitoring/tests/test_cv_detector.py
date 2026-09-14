"""
Unit tests for YOLO Person Detection and Temporal Patient State / Fall Detection.
Covers all 9 required test cases without requiring a physical GPU.
"""

import unittest
from unittest.mock import MagicMock
import numpy as np
import os
import sys
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.yolo_detector import YOLOPersonDetector, PersonDetection
from src.fall_detector import TemporalPatientStateDetector
from src.cv_detector import PatientCVDetector, CVState

class MockYOLOBox:
    def __init__(self, xyxy, conf=0.92, cls=0):
        self.xyxy = [xyxy]
        self.conf = [conf]
        self.cls = [cls]
        self.id = [1]

class MockYOLOResult:
    def __init__(self, boxes):
        self.boxes = boxes

class MockYOLOModel:
    def __init__(self, boxes=None):
        self._boxes = boxes or []

    def __call__(self, frame, **kwargs):
        return [MockYOLOResult(self._boxes)]

class TestYOLOAndTemporalPatientDetection(unittest.TestCase):

    def setUp(self):
        self.bed_roi = (100, 100, 300, 200) # (x, y, w, h)
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. YOLO detector initializes
    def test_yolo_detector_initializes(self):
        mock_model = MockYOLOModel()
        yolo = YOLOPersonDetector(
            model_path="yolo11n.pt",
            confidence_threshold=0.45,
            device="cpu",
            model_instance=mock_model
        )
        self.assertEqual(yolo.model_path, "yolo11n.pt")
        self.assertEqual(yolo.confidence_threshold, 0.45)
        self.assertEqual(yolo.device, "cpu")
        self.assertIsNotNone(yolo.model)

    # 2. Person detection returns expected structure
    def test_person_detection_returns_expected_structure(self):
        # Mock a box [x1, y1, x2, y2]
        mock_box = MockYOLOBox([120, 120, 220, 260], conf=0.91, cls=0)
        mock_model = MockYOLOModel([mock_box])
        yolo = YOLOPersonDetector(model_instance=mock_model)

        detections = yolo.detect_persons(self.frame)
        self.assertEqual(len(detections), 1)
        p = detections[0]

        self.assertIsInstance(p, PersonDetection)
        self.assertEqual(p.x1, 120)
        self.assertEqual(p.y1, 120)
        self.assertEqual(p.x2, 220)
        self.assertEqual(p.y2, 260)
        self.assertEqual(p.width, 100)
        self.assertEqual(p.height, 140)
        self.assertEqual(p.centroid, (170, 190))
        self.assertAlmostEqual(p.confidence, 0.91)
        self.assertAlmostEqual(p.aspect_ratio, 1.4)
        self.assertEqual(p.bbox, (120, 120, 100, 140))

    # 3. No person does not crash
    def test_no_person_does_not_crash(self):
        mock_model = MockYOLOModel([]) # No detections
        yolo = YOLOPersonDetector(model_instance=mock_model)
        detector = PatientCVDetector(
            patient_id="P001",
            room_id="ROOM101",
            bed_roi=self.bed_roi,
            yolo_detector_instance=yolo
        )

        state, event, annotated = detector.process_frame(self.frame)
        self.assertEqual(state, CVState.NORMAL)
        self.assertIsNone(event)
        self.assertEqual(annotated.shape, self.frame.shape)

    # 4. Bed ROI logic works
    def test_bed_roi_logic_selects_patient_in_bed(self):
        mock_model = MockYOLOModel()
        yolo = YOLOPersonDetector(model_instance=mock_model)

        person_in_bed = PersonDetection(
            x1=150, y1=150, x2=250, y2=220,
            width=100, height=70, centroid=(200, 185),
            confidence=0.88, aspect_ratio=0.7
        )
        person_outside = PersonDetection(
            x1=500, y1=300, x2=580, y2=450,
            width=80, height=150, centroid=(540, 375),
            confidence=0.95, aspect_ratio=1.875
        )

        selected = yolo.select_patient([person_outside, person_in_bed], bed_roi=self.bed_roi)
        self.assertIsNotNone(selected)
        # Even though person_outside had higher confidence, person_in_bed is selected!
        self.assertEqual(selected.centroid, (200, 185))

    # 5. Patient-left-bed temporal logic works
    def test_patient_left_bed_requires_temporal_confirmation(self):
        engine = TemporalPatientStateDetector(left_bed_confirmation_frames=5)

        # Person clearly outside bed_roi: x=550, y=350
        person_outside = PersonDetection(
            x1=520, y1=300, x2=580, y2=400,
            width=60, height=100, centroid=(550, 350),
            confidence=0.90, aspect_ratio=1.66
        )

        # First 4 frames: Counter increments, but state remains NORMAL
        for _ in range(4):
            state, telemetry = engine.evaluate(person_outside, self.bed_roi, (480, 640))
            self.assertEqual(state, "NORMAL")
            self.assertFalse(telemetry["in_bed"])

        # 5th frame: Confirmed!
        state, telemetry = engine.evaluate(person_outside, self.bed_roi, (480, 640))
        self.assertEqual(state, "PATIENT_LEFT_BED")

    # 6. Fall logic requires temporal confirmation
    def test_fall_logic_requires_temporal_confirmation(self):
        engine = TemporalPatientStateDetector(
            fall_aspect_ratio_threshold=0.70,
            fall_velocity_threshold=15.0,
            fall_confirmation_frames=4
        )

        # Person in bed upright
        p_upright = PersonDetection(
            x1=200, y1=120, x2=280, y2=260,
            width=80, height=140, centroid=(240, 190),
            confidence=0.92, aspect_ratio=1.75
        )
        engine.evaluate(p_upright, self.bed_roi, (480, 640))

        # Sudden rapid downward plunge: centroid moves to floor (y=380, dy = +190)
        # Horizontal aspect ratio (width=140, height=50 => AR = 0.35)
        p_fallen = PersonDetection(
            x1=250, y1=355, x2=390, y2=405,
            width=140, height=50, centroid=(320, 380),
            confidence=0.94, aspect_ratio=0.357
        )

        # Frame 1 of fall: Downward drop detected, but fall_counter = 1 -> STILL NORMAL
        state, tel = engine.evaluate(p_fallen, self.bed_roi, (480, 640))
        self.assertEqual(state, "NORMAL")
        self.assertEqual(tel["fall_counter"], 1)

        # Frames 2 & 3: Still accumulating
        for i in [2, 3]:
            state, tel = engine.evaluate(p_fallen, self.bed_roi, (480, 640))
            self.assertEqual(state, "NORMAL")
            self.assertEqual(tel["fall_counter"], i)

        # Frame 4: 4th consecutive frame meets confirmation threshold!
        state, tel = engine.evaluate(p_fallen, self.bed_roi, (480, 640))
        self.assertEqual(state, "FALL_DETECTED")
        self.assertEqual(tel["fall_counter"], 4)

    # 7. Event cooldown works
    def test_event_cooldown_debounces_repeated_alerts(self):
        mock_model = MockYOLOModel()
        yolo = YOLOPersonDetector(model_instance=mock_model)
        detector = PatientCVDetector(
            patient_id="P001",
            room_id="ROOM101",
            cooldown_seconds=5.0,
            yolo_detector_instance=yolo
        )

        # Trigger event first time
        evt1 = detector._handle_state_transition(CVState.FALL_DETECTED)
        self.assertIsNotNone(evt1)
        self.assertEqual(evt1["event_type"], "FALL_DETECTED")

        # Trigger immediately again: must return None due to cooldown
        evt2 = detector._handle_state_transition(CVState.FALL_DETECTED)
        self.assertIsNone(evt2)

    # 8. Event contains patient_id and room_id
    def test_event_contains_patient_id_and_room_id(self):
        mock_model = MockYOLOModel()
        yolo = YOLOPersonDetector(model_instance=mock_model)
        detector = PatientCVDetector(
            patient_id="P003",
            room_id="ROOM103",
            yolo_detector_instance=yolo
        )
        evt = detector._handle_state_transition(CVState.PATIENT_LEFT_BED)
        self.assertIsNotNone(evt)
        self.assertEqual(evt["patient_id"], "P003")
        self.assertEqual(evt["room_id"], "ROOM103")

    # 9. CCTV/video_source is attached to critical events where appropriate
    def test_cctv_video_source_attached_to_critical_events(self):
        mock_model = MockYOLOModel()
        yolo = YOLOPersonDetector(model_instance=mock_model)
        detector = PatientCVDetector(
            patient_id="P001",
            room_id="ROOM101",
            video_source="demo/videos/room101.mp4",
            camera_id="CAM101",
            yolo_detector_instance=yolo
        )
        evt = detector._handle_state_transition(CVState.FALL_DETECTED)
        self.assertIsNotNone(evt)
        self.assertEqual(evt["severity"], "CRITICAL")
        self.assertEqual(evt["video_source"], "demo/videos/room101.mp4")
        self.assertEqual(evt["camera_id"], "CAM101")
        self.assertEqual(evt["evidence_type"], "CCTV_VIDEO")

if __name__ == "__main__":
    unittest.main()
