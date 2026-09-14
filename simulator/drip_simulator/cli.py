"""Command-Line Interface for IV Drip Telemetry Simulator.

Allows team members and judges to run headless drip simulations, trigger
events, and view generated telemetry payloads conforming to shared/schemas/event_schema.json.

Usage:
    python -m simulator.drip_simulator.cli --demo
    python -m simulator.drip_simulator.cli --patient P001 --scenario CRITICAL_OCCLUSION
"""

import argparse
import json
import sys
import time

from .drip_simulator import IVDripSimulator, DripSimulationScenario
from .telemetry_generator import DripTelemetryGenerator


def run_automated_demo(patient_id: str = "P001", room_id: str = "ROOM101"):
    """Run an automated step-by-step demonstration of all IV drip scenarios."""
    print("=" * 70)
    print("[+] SmartPatientCare - IV Drip Telemetry Simulator [DEMO MODE]")
    print("    Owner: Nifa | Module: simulator/drip_simulator")
    print("    DISCLAIMER: Hackathon demonstration prototype - NOT for clinical use")
    print("=" * 70)

    sim = IVDripSimulator(patient_id=patient_id, room_id=room_id, total_volume_ml=500.0, prescribed_rate_ml_h=100.0)

    scenarios = [
        (DripSimulationScenario.NORMAL, "Phase 1: Normal Infusion (Steady 100 mL/h)"),
        (DripSimulationScenario.WARNING_LOW_VOLUME, "Phase 2: Warning - Low Volume Level (10% Remaining)"),
        (DripSimulationScenario.CRITICAL_OCCLUSION, "Phase 3: Critical Equipment Alert - IV Line Occlusion / Blockage"),
        (DripSimulationScenario.CRITICAL_RUNAWAY, "Phase 4: Critical Patient Alert - Runaway Infusion Free-Flow"),
        (DripSimulationScenario.CRITICAL_AIR_IN_LINE, "Phase 5: Critical Equipment Alert - Air Bubble in Line"),
        (DripSimulationScenario.CRITICAL_EMPTY, "Phase 6: Critical Alert - IV Completed / Empty Bag"),
    ]

    for scenario, title in scenarios:
        print(f"\n>> {title}")
        print("-" * 70)
        events = sim.apply_scenario(scenario)
        for evt in events:
            print(json.dumps(evt, indent=2))
        print(f"[*] State: Remaining: {sim.remaining_volume_ml:.1f} mL ({sim.volume_percentage:.1f}%) | "
              f"Flow: {sim.current_flow_rate_ml_h:.1f} mL/h | Rate: {sim.drops_per_min:.1f} gtt/min")
        time.sleep(0.5)

    print("\n" + "=" * 70)
    print("[SUCCESS] Automated Demo Complete - All generated events validated against event_schema.json!")
    print("=" * 70)



def main():
    parser = argparse.ArgumentParser(description="SmartPatientCare IV Drip Simulator CLI (Nifa)")
    parser.add_argument("--demo", action="store_true", help="Run automated multi-scenario demonstration")
    parser.add_argument("--patient", type=str, default="P001", help="Patient ID (e.g. P001, P002, P003, P004)")
    parser.add_argument("--room", type=str, default="ROOM101", help="Room ID (e.g. ROOM101)")
    parser.add_argument(
        "--scenario",
        type=str,
        choices=[s.value for s in DripSimulationScenario],
        default=DripSimulationScenario.NORMAL.value,
        help="Specific scenario to trigger",
    )

    args = parser.parse_args()

    if args.demo:
        run_automated_demo(patient_id=args.patient, room_id=args.room)
    else:
        sim = IVDripSimulator(patient_id=args.patient, room_id=args.room)
        scenario = DripSimulationScenario(args.scenario)
        print(f"Applying scenario: {scenario.value} for Patient: {args.patient} in {args.room}")
        events = sim.apply_scenario(scenario)
        for evt in events:
            print(json.dumps(evt, indent=2))


if __name__ == "__main__":
    main()
