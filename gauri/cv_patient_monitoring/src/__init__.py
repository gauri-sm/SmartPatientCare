"""
SmartPatientCare - Computer Vision Patient Monitoring Module (YOLO-Powered)
Author: Gauri (Frontend & CV Lead)

Monitors patient bed area for:
1. Fall detection (YOLO + Temporal confirmation)
2. Patient leaving bed (YOLO + Bed ROI)
3. Unusual movement / agitation (YOLO centroid tracking)
4. Unusual patient position (YOLO bounding box aspect ratio)
"""

from .event_generator import CVEventGenerator, CCTV_VIDEO_MAPPING, CCTV_CAMERA_MAPPING
from .yolo_detector import YOLOPersonDetector, PersonDetection
from .fall_detector import TemporalPatientStateDetector
from .cv_detector import PatientCVDetector, CVState

__all__ = [
    "CVEventGenerator",
    "YOLOPersonDetector",
    "PersonDetection",
    "TemporalPatientStateDetector",
    "PatientCVDetector",
    "CVState",
    "CCTV_VIDEO_MAPPING",
    "CCTV_CAMERA_MAPPING"
]
