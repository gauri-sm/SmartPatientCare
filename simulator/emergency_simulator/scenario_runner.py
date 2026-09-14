"""
Emergency Scenario Runner
=========================
Executes simulated emergency scenarios and routes generated telemetry through
Sandra's RulesEngine and Alert Deduplicator.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging

from sandra.emergency_alerts.src.models import (
    SmartPatientCareEvent,
    AlertItem,
    AlertStatus,
    SeverityLevel,
)
from sandra.emergency_alerts.src.rules_engine import RulesEngine
from sandra.emergency_alerts.src.deduplicator import AlertDeduplicator
from sandra.emergency_alerts.src.priority_queue import PriorityAlertManager
from simulator.emergency_simulator.emergency_scenarios import SCENARIOS

logger = logging.getLogger("emergency_simulator.scenario_runner")


class ScenarioRunner:
    """
    Simulates crisis telemetry and injects it into the emergency alert pipeline.
    """

    def __init__(
        self,
        rules_engine: RulesEngine,
        deduplicator: AlertDeduplicator,
        alert_manager: PriorityAlertManager,
        patient_store: Optional[Dict[str, Any]] = None,
    ):
        self.rules_engine = rules_engine
        self.deduplicator = deduplicator
        self.alert_manager = alert_manager
        self.patient_store = patient_store or {}

    def get_available_scenarios(self) -> List[Dict[str, Any]]:
        """
        Returns list of all available scenarios with metadata.
        """
        result = []
        for key, sc in SCENARIOS.items():
            result.append({
                "id": key,
                "title": sc["title"],
                "description": sc["description"],
                "target_patient_id": sc["target_patient_id"],
            })
        # Add Multi-Patient Code Blue scenario
        result.append({
            "id": "MULTI_PATIENT_CRISIS",
            "title": "Station Code Blue (Multi-Patient Crisis)",
            "description": "Simultaneous emergency across multiple rooms (Low SpO2 on P002, V-Fib on P004, IV Empty on P001).",
            "target_patient_id": "ALL",
        })
        return result

    def execute_scenario(
        self, scenario_id: str, patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a simulation scenario, generates telemetry events, evaluates rules,
        deduplicates, and stores in priority queue.
        """
        if scenario_id == "MULTI_PATIENT_CRISIS":
            return self._execute_multi_patient_crisis()

        if scenario_id not in SCENARIOS:
            raise ValueError(f"Unknown scenario ID: {scenario_id}")

        sc = SCENARIOS[scenario_id]
        target_pid = patient_id if patient_id else sc["target_patient_id"]

        patient_rec = self.patient_store.get(target_pid)
        room_id = patient_rec.room_id if patient_rec else "ROOM101"
        patient_name = patient_rec.name if patient_rec else f"Patient {target_pid}"

        now_iso = datetime.now(timezone.utc).isoformat()
        generated_alerts: List[AlertItem] = []
        raw_events: List[SmartPatientCareEvent] = []

        # 1. Update Vitals if specified
        if "vitals" in sc:
            v = sc["vitals"]
            if patient_rec:
                patient_rec.vitals.heart_rate = v.get("heart_rate")
                patient_rec.vitals.blood_pressure = v.get("blood_pressure")
                patient_rec.vitals.systolic_bp = v.get("systolic_bp")
                patient_rec.vitals.diastolic_bp = v.get("diastolic_bp")
                patient_rec.vitals.spo2 = v.get("spo2")
                patient_rec.vitals.respiratory_rate = v.get("respiratory_rate")
                patient_rec.vitals.temperature = v.get("temperature")
                patient_rec.vitals.last_updated = now_iso

            vitals_events = self.rules_engine.evaluate_vitals(
                patient_id=target_pid,
                room_id=room_id,
                vitals=v,
                source="emergency_simulator",
            )
            raw_events.extend(vitals_events)

        # 2. Update IV Drip if specified
        if "iv_drip" in sc:
            drip = sc["iv_drip"]
            if patient_rec:
                patient_rec.iv_drip.volume_remaining_ml = drip["volume_remaining_ml"]
                patient_rec.iv_drip.flow_rate_ml_h = drip["flow_rate_ml_h"]
                patient_rec.iv_drip.status = drip["status"]
                patient_rec.iv_drip.last_updated = now_iso

            drip_events = self.rules_engine.evaluate_iv_drip(
                patient_id=target_pid,
                room_id=room_id,
                volume_remaining_ml=drip["volume_remaining_ml"],
                flow_rate_ml_h=drip["flow_rate_ml_h"],
                source="emergency_simulator",
            )
            raw_events.extend(drip_events)

        # 3. Update ECG if specified
        if "ecg" in sc:
            ecg_data = sc["ecg"]
            if patient_rec:
                patient_rec.ecg.rhythm = ecg_data["rhythm"]
                patient_rec.ecg.status = ecg_data["status"]
                patient_rec.ecg.last_updated = now_iso

            ecg_events = self.rules_engine.evaluate_ecg(
                patient_id=target_pid,
                room_id=room_id,
                rhythm=ecg_data["rhythm"],
                source="emergency_simulator",
            )
            raw_events.extend(ecg_events)

        # 4. Explicit EMERGENCY event generation
        if sc.get("event_type") == "EMERGENCY" or scenario_id == "EMERGENCY":
            em_event = SmartPatientCareEvent(
                event_id=str(uuid.uuid4()),
                timestamp=now_iso,
                event_type="EMERGENCY",
                patient_id=target_pid,
                room_id=room_id,
                source="EMERGENCY_BUTTON",
                parameter=sc.get("parameter", "emergency_call"),
                value="ACTIVE",
                unit="status",
                severity=SeverityLevel.CRITICAL,
                message=sc.get(
                    "message",
                    f"Bedside EMERGENCY Code Blue trigger activated for patient {target_pid}",
                ),
                status=AlertStatus.ACTIVE,
            )
            raw_events.append(em_event)

        # In case of NORMAL_BASELINE: resolve existing alerts for this patient
        if scenario_id == "NORMAL_BASELINE":
            if patient_rec:
                patient_rec.status = "Stable"
            for alert in self.alert_manager.get_all_alerts(status=AlertStatus.ACTIVE, patient_id=target_pid):
                self.alert_manager.resolve_alert(alert.alert_id, "Normalized by baseline simulation")
            self.deduplicator.clear(target_pid)
            return {
                "scenario_id": scenario_id,
                "title": sc["title"],
                "target_patient_id": target_pid,
                "status": "SUCCESS",
                "events_count": 0,
                "alerts_emitted": 0,
                "message": f"Patient {target_pid} vitals restored to baseline. All alerts resolved.",
            }

        # Route events through deduplicator and priority alert manager
        emitted_count = 0
        for ev in raw_events:
            should_emit, reason = self.deduplicator.should_emit(ev)
            if should_emit:
                alert = self.alert_manager.ingest_event(
                    event=ev,
                    patient_name=patient_name,
                    expected_range="Clinical standard",
                )
                generated_alerts.append(alert)
                emitted_count += 1

        if patient_rec:
            # Update patient status badge
            if any(a.severity.value == "CRITICAL" for a in generated_alerts):
                patient_rec.status = "Critical"
            elif any(a.severity.value == "WARNING" for a in generated_alerts):
                if patient_rec.status != "Critical":
                    patient_rec.status = "Attention"

        return {
            "scenario_id": scenario_id,
            "title": sc["title"],
            "target_patient_id": target_pid,
            "status": "SUCCESS",
            "events_count": len(raw_events),
            "alerts_emitted": emitted_count,
            "alerts": [a.model_dump() for a in generated_alerts],
        }

    def _execute_multi_patient_crisis(self) -> Dict[str, Any]:
        """
        Fires multiple simultaneous emergencies across different rooms to test prioritization.
        """
        r1 = self.execute_scenario("LOW_SPO2", "P002")
        r2 = self.execute_scenario("ECG_ARRHYTHMIA", "P004")
        r3 = self.execute_scenario("DRIP_FINISHED", "P001")
        r4 = self.execute_scenario("DRIP_LOW", "P003")

        all_alerts = (
            r1.get("alerts", [])
            + r2.get("alerts", [])
            + r3.get("alerts", [])
            + r4.get("alerts", [])
        )
        return {
            "scenario_id": "MULTI_PATIENT_CRISIS",
            "title": "Station Code Blue (Multi-Patient Crisis)",
            "target_patient_id": "ALL",
            "status": "SUCCESS",
            "events_count": len(all_alerts),
            "alerts_emitted": len(all_alerts),
            "alerts": all_alerts,
        }
