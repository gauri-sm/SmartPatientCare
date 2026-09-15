"""Mechanical Ventilator Telemetry & Alert Simulator.

Maintained by Melisa. Part of the SmartPatientCare project.
Simulates clinical mechanical ventilator telemetry for intubated patients (P002 and P004).

IMPORTANT SAFETY & DESIGN PRINCIPLES:
- Generates monitoring and recommendation events ONLY.
- Does NOT implement commands that control a real ventilator.
- Uses clinical advisory language: "Ventilator parameter requires attention: ..."
  rather than claiming medical diagnoses.
- Fully supports multi-laptop network configurations via BACKEND_URL.
- Completely independent of CCTV / YOLO components.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import os
import random
import time
from typing import Dict, List, Optional
import urllib.request
import urllib.error
import uuid

from melisa.patient_device_monitoring.src.ventilator_processor import (
    VentilatorProcessor,
    VentilatorThresholdConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [VentSim]: %(message)s"
)
logger = logging.getLogger("VentilatorSimulator")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOCK_PATIENTS_PATH = os.path.join(ROOT_DIR, "shared", "mock_data", "patients.json")


def normalize_backend_url(raw_url: str) -> str:
    """Normalize backend URL to ensure it targets /api/events."""
    url = raw_url.strip().rstrip("/")
    if not url.endswith("/api/events"):
        url = f"{url}/api/events"
    return url


class VentilatorSimulator:
    """Simulates monitoring telemetry and alerts for patients on mechanical ventilation."""

    def __init__(self, backend_url: Optional[str] = None, thresholds: Optional[VentilatorThresholdConfig] = None):
        env_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        self.backend_url = normalize_backend_url(backend_url or env_url)
        self.processor = VentilatorProcessor(thresholds=thresholds or VentilatorThresholdConfig())
        self.ventilator_patients = self._load_ventilator_patients()
        self.active_alarms: Dict[str, str] = {}
        self.cycle_count = 0

    def _load_ventilator_patients(self) -> List[dict]:
        """Load patients connected to mechanical ventilation from shared contracts."""
        if not os.path.exists(MOCK_PATIENTS_PATH):
            return [
                {"patient_id": "P002", "room_id": "ROOM102", "name": "Marcus Brody", "devices_connected": ["VENTILATOR"]},
                {"patient_id": "P004", "room_id": "ROOM104", "name": "David Sterling", "devices_connected": ["VENTILATOR"]}
            ]
        with open(MOCK_PATIENTS_PATH, "r", encoding="utf-8") as f:
            patients = json.load(f)
        return [p for p in patients if "VENTILATOR" in p.get("devices_connected", [])]

    def post_event(self, event: dict) -> bool:
        """Send monitoring event to backend REST API."""
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
        """Log event advisory and dispatch to backend."""
        sev = event.get("severity")
        pid = event.get("patient_id")
        param = event.get("parameter")
        val = event.get("value")
        unit = event.get("unit")
        msg = event.get("message")

        if sev in ("CRITICAL", "HIGH"):
            logger.warning("🚨 [%s] %s %s (%s %s): %s", sev, pid, param, val, unit, msg)
        else:
            logger.info("   [VENT INFO] %s %s: %s %s", pid, param, val, unit)

        self.post_event(event)

    def trigger_demo_event(self, patient_id: str, scenario: str):
        """Demonstrate acute monitoring advisory events."""
        p = next((x for x in self.ventilator_patients if x["patient_id"] == patient_id), self.ventilator_patients[0])
        room_id = p.get("room_id", "ROOM102")

        logger.info("==================================================")
        logger.info("VENTILATOR DEMO ADVISORY: Scenario '%s' on %s (Room: %s)", scenario, patient_id, room_id)
        logger.info("Target Backend: %s", self.backend_url)
        logger.info("==================================================")

        event = self.processor.evaluate_scenario(patient_id=patient_id, room_id=room_id, scenario=scenario)
        self.emit_event(event)

    def run_continuous_monitoring(self, interval: float = 2.5):
        """Continuously simulate periodic monitoring telemetry without machine control commands."""
        logger.info("Starting continuous ventilator monitoring simulation (Target: %s)...", self.backend_url)
        try:
            while True:
                self.cycle_count += 1
                for p in self.ventilator_patients:
                    pid = p["patient_id"]
                    room = p.get("room_id", "ROOM102")
                    pip = round(21.0 + random.uniform(-1.0, 1.5), 1)
                    peep = round(6.0 + random.uniform(-0.4, 0.4), 1)
                    vt = int(480 + random.uniform(-15, 15))

                    event = self.processor.evaluate_telemetry(
                        patient_id=pid,
                        room_id=room,
                        pip=pip,
                        peep=peep,
                        tidal_volume=vt
                    )
                    self.emit_event(event)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Ventilator simulation stopped.")


def main():
    parser = argparse.ArgumentParser(description="Mechanical Ventilator Telemetry Simulator (Melisa)")
    parser.add_argument(
        "--backend",
        default=None,
        help="Backend URL (e.g. http://192.168.1.50:8000). Defaults to BACKEND_URL env var."
    )
    parser.add_argument(
        "--patient",
        default="P002",
        choices=["P002", "P004"],
        help="Target ventilator-connected patient"
    )
    parser.add_argument(
        "--scenario",
        choices=["HIGH_PRESSURE", "CIRCUIT_DISCONNECT", "APNEA", "NORMAL"],
        help="Demonstrate an acute advisory alarm event"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous periodic telemetry stream"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.5,
        help="Seconds between cycles"
    )
    args = parser.parse_args()

    simulator = VentilatorSimulator(backend_url=args.backend)

    if args.scenario:
        simulator.trigger_demo_event(patient_id=args.patient, scenario=args.scenario)
    elif args.continuous:
        simulator.run_continuous_monitoring(interval=args.interval)
    else:
        logger.info("No mode specified. Demonstrating HIGH_PRESSURE attention advisory on %s.", args.patient)
        simulator.trigger_demo_event(patient_id=args.patient, scenario="HIGH_PRESSURE")


if __name__ == "__main__":
    main()
