"""
SmartPatientCare - Computer Vision Event Generator
Author: Gauri (Frontend & CV Lead)

Constructs standardized event payloads conforming strictly to:
shared/schemas/event_schema.json
Includes optional CCTV video evidence metadata for critical alerts.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict

# CCTV Camera and Demo Video Source Mappings
CCTV_CAMERA_MAPPING = {
    "ROOM101": "CAM101",
    "ROOM102": "CAM102",
    "ROOM103": "CAM103",
    "ROOM104": "CAM104",
}

CCTV_VIDEO_MAPPING = {
    "P001": "demo/videos/room101.mp4",
    "P002": "demo/videos/room102.mp4",
    "P003": "demo/videos/room103.mp4",
    "P004": "demo/videos/room104.mp4",
}

class CVEventGenerator:
    """
    Builds validated event dictionaries conforming to the SmartPatientCare event schema.
    """

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _generate_id(prefix: str = "EVT-CV") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def get_cctv_source(patient_id: str) -> str:
        return CCTV_VIDEO_MAPPING.get(patient_id, f"demo/videos/{patient_id.lower()}.mp4")

    @staticmethod
    def get_camera_id(room_id: str) -> str:
        return CCTV_CAMERA_MAPPING.get(room_id, f"CAM-{room_id}")

    @classmethod
    def create_fall_detected_event(
        cls,
        patient_id: str,
        room_id: str,
        confidence: float = 0.92,
        message: Optional[str] = None,
        video_source: Optional[str] = None,
        camera_id: Optional[str] = None,
        evidence_type: Optional[str] = "CCTV_VIDEO"
    ) -> Dict[str, Any]:
        """
        Creates a CRITICAL fall detection event with attached CCTV video evidence.
        """
        msg = message or f"CRITICAL: Computer vision detected patient fall in {room_id}!"
        v_source = video_source if video_source is not None else cls.get_cctv_source(patient_id)
        c_id = camera_id if camera_id is not None else cls.get_camera_id(room_id)

        event = {
            "event_id": cls._generate_id("EVT-FALL"),
            "timestamp": cls._now_iso(),
            "event_type": "FALL_DETECTED",
            "patient_id": patient_id,
            "room_id": room_id,
            "source": "computer_vision",
            "parameter": "fall_state",
            "value": True,
            "unit": "boolean",
            "severity": "CRITICAL",
            "message": msg,
            "status": "ACTIVE",
            "video_source": v_source,
            "camera_id": c_id,
            "evidence_type": evidence_type
        }
        return event

    @classmethod
    def create_patient_left_bed_event(
        cls,
        patient_id: str,
        room_id: str,
        bed_occupancy: float = 0.0,
        message: Optional[str] = None,
        video_source: Optional[str] = None,
        camera_id: Optional[str] = None,
        evidence_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a WARNING event indicating the patient vacated the designated bed zone.
        """
        msg = message or f"WARNING: Patient {patient_id} has left bed zone without assistance in {room_id}."
        event = {
            "event_id": cls._generate_id("EVT-BED"),
            "timestamp": cls._now_iso(),
            "event_type": "PATIENT_ABNORMALITY",
            "patient_id": patient_id,
            "room_id": room_id,
            "source": "computer_vision",
            "parameter": "bed_occupancy",
            "value": "unoccupied",
            "unit": "state",
            "severity": "WARNING",
            "message": msg,
            "status": "ACTIVE"
        }
        if video_source is not None:
            event["video_source"] = video_source
        if camera_id is not None:
            event["camera_id"] = camera_id
        if evidence_type is not None:
            event["evidence_type"] = evidence_type
        return event

    @classmethod
    def create_abnormal_movement_event(
        cls,
        patient_id: str,
        room_id: str,
        motion_score: float = 85.0,
        message: Optional[str] = None,
        video_source: Optional[str] = None,
        camera_id: Optional[str] = None,
        evidence_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an alert for excessive or abnormal movement.
        """
        msg = message or f"ALERT: Unusual patient movement detected for patient {patient_id} in {room_id}."
        event = {
            "event_id": cls._generate_id("EVT-MOV"),
            "timestamp": cls._now_iso(),
            "event_type": "PATIENT_ABNORMALITY",
            "patient_id": patient_id,
            "room_id": room_id,
            "source": "computer_vision",
            "parameter": "motion_intensity",
            "value": round(float(motion_score), 2),
            "unit": "motion_units",
            "severity": "WARNING",
            "message": msg,
            "status": "ACTIVE"
        }
        if video_source is not None:
            event["video_source"] = video_source
        if camera_id is not None:
            event["camera_id"] = camera_id
        if evidence_type is not None:
            event["evidence_type"] = evidence_type
        return event

    @classmethod
    def create_unusual_position_event(
        cls,
        patient_id: str,
        room_id: str,
        posture_description: str = "slumped_edge",
        message: Optional[str] = None,
        video_source: Optional[str] = None,
        camera_id: Optional[str] = None,
        evidence_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an alert for atypical patient posture (e.g. slumping towards edge).
        """
        msg = message or f"WARNING: Unusual patient position detected ({posture_description}) for patient {patient_id} in {room_id}."
        event = {
            "event_id": cls._generate_id("EVT-POS"),
            "timestamp": cls._now_iso(),
            "event_type": "PATIENT_ABNORMALITY",
            "patient_id": patient_id,
            "room_id": room_id,
            "source": "computer_vision",
            "parameter": "posture_state",
            "value": posture_description,
            "unit": "posture",
            "severity": "WARNING",
            "message": msg,
            "status": "ACTIVE"
        }
        if video_source is not None:
            event["video_source"] = video_source
        if camera_id is not None:
            event["camera_id"] = camera_id
        if evidence_type is not None:
            event["evidence_type"] = evidence_type
        return event
