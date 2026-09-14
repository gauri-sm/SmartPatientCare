"""
SmartPatientCare - Explainable Temporal Rule-Based Patient State & Fall Detector
Author: Gauri (Frontend & CV Lead)

Evaluates YOLO person detections across consecutive frames to confirm:
1. FALL_DETECTED (rapid downward movement + horizontal lying posture + temporal confirmation)
2. PATIENT_LEFT_BED (patient outside bed ROI confirmed over consecutive frames)
3. ABNORMAL_MOVEMENT (sustained high velocity/agitation)
4. UNUSUAL_POSITION (sustained precarious posture on bed boundary)

DISCLAIMER: This is a hackathon prototype decision-support tool, NOT a clinical system.
"""

from typing import Tuple, Optional, List
import math
from .yolo_detector import PersonDetection

class TemporalPatientStateDetector:
    """
    Applies multi-frame temporal rules on top of YOLO person detections.
    Never triggers critical fall or departure alerts from a single transient frame.
    """

    def __init__(
        self,
        fall_aspect_ratio_threshold: float = 0.70,
        fall_velocity_threshold: float = 18.0,
        fall_confirmation_frames: int = 5,
        left_bed_confirmation_frames: int = 10,
        abnormal_movement_threshold: float = 22.0,
        movement_confirmation_frames: int = 5,
        unusual_pos_confirmation_frames: int = 7
    ):
        self.fall_aspect_ratio_threshold = fall_aspect_ratio_threshold
        self.fall_velocity_threshold = fall_velocity_threshold
        self.fall_confirmation_frames = fall_confirmation_frames
        self.left_bed_confirmation_frames = left_bed_confirmation_frames
        self.abnormal_movement_threshold = abnormal_movement_threshold
        self.movement_confirmation_frames = movement_confirmation_frames
        self.unusual_pos_confirmation_frames = unusual_pos_confirmation_frames

        # Temporal counters
        self.fall_counter: int = 0
        self.left_bed_counter: int = 0
        self.movement_counter: int = 0
        self.unusual_pos_counter: int = 0

        # Motion & trajectory tracking
        self.prev_centroid: Optional[Tuple[int, int]] = None
        self.recent_downward_drop: bool = False
        self.downward_drop_frames_left: int = 0
        self.last_movement_velocity: float = 0.0

    def is_inside_roi(self, pt: Tuple[int, int], roi: Tuple[int, int, int, int]) -> bool:
        x, y = pt
        rx, ry, rw, rh = roi
        return (rx <= x <= rx + rw) and (ry <= y <= ry + rh)

    def evaluate(
        self,
        person: Optional[PersonDetection],
        bed_roi: Tuple[int, int, int, int],
        frame_shape: Tuple[int, int]
    ) -> Tuple[str, dict]:
        """
        Evaluates the current frame detection and returns:
        (state_name, telemetry_dict)
        where state_name is one of 'NORMAL', 'FALL_DETECTED', 'PATIENT_LEFT_BED',
        'ABNORMAL_MOVEMENT', 'UNUSUAL_POSITION'.
        """
        h, w = frame_shape
        rx, ry, rw, rh = bed_roi

        telemetry = {
            "centroid": None,
            "velocity": 0.0,
            "downward_velocity": 0.0,
            "aspect_ratio": 0.0,
            "in_bed": False,
            "fall_counter": self.fall_counter,
            "left_bed_counter": self.left_bed_counter,
            "movement_counter": self.movement_counter
        }

        if person is None:
            # If no person is detected at all, decay counters
            self.fall_counter = max(0, self.fall_counter - 1)
            self.movement_counter = max(0, self.movement_counter - 1)
            if self.left_bed_counter >= self.left_bed_confirmation_frames:
                return "PATIENT_LEFT_BED", telemetry
            return "NORMAL", telemetry

        cx, cy = person.centroid
        ar = person.aspect_ratio
        telemetry["centroid"] = (cx, cy)
        telemetry["aspect_ratio"] = round(ar, 3)

        # 1. Calculate velocity relative to previous centroid
        dy = 0.0
        dx = 0.0
        dist = 0.0
        if self.prev_centroid is not None:
            dx = cx - self.prev_centroid[0]
            dy = cy - self.prev_centroid[1] # positive dy = downward movement
            dist = math.sqrt(dx * dx + dy * dy)

        self.prev_centroid = (cx, cy)
        self.last_movement_velocity = dist
        telemetry["velocity"] = round(dist, 2)
        telemetry["downward_velocity"] = round(dy, 2)

        # 2. Track sudden downward displacement
        if dy >= self.fall_velocity_threshold:
            self.recent_downward_drop = True
            self.downward_drop_frames_left = 18 # Maintain memory for ~1 sec

        if self.downward_drop_frames_left > 0:
            self.downward_drop_frames_left -= 1
        else:
            self.recent_downward_drop = False

        in_bed = self.is_inside_roi((cx, cy), bed_roi)
        telemetry["in_bed"] = in_bed

        # 3. Rule 1: Fall Detection (Explainable Multi-factor Temporal Rule)
        # - Condition A: Person is in lower portion of bed or below bed region (floor area)
        is_floor_or_lower_region = cy >= (ry + rh * 0.70)
        # - Condition B: Horizontal aspect ratio (body lying down: height substantially less than width)
        is_horizontal_lying = ar <= self.fall_aspect_ratio_threshold
        # - Condition C: Preceded by rapid downward velocity OR located deep on the floor
        is_deep_floor = cy >= (ry + rh * 0.95)
        has_fall_dynamics = self.recent_downward_drop or is_deep_floor

        if is_horizontal_lying and is_floor_or_lower_region and has_fall_dynamics:
            self.fall_counter += 1
            if self.fall_counter >= self.fall_confirmation_frames:
                telemetry["fall_counter"] = self.fall_counter
                return "FALL_DETECTED", telemetry
        else:
            self.fall_counter = max(0, self.fall_counter - 1)

        # 4. Rule 2: Patient Left Bed
        # Person has exited the bed ROI and is walking/standing away
        if not in_bed:
            self.left_bed_counter += 1
            if self.left_bed_counter >= self.left_bed_confirmation_frames:
                telemetry["left_bed_counter"] = self.left_bed_counter
                return "PATIENT_LEFT_BED", telemetry
        else:
            self.left_bed_counter = max(0, self.left_bed_counter - 1)

        # 5. Rule 3: Abnormal Movement (sustained erratic agitation / tremor)
        if dist >= self.abnormal_movement_threshold:
            self.movement_counter += 1
            if self.movement_counter >= self.movement_confirmation_frames:
                telemetry["movement_counter"] = self.movement_counter
                return "ABNORMAL_MOVEMENT", telemetry
        else:
            self.movement_counter = max(0, self.movement_counter - 1)

        # 6. Rule 4: Unusual Position (slumping on mattress edge)
        if in_bed:
            is_near_edge = (
                cx < rx + rw * 0.16 or cx > rx + rw * 0.84 or
                cy < ry + rh * 0.16 or cy > ry + rh * 0.84
            )
            if is_near_edge and (ar > 1.35 or ar < 0.38):
                self.unusual_pos_counter += 1
                if self.unusual_pos_counter >= self.unusual_pos_confirmation_frames:
                    return "UNUSUAL_POSITION", telemetry
            else:
                self.unusual_pos_counter = max(0, self.unusual_pos_counter - 1)
        else:
            self.unusual_pos_counter = max(0, self.unusual_pos_counter - 1)

        telemetry["fall_counter"] = self.fall_counter
        telemetry["left_bed_counter"] = self.left_bed_counter
        telemetry["movement_counter"] = self.movement_counter

        return "NORMAL", telemetry

    def reset(self):
        """Resets all temporal counters."""
        self.fall_counter = 0
        self.left_bed_counter = 0
        self.movement_counter = 0
        self.unusual_pos_counter = 0
        self.prev_centroid = None
        self.recent_downward_drop = False
        self.downward_drop_frames_left = 0
