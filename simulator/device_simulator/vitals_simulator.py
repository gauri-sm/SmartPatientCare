"""Bedside Vital Signs Telemetry Simulator.

Maintained by Melisa. Part of the SmartPatientCare project.
Simulates bedside multi-parameter patient monitors for patients P001-P004.

Generates compatible SmartPatientCare events:
- LOW_SPO2
- ABNORMAL_ECG
- ABNORMAL_HEART_RATE
- ABNORMAL_BP
- ABNORMAL_TEMPERATURE
- ABNORMAL_RESPIRATORY_RATE

Supports:
- Demonstration transitions: NORMAL -> ABNORMAL progression
- Multi-laptop setup via BACKEND_URL environment variable or --backend CLI flag
- Configurable thresholds and intervals
- Coexists with CCTV / YOLO without any CCTV dependencies
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import math
import os
import random
import time
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error
import uuid

from melisa.patient_device_monitoring.src.vitals_processor import (
    VitalsProcessor,
    VitalsThresholdConfig,
)
from melisa.patient_device_monitoring.src.ecg_analyzer import ECGAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [VitalsSim]: %(message)s"
)
logger = logging.getLogger("VitalsSimulator")

# Resolve shared patients mock data
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOCK_PATIENTS_PATH = os.path.join(ROOT_DIR, "shared", "mock_data", "patients.json")


def normalize_backend_url(raw_url: str) -> str:
    """Normalize backend URL to ensure it points to /api/events endpoint.

    Supports multi-laptop configuration:
    e.g., http://192.168.1.50:8000 -> http://192.168.1.50:8000/api/events
    """
    url = raw_url.strip().rstrip("/")
    if not url.endswith("/api/events"):
        url = f"{url}/api/events"
    return url


class VitalsSimulator:
    """Bedside vital signs simulator supporting continuous monitoring and demo transitions."""

    def __init__(
        self,
        backend_url: Optional[str] = None,
        thresholds: Optional[VitalsThresholdConfig] = None
    ):
        # 1. Environment variable support for multi-laptop deployment
        env_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        self.backend_url = normalize_backend_url(backend_url or env_url)
        self.processor = VitalsProcessor(thresholds=thresholds or VitalsThresholdConfig())
        self.patients = self._load_patients()
        self.anomaly_modes: Dict[str, str] = {}
        self.tick_count = 0

    def _load_patients(self) -> List[dict]:
        """Load patient baselines from shared contracts."""
        if not os.path.exists(MOCK_PATIENTS_PATH):
            logger.warning("Mock patients file not found at %s. Using default patient P001.", MOCK_PATIENTS_PATH)
            return [{
                "patient_id": "P001",
                "room_id": "ROOM101",
                "name": "Eleanor Vance",
                "baseline_vitals": {
                    "heart_rate": 74,
                    "blood_pressure": "125/80",
                    "spo2": 97,
                    "respiratory_rate": 16,
                    "temperature": 36.8
                }
            }]
        with open(MOCK_PATIENTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def post_event(self, event: dict) -> bool:
        """Send event payload to backend REST API (works across laptops via HTTP)."""
        try:
            req = urllib.request.Request(
                self.backend_url,
                data=json.dumps(event).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status in (200, 201)
        except urllib.error.URLError as e:
            logger.debug("Backend unreachable at %s (%s). Running standalone.", self.backend_url, e)
            return False

    def emit_event(self, event: dict):
        """Log event and dispatch to backend."""
        sev = event.get("severity")
        etype = event.get("event_type")
        pid = event.get("patient_id")
        param = event.get("parameter")
        val = event.get("value")
        unit = event.get("unit")

        if sev in ("CRITICAL", "HIGH"):
            logger.warning("🚨 [%s - %s] %s %s: %s %s | %s", sev, etype, pid, param, val, unit, event.get("message"))
        elif sev == "MEDIUM":
            logger.info("⚠️  [%s - %s] %s %s: %s %s", sev, etype, pid, param, val, unit)
        else:
            logger.info("   [NORMAL] %s %s: %s %s", pid, param, val, unit)

        self.post_event(event)

    def demonstrate_transition(
        self,
        parameter: str,
        patient_id: str = "P001",
        step_interval: float = 1.0,
        custom_values: Optional[List[Any]] = None
    ):
        """Demonstrate clear NORMAL -> ABNORMAL threshold transitions.

        Shows progression of parameters stepping past safety boundaries and
        triggering designated alert events.
        """
        # Find room for target patient
        p = next((x for x in self.patients if x["patient_id"] == patient_id), self.patients[0])
        room_id = p.get("room_id", "ROOM101")

        logger.info("==================================================")
        logger.info("DEMO TRANSITION: NORMAL -> ABNORMAL for '%s' (Patient: %s, Room: %s)", parameter, patient_id, room_id)
        logger.info("Target Backend: %s", self.backend_url)
        logger.info("==================================================")

        # 1. SpO2 Transition (98 -> 97 -> 96 -> ... -> 90 -> 88 -> LOW_SPO2)
        if parameter.lower() in ("spo2", "low_spo2"):
            values = custom_values or [98.0, 97.0, 96.0, 94.0, 92.0, 90.0, 88.0, 85.0]
            for v in values:
                event = self.processor.evaluate_spo2(patient_id, room_id, float(v))
                self.emit_event(event)
                time.sleep(step_interval)

        # 2. Heart Rate Transition (75 -> 82 -> 95 -> 110 -> 125 -> ABNORMAL_HEART_RATE)
        elif parameter.lower() in ("heart_rate", "hr", "abnormal_heart_rate"):
            values = custom_values or [75.0, 82.0, 95.0, 105.0, 115.0, 125.0, 135.0]
            for v in values:
                event = self.processor.evaluate_heart_rate(patient_id, room_id, float(v))
                self.emit_event(event)
                time.sleep(step_interval)

        # 3. ECG Transition (NORMAL_ECG -> ABNORMAL_ECG)
        elif parameter.lower() in ("ecg", "abnormal_ecg"):
            scenarios = [
                (75.0, "NORMAL_SINUS_RHYTHM", False),
                (78.0, "NORMAL_SINUS_RHYTHM", False),
                (92.0, "SINUS_TACHYCARDIA", False),
                (125.0, "ATRIAL_FIBRILLATION", True),
                (150.0, "VENTRICULAR_TACHYCARDIA", True),
                (0.0, "ASYSTOLE", True)
            ]
            for hr, rhythm, abnormal in scenarios:
                event = ECGAnalyzer.evaluate_rhythm(
                    patient_id=patient_id,
                    room_id=room_id,
                    heart_rate=hr,
                    rhythm_name=rhythm,
                    is_abnormal=abnormal
                )
                self.emit_event(event)
                time.sleep(step_interval)

        # 4. Blood Pressure Transition (120/80 -> 135/85 -> 150/95 -> 185/125 -> ABNORMAL_BP)
        elif parameter.lower() in ("bp", "blood_pressure", "abnormal_bp"):
            values = custom_values or ["120/80", "130/85", "145/92", "160/100", "185/125"]
            for bp_val in values:
                event = self.processor.evaluate_blood_pressure(patient_id, room_id, str(bp_val))
                self.emit_event(event)
                time.sleep(step_interval)

        # 5. Temperature Transition (37.0 -> 37.5 -> 38.2 -> 39.2 -> 40.0 -> ABNORMAL_TEMPERATURE)
        elif parameter.lower() in ("temp", "temperature", "abnormal_temperature"):
            values = custom_values or [37.0, 37.5, 38.2, 38.8, 39.6]
            for t_val in values:
                event = self.processor.evaluate_temperature(patient_id, room_id, float(t_val))
                self.emit_event(event)
                time.sleep(step_interval)

        # 6. Respiratory Rate Transition (16 -> 18 -> 22 -> 26 -> 32 -> ABNORMAL_RESPIRATORY_RATE)
        elif parameter.lower() in ("rr", "respiratory_rate", "abnormal_respiratory_rate"):
            values = custom_values or [16.0, 18.0, 22.0, 26.0, 32.0]
            for rr_val in values:
                event = self.processor.evaluate_respiratory_rate(patient_id, room_id, float(rr_val))
                self.emit_event(event)
                time.sleep(step_interval)

        logger.info("Transition demonstration completed for %s.", parameter)

    def run_continuous_simulation(self, interval: float = 2.0, target_patient: Optional[str] = None):
        """Continuous simulation cycle generating multi-patient vitals."""
        logger.info("Starting continuous medical-device telemetry stream...")
        logger.info("Target Backend: %s", self.backend_url)
        patients_to_sim = [p for p in self.patients if not target_patient or p["patient_id"] == target_patient]

        try:
            while True:
                self.tick_count += 1
                for p in patients_to_sim:
                    pid = p["patient_id"]
                    room = p.get("room_id", "ROOM101")
                    base = p.get("baseline_vitals", {})

                    hr = base.get("heart_rate", 75) + random.uniform(-2, 2)
                    spo2 = base.get("spo2", 98) + random.uniform(-0.5, 0.5)
                    temp = base.get("temperature", 37.0) + random.uniform(-0.1, 0.1)
                    rr = base.get("respiratory_rate", 16) + random.uniform(-1, 1)

                    bp_str = base.get("blood_pressure", "120/80")
                    try:
                        sys_base, dia_base = map(int, bp_str.split("/"))
                        sys_bp = int(sys_base + random.uniform(-3, 3))
                        dia_bp = int(dia_base + random.uniform(-2, 2))
                        bp_val = f"{sys_bp}/{dia_bp}"
                    except Exception:
                        bp_val = "120/80"

                    # Generate events through vitals processor
                    self.emit_event(self.processor.evaluate_spo2(pid, room, spo2))
                    self.emit_event(self.processor.evaluate_heart_rate(pid, room, hr))
                    self.emit_event(self.processor.evaluate_blood_pressure(pid, room, bp_val))
                    self.emit_event(self.processor.evaluate_temperature(pid, room, temp))
                    self.emit_event(self.processor.evaluate_respiratory_rate(pid, room, rr))
                    self.emit_event(ECGAnalyzer.evaluate_rhythm(pid, room, hr))

                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Simulation halted.")


def main():
    parser = argparse.ArgumentParser(description="SmartPatientCare Bedside Device Simulator (Melisa)")
    parser.add_argument(
        "--backend",
        default=None,
        help="Backend URL (e.g. http://192.168.1.50:8000 or http://localhost:8000). Defaults to BACKEND_URL env var."
    )
    parser.add_argument(
        "--demo-transition",
        choices=["spo2", "heart_rate", "ecg", "bp", "temp", "respiratory_rate", "all"],
        help="Demonstrate NORMAL -> ABNORMAL transition for a specific parameter"
    )
    parser.add_argument(
        "--patient",
        default="P001",
        help="Target patient ID for demo transition (e.g. P001, P002, P003, P004)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between transition steps or telemetry updates"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous live telemetry simulation"
    )
    args = parser.parse_args()

    simulator = VitalsSimulator(backend_url=args.backend)

    if args.demo_transition == "all":
        for param in ["spo2", "heart_rate", "ecg", "bp", "temp", "respiratory_rate"]:
            simulator.demonstrate_transition(param, patient_id=args.patient, step_interval=args.interval)
            time.sleep(1.0)
    elif args.demo_transition:
        simulator.demonstrate_transition(args.demo_transition, patient_id=args.patient, step_interval=args.interval)
    elif args.continuous:
        simulator.run_continuous_simulation(interval=args.interval, target_patient=args.patient)
    else:
        # Default action: run SpO2 transition demonstration
        logger.info("No mode specified. Running default NORMAL -> ABNORMAL SpO2 demo transition.")
        simulator.demonstrate_transition("spo2", patient_id=args.patient, step_interval=args.interval)


if __name__ == "__main__":
    main()
