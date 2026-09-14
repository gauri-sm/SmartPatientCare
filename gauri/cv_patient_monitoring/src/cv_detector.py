"""
SmartPatientCare - Computer Vision Patient Monitoring Core (YOLO-Based)
Author: Gauri (Frontend & CV Lead)

Replaces classical MOG2 background subtraction with Ultralytics YOLO person detection
coupled with explainable multi-frame temporal rules for:
1. Fall detection (temporal velocity + horizontal posture confirmation)
2. Patient leaving bed (consecutive frames outside bed ROI)
3. Unusual patient movement (sustained velocity spikes)
4. Unusual patient position (prolonged edge posture)

DISCLAIMER:
This computer vision module is an engineering prototype designed for
hackathon demonstration purposes only. It is NOT medically validated,
NOT a diagnostic device, and MUST NOT be used for clinical decision-making.
"""

import cv2
import numpy as np
import time
from enum import Enum
from typing import Tuple, Optional, Dict, Any, List

from .yolo_detector import YOLOPersonDetector, PersonDetection
from .fall_detector import TemporalPatientStateDetector
from .event_generator import CVEventGenerator, CCTV_VIDEO_MAPPING, CCTV_CAMERA_MAPPING

class CVState(str, Enum):
    NORMAL = "NORMAL"
    FALL_DETECTED = "FALL_DETECTED"
    PATIENT_LEFT_BED = "PATIENT_LEFT_BED"
    ABNORMAL_MOVEMENT = "ABNORMAL_MOVEMENT"
    UNUSUAL_POSITION = "UNUSUAL_POSITION"

class PatientCVDetector:
    """
    YOLO-based patient state detector for bedside video streams.
    Loads YOLO once, detects 'person' instances, tracks patient relative to Bed ROI,
    and applies explainable temporal rules to prevent false-positive alarms.
    """

    def __init__(
        self,
        patient_id: str = "P001",
        room_id: str = "ROOM101",
        model_path: str = "yolo11n.pt",
        confidence_threshold: float = 0.35,
        bed_roi: Optional[Tuple[int, int, int, int]] = None,
        device: str = "cpu",
        fall_velocity_threshold: float = 18.0,
        fall_aspect_ratio_threshold: float = 0.70,
        fall_confirmation_frames: int = 5,
        left_bed_confirmation_frames: int = 10,
        abnormal_movement_threshold: float = 22.0,
        movement_confirmation_frames: int = 5,
        cooldown_seconds: float = 8.0,
        video_source: Optional[str] = None,
        camera_id: Optional[str] = None,
        yolo_detector_instance: Optional[YOLOPersonDetector] = None
    ):
        self.patient_id = patient_id
        self.room_id = room_id
        self.bed_roi = bed_roi
        self.cooldown_seconds = cooldown_seconds
        
        # CCTV Evidence Metadata
        self.camera_id = camera_id or CCTV_CAMERA_MAPPING.get(room_id, f"CAM-{room_id}")
        self.video_source = video_source or CCTV_VIDEO_MAPPING.get(patient_id, f"demo/videos/{patient_id.lower()}.mp4")

        # 1. Initialize YOLO Person Detector (Loaded ONCE)
        if yolo_detector_instance is not None:
            self.yolo = yolo_detector_instance
        else:
            self.yolo = YOLOPersonDetector(
                model_path=model_path,
                confidence_threshold=confidence_threshold,
                device=device
            )

        # 2. Initialize Explainable Temporal Rule Engine
        self.temporal_engine = TemporalPatientStateDetector(
            fall_aspect_ratio_threshold=fall_aspect_ratio_threshold,
            fall_velocity_threshold=fall_velocity_threshold,
            fall_confirmation_frames=fall_confirmation_frames,
            left_bed_confirmation_frames=left_bed_confirmation_frames,
            abnormal_movement_threshold=abnormal_movement_threshold,
            movement_confirmation_frames=movement_confirmation_frames
        )

        # State tracking and event deduplication
        self.current_state = CVState.NORMAL
        self.last_event_time: Dict[CVState, float] = {}
        self.last_patient_detection: Optional[PersonDetection] = None

    def _default_bed_roi(self, frame_w: int, frame_h: int) -> Tuple[int, int, int, int]:
        """Calculates default central bed ROI: top 20% to 70%, left 20% to 75%."""
        x = int(frame_w * 0.20)
        y = int(frame_h * 0.20)
        w = int(frame_w * 0.55)
        h = int(frame_h * 0.48)
        return (x, y, w, h)

    def process_frame(
        self,
        frame: np.ndarray,
        force_state: Optional[CVState] = None
    ) -> Tuple[CVState, Optional[Dict[str, Any]], np.ndarray]:
        """
        Processes a single BGR video frame and returns:
        (detected_state, generated_event_or_None, annotated_frame)
        """
        h, w = frame.shape[:2]
        if self.bed_roi is None:
            self.bed_roi = self._default_bed_roi(w, h)

        # 1. Deterministic state override for demonstration/testing
        if force_state is not None:
            event = self._handle_state_transition(force_state, confidence=0.95)
            annotated = self._draw_annotations(
                frame.copy(),
                state=force_state,
                patient=PersonDetection(
                    x1=int(w * 0.3), y1=int(h * 0.4), x2=int(w * 0.7), y2=int(h * 0.7),
                    width=int(w * 0.4), height=int(h * 0.3),
                    centroid=(int(w * 0.5), int(h * 0.55)),
                    confidence=0.94, aspect_ratio=0.75
                ),
                telemetry={"velocity": 24.0, "aspect_ratio": 0.55, "in_bed": False}
            )
            return force_state, event, annotated

        # 2. YOLO Person Inference (strictly class 0 'person')
        effective_conf = self.yolo.confidence_threshold
        in_floor_area = False
        if self.last_patient_detection and self.bed_roi:
            in_floor_area = self.last_patient_detection.centroid[1] >= (self.bed_roi[1] + self.bed_roi[3] * 0.70)

        if self.temporal_engine.recent_downward_drop or self.temporal_engine.fall_counter > 0 or in_floor_area:
            effective_conf = min(effective_conf, 0.25)

        detected_persons = self.yolo.detect_persons(frame, confidence=effective_conf)

        # 3. Select primary monitored patient near Bed ROI
        prev_centroid = self.last_patient_detection.centroid if self.last_patient_detection else None
        patient = self.yolo.select_patient(
            persons=detected_persons,
            bed_roi=self.bed_roi,
            previous_centroid=prev_centroid
        )
        self.last_patient_detection = patient

        # 4. Multi-frame Temporal Evaluation
        state_str, telemetry = self.temporal_engine.evaluate(
            person=patient,
            bed_roi=self.bed_roi,
            frame_shape=(h, w)
        )
        detected_state = CVState(state_str)

        # 5. Cooldown & Event Generation
        conf = patient.confidence if patient else 0.90
        event = self._handle_state_transition(
            new_state=detected_state,
            confidence=conf,
            telemetry=telemetry
        )

        # 6. Render HUD & Visual Annotations
        annotated_frame = self._draw_annotations(
            frame=frame.copy(),
            state=detected_state,
            patient=patient,
            telemetry=telemetry
        )

        return detected_state, event, annotated_frame

    def _handle_state_transition(
        self,
        new_state: CVState,
        confidence: float = 0.90,
        telemetry: Optional[dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Deduplicates alerts using a cooldown timer and generates standardized payloads.
        """
        now = time.time()
        last_t = self.last_event_time.get(new_state, 0.0)

        if new_state != CVState.NORMAL and (now - last_t >= self.cooldown_seconds):
            self.last_event_time[new_state] = now
            self.current_state = new_state

            if new_state == CVState.FALL_DETECTED:
                return CVEventGenerator.create_fall_detected_event(
                    patient_id=self.patient_id,
                    room_id=self.room_id,
                    confidence=confidence,
                    message=f"CRITICAL: Computer vision detected patient fall in {self.room_id}!",
                    video_source=self.video_source,
                    camera_id=self.camera_id,
                    evidence_type="CCTV_VIDEO"
                )
            elif new_state == CVState.PATIENT_LEFT_BED:
                return CVEventGenerator.create_patient_left_bed_event(
                    patient_id=self.patient_id,
                    room_id=self.room_id,
                    message=f"WARNING: Patient {self.patient_id} has left bed zone without assistance in {self.room_id}.",
                    video_source=self.video_source,
                    camera_id=self.camera_id,
                    evidence_type="CCTV_VIDEO"
                )
            elif new_state == CVState.ABNORMAL_MOVEMENT:
                vel = (telemetry or {}).get("velocity", 35.0)
                return CVEventGenerator.create_abnormal_movement_event(
                    patient_id=self.patient_id,
                    room_id=self.room_id,
                    motion_score=vel,
                    message=f"ALERT: Unusual patient movement detected for patient {self.patient_id} in {self.room_id}.",
                    video_source=self.video_source,
                    camera_id=self.camera_id,
                    evidence_type="CCTV_VIDEO"
                )
            elif new_state == CVState.UNUSUAL_POSITION:
                return CVEventGenerator.create_unusual_position_event(
                    patient_id=self.patient_id,
                    room_id=self.room_id,
                    posture_description="slumped_edge",
                    message=f"WARNING: Unusual patient position detected (slumping on edge) for {self.patient_id}.",
                    video_source=self.video_source,
                    camera_id=self.camera_id,
                    evidence_type="CCTV_VIDEO"
                )

        if new_state == CVState.NORMAL:
            self.current_state = CVState.NORMAL

        return None

    def _draw_annotations(
        self,
        frame: np.ndarray,
        state: CVState,
        patient: Optional[PersonDetection],
        telemetry: dict
    ) -> np.ndarray:
        """
        Draws bed ROI, YOLO bounding box, centroid, and telemetry HUD on frame.
        """
        h, w = frame.shape[:2]

        # 1. Draw Bed Zone ROI (Cyan rectangle)
        if self.bed_roi:
            bx, by, bw, bh = self.bed_roi
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (255, 200, 0), 2)
            cv2.putText(
                frame, "BED ZONE ROI", (bx + 8, by + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 1, cv2.LINE_AA
            )

        # 2. Draw Patient Bounding Box
        if patient:
            px, py, pw, ph = patient.bbox
            conf_str = f"{patient.confidence:.2f}"

            if state == CVState.FALL_DETECTED:
                color = (0, 0, 255) # Red
                label = f"FALL DETECTED! [YOLO: {conf_str}]"
            elif state in (CVState.PATIENT_LEFT_BED, CVState.ABNORMAL_MOVEMENT, CVState.UNUSUAL_POSITION):
                color = (0, 165, 255) # Amber
                label = f"{state.value} [YOLO: {conf_str}]"
            else:
                color = (0, 255, 100) # Green
                label = f"PATIENT (IN BED) [YOLO: {conf_str}]"

            cv2.rectangle(frame, (px, py), (px + pw, py + ph), color, 2)
            cv2.putText(
                frame, label, (px, max(22, py - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA
            )

            # Draw Centroid
            cx, cy = patient.centroid
            cv2.circle(frame, (cx, cy), 5, (0, 255, 255), -1)

        # 3. Top Telemetry HUD
        hud_bg = np.zeros((72, w, 3), dtype=np.uint8)
        alpha = 0.65
        roi = frame[0:72, 0:w]
        frame[0:72, 0:w] = cv2.addWeighted(roi, 1 - alpha, hud_bg, alpha, 0)

        # Header with Camera & Room
        cv2.putText(
            frame, f"SmartPatientCare YOLO Monitor | {self.camera_id} • {self.room_id} ({self.patient_id})",
            (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA
        )

        # Demo Banner label
        cv2.putText(
            frame, "CCTV DEMO VIDEO", (w - 180, 24),
            cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 180, 255), 1, cv2.LINE_AA
        )

        # State Tag
        if state == CVState.NORMAL:
            state_color = (0, 255, 100)
        elif state == CVState.FALL_DETECTED:
            state_color = (0, 0, 255)
        else:
            state_color = (0, 165, 255)

        cv2.putText(
            frame, f"STATE: {state.value}", (15, 54),
            cv2.FONT_HERSHEY_SIMPLEX, 0.60, state_color, 2, cv2.LINE_AA
        )

        # Metrics: Velocity & Aspect Ratio
        vel = telemetry.get("velocity", 0.0)
        ar = telemetry.get("aspect_ratio", 0.0)
        cv2.putText(
            frame, f"AR: {ar:.2f} | Vel: {vel:.1f} px/f", (w - 230, 54),
            cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1, cv2.LINE_AA
        )

        return frame
