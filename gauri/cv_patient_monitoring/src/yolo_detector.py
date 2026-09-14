"""
SmartPatientCare - YOLO Person Detector
Author: Gauri (Frontend & CV Lead)

Loads lightweight Ultralytics YOLO (yolo11n.pt / yolov8n.pt) for patient person detection.
Filters strictly for COCO class 0 (person), extracts bounding boxes, confidence,
and selects the most relevant patient near the configured bed ROI.
"""

import os
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np

@dataclass
class PersonDetection:
    """Represents a detected person in a frame."""
    x1: int
    y1: int
    x2: int
    y2: int
    width: int
    height: int
    centroid: Tuple[int, int]
    confidence: float
    aspect_ratio: float # height / width
    track_id: Optional[int] = None

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """Returns (x, y, width, height) format."""
        return (self.x1, self.y1, self.width, self.height)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": (self.x1, self.y1, self.width, self.height),
            "centroid": self.centroid,
            "confidence": round(self.confidence, 3),
            "aspect_ratio": round(self.aspect_ratio, 3),
            "track_id": self.track_id
        }


class YOLOPersonDetector:
    """
    Lightweight YOLO person detector wrapper for hospital bedside surveillance.
    """

    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence_threshold: float = 0.35,
        device: str = "cpu",
        model_instance: Any = None
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.model = model_instance

        if self.model is None:
            self._load_model()

    def _load_model(self):
        """Loads Ultralytics YOLO model with fallback to yolov8n.pt if needed."""
        try:
            from ultralytics import YOLO
            try:
                # Prefer yolo11n.pt
                self.model = YOLO(self.model_path)
            except Exception as e:
                # Fallback to yolov8n.pt if yolo11n is not supported or fails download
                fallback = "yolov8n.pt"
                print(f"[YOLO] Warning: Failed to load '{self.model_path}' ({e}). Falling back to '{fallback}'...")
                self.model = YOLO(fallback)
                self.model_path = fallback
        except ImportError:
            print("[YOLO] Ultralytics not installed. YOLOPersonDetector operating in mock/fallback mode.")
            self.model = None

    def detect_persons(self, frame: np.ndarray, confidence: Optional[float] = None) -> List[PersonDetection]:
        """
        Runs YOLO inference on a single frame and returns all person detections.
        """
        if self.model is None:
            return []

        h, w = frame.shape[:2]
        persons: List[PersonDetection] = []
        conf_thresh = confidence if confidence is not None else self.confidence_threshold

        try:
            # classes=[0] filters strictly for 'person' class in COCO
            results = self.model(
                frame,
                classes=[0],
                conf=conf_thresh,
                device=self.device,
                verbose=False
            )

            if not results or len(results) == 0:
                return []

            boxes = results[0].boxes
            if boxes is None or len(boxes) == 0:
                return []

            for box in boxes:
                if hasattr(box.xyxy[0], 'tolist'):
                    xyxy = box.xyxy[0].tolist()
                else:
                    xyxy = list(box.xyxy[0])

                if hasattr(box.conf, '__getitem__'):
                    conf = float(box.conf[0])
                else:
                    conf = float(box.conf)

                if hasattr(box.cls, '__getitem__'):
                    cls_id = int(box.cls[0])
                else:
                    cls_id = int(box.cls)

                if cls_id != 0: # Ensure strictly person class
                    continue

                x1, y1, x2, y2 = [int(v) for v in xyxy]
                # Clamp coordinates to frame boundary
                x1 = max(0, min(w - 1, x1))
                y1 = max(0, min(h - 1, y1))
                x2 = max(x1 + 1, min(w, x2))
                y2 = max(y1 + 1, min(h, y2))

                bw = x2 - x1
                bh = y2 - y1
                cx = x1 + bw // 2
                cy = y1 + bh // 2
                ar = bh / max(1, bw)

                track_id = int(box.id[0]) if (hasattr(box, 'id') and box.id is not None) else None

                persons.append(PersonDetection(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    width=bw,
                    height=bh,
                    centroid=(cx, cy),
                    confidence=conf,
                    aspect_ratio=ar,
                    track_id=track_id
                ))

        except Exception as e:
            print(f"[YOLO] Error during inference: {e}")
            return []

        return persons

    def select_patient(
        self,
        persons: List[PersonDetection],
        bed_roi: Tuple[int, int, int, int],
        previous_centroid: Optional[Tuple[int, int]] = None
    ) -> Optional[PersonDetection]:
        """
        Selects the primary patient detection from a list of persons:
        1. Prioritize person whose centroid is inside or closest to the Bed ROI.
        2. If multiple inside bed, select highest confidence or closest to previous centroid.
        3. If none inside bed, select person closest to bed ROI / previous location.
        """
        if not persons:
            return None

        rx, ry, rw, rh = bed_roi
        bed_center = (rx + rw // 2, ry + rh // 2)

        def is_in_roi(p: PersonDetection) -> bool:
            cx, cy = p.centroid
            return (rx <= cx <= rx + rw) and (ry <= cy <= ry + rh)

        in_bed = [p for p in persons if is_in_roi(p)]

        if in_bed:
            # If we had a previous centroid, choose closest inside bed; otherwise highest confidence
            if previous_centroid:
                return min(in_bed, key=lambda p: (
                    (p.centroid[0] - previous_centroid[0])**2 + (p.centroid[1] - previous_centroid[1])**2
                ))
            return max(in_bed, key=lambda p: p.confidence)

        # If none strictly inside bed ROI:
        # Prioritize closest to previous centroid, or closest to bed center
        target_pt = previous_centroid or bed_center
        return min(persons, key=lambda p: (
            (p.centroid[0] - target_pt[0])**2 + (p.centroid[1] - target_pt[1])**2
        ))
