"""Patient Infusion Session Manager.

Integrates with shared/mock_data/patients.json to track live IV drip sessions
for each patient in the hospital ward.
"""

import json
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from .constants import (
    DropFactor,
    SeverityLevel,
    AlertCategory,
    PARAM_FLOW_RATE,
    PARAM_REMAINING_VOLUME,
    PARAM_OCCLUSION_STATE,
    PARAM_AIR_IN_LINE,
    PARAM_DRIP_STATUS,
    UNIT_ML_H,
    UNIT_ML,
    UNIT_PERCENT,
    UNIT_STATUS,
)
from .drip_calculator import DripCalculator
from .anomaly_detector import DripAnomalyDetector, AnomalyDetectionResult
from .alert_manager import DripAlertManager


@dataclass
class InfusionSession:
    """Represents the active IV drip infusion configuration and state for a patient."""
    patient_id: str
    room_id: str
    patient_name: str
    patient_condition: str
    patient_status: str
    fluid_name: str
    total_volume_ml: float
    prescribed_rate_ml_h: float
    current_flow_rate_ml_h: float
    infused_volume_ml: float = 0.0
    drop_factor: int = DropFactor.MACRO_20.value
    clamp_closed: bool = False
    air_in_line: bool = False
    is_paused: bool = False

    @property
    def remaining_volume_ml(self) -> float:
        return DripCalculator.calculate_remaining_volume(self.total_volume_ml, self.infused_volume_ml)

    @property
    def volume_percentage(self) -> float:
        return DripCalculator.calculate_volume_percentage(self.remaining_volume_ml, self.total_volume_ml)

    @property
    def drops_per_min(self) -> float:
        return DripCalculator.flow_rate_to_drops_per_min(self.current_flow_rate_ml_h, self.drop_factor)

    @property
    def eta_display(self) -> str:
        _, formatted = DripCalculator.calculate_time_to_completion(
            self.remaining_volume_ml, self.current_flow_rate_ml_h
        )
        return formatted


class PatientInfusionManager:
    """Coordinates IV drip sessions for all admitted patients in the ward."""

    DEFAULT_PRESETS = {
        "P001": {
            "fluid_name": "0.9% Normal Saline (0.9% NaCl)",
            "total_volume_ml": 500.0,
            "prescribed_rate_ml_h": 100.0,
            "drop_factor": 20,
        },
        "P002": {
            "fluid_name": "Norepinephrine 4mg/250ml D5W",
            "total_volume_ml": 250.0,
            "prescribed_rate_ml_h": 30.0,
            "drop_factor": 60,
        },
        "P003": {
            "fluid_name": "Lactated Ringer's Solution",
            "total_volume_ml": 1000.0,
            "prescribed_rate_ml_h": 125.0,
            "drop_factor": 20,
        },
        "P004": {
            "fluid_name": "5% Dextrose in Water (D5W)",
            "total_volume_ml": 500.0,
            "prescribed_rate_ml_h": 50.0,
            "drop_factor": 20,
        },
    }

    def __init__(self, patients_json_path: Optional[str] = None):
        if not patients_json_path:
            # Default to shared/mock_data/patients.json
            repo_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..")
            )
            patients_json_path = os.path.join(repo_root, "shared", "mock_data", "patients.json")

        self.patients_json_path = patients_json_path
        self.sessions: Dict[str, InfusionSession] = {}
        self.alert_manager = DripAlertManager()
        self.anomaly_detector = DripAnomalyDetector()
        self._load_patients()

    def _load_patients(self):
        """Load standard patients and initialize IV drip infusion sessions."""
        if not os.path.exists(self.patients_json_path):
            raise FileNotFoundError(f"Patients mock file not found: {self.patients_json_path}")

        with open(self.patients_json_path, "r", encoding="utf-8") as f:
            patients_data = json.load(f)

        for p in patients_data:
            pid = p["patient_id"]
            preset = self.DEFAULT_PRESETS.get(
                pid,
                {
                    "fluid_name": "0.9% Normal Saline",
                    "total_volume_ml": 500.0,
                    "prescribed_rate_ml_h": 100.0,
                    "drop_factor": 20,
                },
            )
            session = InfusionSession(
                patient_id=pid,
                room_id=p["room_id"],
                patient_name=p["name"],
                patient_condition=p["condition"],
                patient_status=p["status"],
                fluid_name=preset["fluid_name"],
                total_volume_ml=preset["total_volume_ml"],
                prescribed_rate_ml_h=preset["prescribed_rate_ml_h"],
                current_flow_rate_ml_h=preset["prescribed_rate_ml_h"],
                infused_volume_ml=0.0,
                drop_factor=preset["drop_factor"],
            )
            self.sessions[pid] = session

    def get_session(self, patient_id: str) -> Optional[InfusionSession]:
        """Retrieve session for a given patient ID."""
        return self.sessions.get(patient_id)

    def get_all_sessions(self) -> List[InfusionSession]:
        """Retrieve all active patient sessions."""
        return list(self.sessions.values())

    def update_telemetry(
        self,
        patient_id: str,
        current_flow_rate_ml_h: Optional[float] = None,
        infused_volume_delta_ml: float = 0.0,
        clamp_closed: Optional[bool] = None,
        air_in_line: Optional[bool] = None,
    ) -> List[AnomalyDetectionResult]:
        """Update telemetry for a patient and check for anomalies."""
        session = self.get_session(patient_id)
        if not session:
            raise KeyError(f"Patient {patient_id} not found in active infusion sessions.")

        if current_flow_rate_ml_h is not None:
            session.current_flow_rate_ml_h = max(0.0, current_flow_rate_ml_h)

        if clamp_closed is not None:
            session.clamp_closed = clamp_closed
            if clamp_closed:
                session.current_flow_rate_ml_h = 0.0

        if air_in_line is not None:
            session.air_in_line = air_in_line

        if infused_volume_delta_ml > 0:
            session.infused_volume_ml = min(
                session.total_volume_ml, session.infused_volume_ml + infused_volume_delta_ml
            )

        # Run anomaly detection
        anomalies = self.anomaly_detector.evaluate(
            remaining_volume_ml=session.remaining_volume_ml,
            total_volume_ml=session.total_volume_ml,
            current_flow_rate_ml_h=session.current_flow_rate_ml_h,
            prescribed_rate_ml_h=session.prescribed_rate_ml_h,
            air_in_line_detected=session.air_in_line,
            clamp_closed=session.clamp_closed,
        )

        # Register non-normal events into alert manager if not already active
        for anomaly in anomalies:
            if anomaly.is_anomaly:
                if not self.alert_manager.has_active_alert_of_type(patient_id, anomaly.event_type.value):
                    evt = self.alert_manager.create_event(
                        event_type=anomaly.event_type.value,
                        patient_id=session.patient_id,
                        room_id=session.room_id,
                        parameter=anomaly.parameter,
                        value=anomaly.value,
                        unit=anomaly.unit,
                        severity=anomaly.severity,
                        message=anomaly.message,
                    )
                    self.alert_manager.register_event(evt)

        return anomalies

    def reset_bag(
        self,
        patient_id: str,
        total_volume_ml: Optional[float] = None,
        prescribed_rate_ml_h: Optional[float] = None,
    ):
        """Reset / hang a new IV bag for the patient and clear related active alerts."""
        session = self.get_session(patient_id)
        if not session:
            return

        if total_volume_ml is not None:
            session.total_volume_ml = total_volume_ml
        if prescribed_rate_ml_h is not None:
            session.prescribed_rate_ml_h = prescribed_rate_ml_h

        session.infused_volume_ml = 0.0
        session.current_flow_rate_ml_h = session.prescribed_rate_ml_h
        session.clamp_closed = False
        session.air_in_line = False
        session.is_paused = False

        # Resolve active drip alerts for this patient
        active = self.alert_manager.get_active_alerts(patient_id=patient_id)
        for a in active:
            self.alert_manager.resolve_alert(a["event_id"])
