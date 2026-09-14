"""Command-Line Interface for SmartPatientCare IV Drip Simulator.

Runs the demo sequence:
NORMAL DRIP -> DRIP LOW -> DRIP FINISHED
(100% -> 80% -> 60% -> 40% -> 20% -> 10% -> 5% -> 0%)

Emits:
- DRIP_LOW (when crossing configured low threshold)
- DRIP_FINISHED (when reaching 0%)
with duplicate event suppression.

Sends events to POST /api/events using configurable BACKEND_URL.
No CCTV/video dependencies.

Usage:
    python -m simulator.drip_simulator.cli
    python -m simulator.drip_simulator.cli --backend-url http://192.168.1.50:8000
    python -m simulator.drip_simulator.cli --patient P002 --room ROOM102
"""

import argparse
import json
import os
import sys

from .drip_simulator import IVDripSimulator
from nifa.drip_monitoring.src.constants import (
    DEFAULT_BACKEND_URL,
    DEFAULT_LOW_THRESHOLD_PCT,
    DEFAULT_LOW_SEVERITY,
    DEFAULT_FINISHED_SEVERITY,
)


def main():
    parser = argparse.ArgumentParser(
        description="SmartPatientCare IV Drip Telemetry Simulator (Nifa's Component)"
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        default=os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL),
        help=f"Target backend URL for POST /api/events (default: {DEFAULT_BACKEND_URL})",
    )
    parser.add_argument(
        "--patient",
        type=str,
        default="P001",
        help="Patient ID (default: P001)",
    )
    parser.add_argument(
        "--room",
        type=str,
        default="ROOM101",
        help="Room ID (default: ROOM101)",
    )
    parser.add_argument(
        "--low-threshold",
        type=float,
        default=DEFAULT_LOW_THRESHOLD_PCT,
        help=f"Low drip volume threshold percentage (default: {DEFAULT_LOW_THRESHOLD_PCT}%%)",
    )
    parser.add_argument(
        "--low-severity",
        type=str,
        default=DEFAULT_LOW_SEVERITY,
        help=f"Severity for DRIP_LOW (default: {DEFAULT_LOW_SEVERITY})",
    )
    parser.add_argument(
        "--finished-severity",
        type=str,
        default=DEFAULT_FINISHED_SEVERITY,
        help=f"Severity for DRIP_FINISHED (default: {DEFAULT_FINISHED_SEVERITY})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Delay between sequence steps in seconds (default: 0.4)",
    )
    parser.add_argument(
        "--sequence",
        type=str,
        default="100,80,60,40,20,10,5,0",
        help="Comma-separated percentage sequence (default: 100,80,60,40,20,10,5,0)",
    )
    parser.add_argument(
        "--level",
        type=float,
        default=None,
        help="Set a single fluid level percentage instead of running sequence",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("[+] SmartPatientCare - IV Drip Telemetry Simulator")
    print(f"    Owner: Nifa | Patient: {args.patient} | Room: {args.room}")
    print(f"    Target Backend: {args.backend_url}/api/events")
    print(f"    Low Threshold: <= {args.low_threshold:.0f}% (Severity: {args.low_severity})")
    print(f"    Finished Threshold: 0% (Severity: {args.finished_severity})")
    print("=" * 70)

    sim = IVDripSimulator(
        patient_id=args.patient,
        room_id=args.room,
        low_threshold_pct=args.low_threshold,
        low_severity=args.low_severity,
        finished_severity=args.finished_severity,
        backend_url=args.backend_url,
    )

    if args.level is not None:
        print(f"\nEvaluating single level: {args.level:.1f}%")
        event = sim.set_level_pct(args.level)
        if event:
            print("\nGenerated Event:")
            print(json.dumps(event, indent=2))
        else:
            print(f"State: {sim.current_state.value} (No new event emitted - duplicate suppressed or normal)")
    else:
        seq_levels = [float(x.strip()) for x in args.sequence.split(",")]
        print(f"\nExecuting sequence: {seq_levels}\n")
        events = sim.run_sequence(seq_levels, delay_seconds=args.delay)

        print("\n" + "=" * 70)
        print(f"[SUMMARY] Total State Transition Events Emitted: {len(events)}")
        for idx, evt in enumerate(events, 1):
            print(f"\n--- Event #{idx}: {evt['event_type']} ---")
            print(json.dumps(evt, indent=2))
        print("=" * 70)


if __name__ == "__main__":
    main()
