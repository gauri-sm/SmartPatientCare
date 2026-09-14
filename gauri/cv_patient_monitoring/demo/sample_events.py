"""
SmartPatientCare - Sample CV Event Generator & Dispatcher
Author: Gauri (Frontend & CV Lead)

Generates sample computer vision event payloads for testing.
"""

import sys
import os
import json

# Ensure clean UTF-8 printing
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.event_generator import CVEventGenerator
from src.api_client import CVBackendClient

def generate_sample_events():
    return {
        "fall_detected": CVEventGenerator.create_fall_detected_event(
            patient_id="P001",
            room_id="ROOM101",
            confidence=0.96,
            message="CRITICAL: Patient fall detected on floor beside bed!"
        ),
        "patient_left_bed": CVEventGenerator.create_patient_left_bed_event(
            patient_id="P003",
            room_id="ROOM103",
            message="WARNING: Patient has unassistedly exited bed perimeter."
        ),
        "abnormal_movement": CVEventGenerator.create_abnormal_movement_event(
            patient_id="P002",
            room_id="ROOM102",
            motion_score=94.5,
            message="ALERT: High erratic movement/agitation detected in bed."
        ),
        "unusual_position": CVEventGenerator.create_unusual_position_event(
            patient_id="P001",
            room_id="ROOM101",
            posture_description="slumped_edge",
            message="WARNING: Patient slumped precariously near edge of mattress."
        )
    }

def main():
    events = generate_sample_events()
    print("=" * 60)
    print("🏥 SmartPatientCare - Sample Computer Vision Event Payloads")
    print("=" * 60)

    for name, evt in events.items():
        print(f"\n--- Event Type: {evt['event_type']} (Scenario: {name}) ---")
        print(json.dumps(evt, indent=2))

    if "--send" in sys.argv:
        backend_url = "http://localhost:8000"
        for arg in sys.argv:
            if arg.startswith("--url="):
                backend_url = arg.split("=")[1]
        
        client = CVBackendClient(backend_url)
        print(f"\nDispatching events to {backend_url}/api/events...")
        for name, evt in events.items():
            success = client.send_event(evt)
            print(f" -> Sent {name}: {'SUCCESS' if success else 'FAILED (Backend unreachable)'}")

if __name__ == "__main__":
    main()
