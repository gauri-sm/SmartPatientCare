"""
Patient & Telemetry Service
===========================
Integrates patient records from shared/mock_data/patients.json with Sandra's
RulesEngine, Deduplicator, Priority Alert Manager, and Scenario Runner.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging

from sandra.emergency_alerts.src.models import (
    PatientRecord,
    VitalSigns,
    IVDripState,
    ECGState,
    AlertItem,
    AlertStatus,
    SeverityLevel,
    SmartPatientCareEvent,
)
from sandra.emergency_alerts.src.rules_engine import RulesEngine
from sandra.emergency_alerts.src.deduplicator import AlertDeduplicator
from sandra.emergency_alerts.src.priority_queue import PriorityAlertManager
from simulator.emergency_simulator.scenario_runner import ScenarioRunner

logger = logging.getLogger("backend.patient_service")


class PatientService:
    def __init__(self, mock_patients_path: Optional[str] = None):
        if mock_patients_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent
            self.mock_patients_path = str(repo_root / "shared" / "mock_data" / "patients.json")
        else:
            self.mock_patients_path = mock_patients_path

        self.patients: Dict[str, PatientRecord] = {}
        self.rules_engine = RulesEngine()
        self.deduplicator = AlertDeduplicator(cooldown_seconds=15.0)
        self.alert_manager = PriorityAlertManager()
        self._load_patients()
        self.scenario_runner = ScenarioRunner(
            self.rules_engine,
            self.deduplicator,
            self.alert_manager,
            self.patients,
        )

    def _load_patients(self):
        """Loads patients from shared/mock_data/patients.json"""
        path = Path(self.mock_patients_path)
        if not path.exists():
            logger.error(f"Patient file not found: {path}")
            return

        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        now_iso = datetime.now(timezone.utc).isoformat()
        for p in raw_data:
            pid = p["patient_id"]
            bv = p.get("baseline_vitals", {})

            # Parse systolic & diastolic
            bp_str = bv.get("blood_pressure", "120/80")
            sys_bp, dia_bp = 120.0, 80.0
            if "/" in str(bp_str):
                parts = str(bp_str).split("/")
                sys_bp = float(parts[0])
                dia_bp = float(parts[1])

            vitals = VitalSigns(
                heart_rate=float(bv.get("heart_rate", 75)),
                blood_pressure=str(bp_str),
                systolic_bp=sys_bp,
                diastolic_bp=dia_bp,
                spo2=float(bv.get("spo2", 98)),
                respiratory_rate=float(bv.get("respiratory_rate", 16)),
                temperature=float(bv.get("temperature", 37.0)),
                last_updated=now_iso,
            )

            # Set up IV drip state
            iv_drip = IVDripState(
                volume_remaining_ml=450.0,
                flow_rate_ml_h=100.0,
                status="NORMAL",
                last_updated=now_iso,
            )

            # Set up ECG state
            ecg = ECGState(
                rhythm="NORMAL_SINUS_RHYTHM",
                status="NORMAL",
                last_updated=now_iso,
            )

            rec = PatientRecord(
                patient_id=pid,
                room_id=p.get("room_id", "ROOM101"),
                name=p.get("name", f"Patient {pid}"),
                age=p.get("age", 50),
                gender=p.get("gender", "Unknown"),
                admission_date=p.get("admission_date", now_iso),
                condition=p.get("condition", "Under Evaluation"),
                status=p.get("status", "Observation"),
                assigned_doctor=p.get("assigned_doctor", "Staff Physician"),
                assigned_nurse=p.get("assigned_nurse", "Staff Nurse"),
                devices_connected=p.get("devices_connected", []),
                vitals=vitals,
                iv_drip=iv_drip,
                ecg=ecg,
                active_alerts=[],
            )
            self.patients[pid] = rec

    def get_all_patients(self) -> List[Dict[str, Any]]:
        result = []
        for p in self.patients.values():
            p_data = p.model_dump()
            # Attach active alerts
            p_data["active_alerts"] = [
                a.model_dump()
                for a in self.alert_manager.get_all_alerts(
                    status=AlertStatus.ACTIVE, patient_id=p.patient_id
                )
            ]
            result.append(p_data)
        return result

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        p = self.patients.get(patient_id)
        if not p:
            return None
        p_data = p.model_dump()
        p_data["alerts_history"] = [
            a.model_dump()
            for a in self.alert_manager.get_all_alerts(patient_id=patient_id)
        ]
        return p_data

    def get_alerts(
        self,
        status: Optional[str] = None,
        patient_id: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        st = AlertStatus(status) if status else None
        sev = SeverityLevel(severity) if severity else None
        alerts = self.alert_manager.get_all_alerts(
            status=st, patient_id=patient_id, severity=sev
        )
        return [a.model_dump() for a in alerts]

    def acknowledge_alert(
        self, alert_id: str, acknowledged_by: str = "Nurse Station"
    ) -> Optional[Dict[str, Any]]:
        alert = self.alert_manager.acknowledge_alert(alert_id, acknowledged_by)
        return alert.model_dump() if alert else None

    def resolve_alert(
        self, alert_id: str, note: str = "Resolved by clinical nurse"
    ) -> Optional[Dict[str, Any]]:
        alert = self.alert_manager.resolve_alert(alert_id, note)
        if alert:
            # Check if patient condition can be downgraded from Critical
            pid = alert.patient_id
            if pid in self.patients:
                remaining_active = self.alert_manager.get_all_alerts(
                    status=AlertStatus.ACTIVE, patient_id=pid
                )
                if not remaining_active:
                    self.patients[pid].status = "Stable"
            return alert.model_dump()
        return None

    def execute_scenario(
        self, scenario_id: str, patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.scenario_runner.execute_scenario(scenario_id, patient_id)

    def ingest_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes event (CCTV, Medical Device, Drip, or Emergency),
        applies duplicate throttling, and ingests into Sandra's centralized Priority Alert Manager.
        """
        # Normalize via Sandra's RulesEngine
        event = self.rules_engine.normalize_event(event_data)

        # Check deduplication / throttle bursts (e.g. repeated CCTV video frames)
        should_emit, reason = self.deduplicator.should_emit(event)

        pid = event.patient_id
        patient_name = f"Patient {pid}"
        if pid in self.patients:
            patient_name = self.patients[pid].name

        alert = self.alert_manager.ingest_event(
            event=event,
            patient_name=patient_name,
            expected_range="Telemetry standard",
        )

        # Update patient status badge
        if pid in self.patients:
            p = self.patients[pid]
            if event.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                p.status = "Critical"
            elif event.severity in [SeverityLevel.WARNING, SeverityLevel.MEDIUM] and p.status != "Critical":
                p.status = "Attention"

        return alert.model_dump()

    def get_station_stats(self) -> Dict[str, Any]:
        all_alerts = self.alert_manager.get_all_alerts()
        active_alerts = [a for a in all_alerts if a.status == AlertStatus.ACTIVE]
        active_critical = [
            a for a in active_alerts if a.severity == SeverityLevel.CRITICAL
        ]
        active_warning = [
            a for a in active_alerts if a.severity == SeverityLevel.WARNING
        ]

        total_patients = len(self.patients)
        critical_patients = set(a.patient_id for a in active_critical)
        warning_patients = set(
            a.patient_id for a in active_warning if a.patient_id not in critical_patients
        )
        stable_count = total_patients - len(critical_patients) - len(warning_patients)

        return {
            "total_patients": total_patients,
            "stable_patients": max(0, stable_count),
            "attention_patients": len(warning_patients),
            "critical_patients": len(critical_patients),
            "active_critical_alerts": len(active_critical),
            "active_warning_alerts": len(active_warning),
            "total_active_alerts": len(active_alerts),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
