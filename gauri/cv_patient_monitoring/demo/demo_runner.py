"""
SmartPatientCare - YOLO Computer Vision Demo Runner
Author: Gauri (Frontend & CV Lead)

Demonstrates the real-time YOLO person detection & CCTV pipeline:
PRERECORDED CCTV VIDEO -> OpenCV reads frames sequentially
                       -> PatientCVDetector (YOLO + Temporal Rule Engine)
                       -> Renders annotated HUD frame (Bed ROI, Centroid, Posture)
                       -> Standardized event generated with CCTV metadata
                       -> Event sent to backend API (POST /api/events) if --send-api
                       -> Nursing dashboard displays alert and CCTV evidence video
"""

import sys
import os
import time
import argparse
import json
from typing import Optional

# Ensure clean UTF-8 printing on Windows PowerShell/CMD
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure parent and repo root directories are in sys.path
demo_dir = os.path.dirname(os.path.abspath(__file__))
module_dir = os.path.dirname(demo_dir)
repo_root = os.path.dirname(os.path.dirname(module_dir))

for path in [module_dir, repo_root]:
    if path and path not in sys.path:
        sys.path.insert(0, path)

import cv2

try:
    from src.cv_detector import PatientCVDetector, CVState
    from src.event_generator import CVEventGenerator, CCTV_VIDEO_MAPPING, CCTV_CAMERA_MAPPING
    from src.api_client import CVBackendClient
except ImportError:
    from gauri.cv_patient_monitoring.src.cv_detector import PatientCVDetector, CVState
    from gauri.cv_patient_monitoring.src.event_generator import (
        CVEventGenerator, CCTV_VIDEO_MAPPING, CCTV_CAMERA_MAPPING
    )
    from gauri.cv_patient_monitoring.src.api_client import CVBackendClient


def resolve_video_path(video_path: str) -> str:
    """
    Resolves relative or filename video paths against known video locations.
    """
    if not video_path:
        return ""
    if os.path.isabs(video_path) and os.path.exists(video_path):
        return video_path

    filename = os.path.basename(video_path)
    candidates = [
        video_path,
        os.path.join(repo_root, video_path),
        os.path.join(module_dir, video_path),
        os.path.join(demo_dir, video_path),
        os.path.join(module_dir, "demo", "videos", filename),
        os.path.join(repo_root, "gauri", "cv_patient_monitoring", "demo", "videos", filename),
        os.path.join(repo_root, "frontend", "dashboard", "videos", filename),
        os.path.join(demo_dir, "videos", filename)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return video_path


def resolve_model_path(model_path: str) -> str:
    """
    Resolves YOLO model file path if stored locally.
    """
    if os.path.isabs(model_path) and os.path.exists(model_path):
        return model_path

    candidates = [
        model_path,
        os.path.join(repo_root, model_path),
        os.path.join(module_dir, model_path),
        os.path.join(os.getcwd(), model_path)
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return model_path


def run_video_demo(
    video_path: str,
    patient_id: str = "P001",
    room_id: str = "ROOM101",
    model_path: str = "yolo11n.pt",
    confidence_threshold: float = 0.35,
    backend_url: str = "http://localhost:8000",
    send_api: bool = False,
    show_window: bool = False,
    output_video: Optional[str] = None
):
    """
    Runs real-time YOLO person detection and temporal rule evaluation
    on the supplied prerecorded video file.
    """
    resolved_video = resolve_video_path(video_path)
    resolved_model = resolve_model_path(model_path)

    print("=" * 68)
    print(f"🏥 SmartPatientCare YOLO Patient Surveillance & CCTV Demo")
    print(f"Patient: {patient_id} | Room: {room_id}")
    print(f"YOLO Model: {model_path} (Confidence: {confidence_threshold:.2f})")
    print(f"Video Source: {resolved_video}")
    print(f"Backend API: {backend_url} (Dispatch: {'ENABLED' if send_api else 'CONSOLE ONLY'})")
    if output_video:
        print(f"Output Video: {output_video}")
    if show_window:
        print(f"Display Window: ENABLED (Press 'q' in window to exit)")
    print("=" * 68)

    # Validate video file existence
    if not os.path.exists(resolved_video):
        print(f"\n❌ Error: Video file not found at: '{video_path}' (resolved: '{resolved_video}')")
        print("Please provide a valid video path via --video, or run:")
        print("    python gauri/cv_patient_monitoring/demo/generate_cctv_videos.py")
        print("to generate the sample CCTV test videos.\n")
        sys.exit(1)

    # 1. Open video with OpenCV VideoCapture
    cap = cv2.VideoCapture(resolved_video)
    if not cap.isOpened():
        print(f"\n❌ Error: Unable to open/decode video file '{resolved_video}' with OpenCV.")
        sys.exit(1)

    # 2. Initialize PatientCVDetector (loads YOLO person detector once)
    print("\n[INIT] Initializing YOLO Person Detector and Temporal Rule Engine...")
    detector = PatientCVDetector(
        patient_id=patient_id,
        room_id=room_id,
        model_path=resolved_model,
        confidence_threshold=confidence_threshold,
        video_source=video_path
    )
    api_client = CVBackendClient(backend_url=backend_url)

    # 3. Setup optional VideoWriter if --output is provided
    writer = None
    if output_video:
        out_path = os.path.abspath(output_video)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0 or fps > 120:
            fps = 20.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_path, fourcc, float(fps), (w, h))
        if not writer.isOpened():
            print(f"[WARN] Unable to open VideoWriter for '{out_path}'. Video will not be saved.")
            writer = None
        else:
            print(f"[OUTPUT] Recording annotated video to: {out_path}")

    detected_events = []
    frame_count = 0
    start_time = time.time()

    print(f"[STREAM STARTED] Processing CCTV feed from '{resolved_video}'...")
    try:
        # 4. Sequentially read and process video frames
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_count += 1

            # Real YOLO person detection + temporal state analysis
            state, event, annotated = detector.process_frame(frame)

            # Record annotated frame if writer active
            if writer is not None:
                writer.write(annotated)

            # 5. Handle and print detected events
            if event:
                detected_events.append(event)
                print("\n" + "!" * 68)
                print(f"🚨 [CV EVENT DETECTED] Type: {event.get('event_type')} | Severity: {event.get('severity')}")
                print(f"   Patient: {event.get('patient_id')} | Location: {event.get('room_id')}")
                print(f"   Message: {event.get('message')}")
                print(f"   CCTV Evidence: {event.get('video_source')} (Camera: {event.get('camera_id')})")
                print(f"   Event Payload:\n{json.dumps(event, indent=2)}")

                # Dispatch to backend API if enabled
                if send_api:
                    success = api_client.send_event(event)
                    if success:
                        print(f"   --> [API DISPATCH] Successfully forwarded to {backend_url}/api/events")
                    else:
                        print(f"   --> [API NOTICE] Backend not reachable at {backend_url}. Event queued.")
                print("!" * 68 + "\n")

            # 6. Display annotated frame if --show-window is enabled
            if show_window:
                cv2.imshow("SmartPatientCare YOLO CCTV Stream", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    print("\nUser requested video stream exit (pressed 'q'/ESC).")
                    break

    finally:
        # 7. Cleanly release VideoCapture, VideoWriter, and GUI windows
        cap.release()
        if writer is not None:
            writer.release()
            print(f"\nSaved annotated demo video to: {output_video}")
        if show_window:
            cv2.destroyAllWindows()

    elapsed = time.time() - start_time
    fps_avg = frame_count / max(0.001, elapsed)
    print("\n" + "=" * 68)
    print(f"✅ CCTV Demo processing complete.")
    print(f"Total Frames: {frame_count} | Elapsed: {elapsed:.2f}s ({fps_avg:.1f} FPS) | Events Triggered: {len(detected_events)}")
    print("=" * 68)


def run_simulation_demo(
    patient_id: str = "P001",
    room_id: str = "ROOM101",
    backend_url: str = "http://localhost:8000",
    send_api: bool = False
):
    """
    Simulation mode that demonstrates the clinical vision stages sequentially
    without requiring video decoding. Uses existing CVEventGenerator functions.
    """
    print("=" * 68)
    print(f"🏥 SmartPatientCare CV Demo (SIMULATION / PITCH MODE)")
    print(f"Patient: {patient_id} | Room: {room_id}")
    print(f"Backend API: {backend_url} (Dispatch: {'ENABLED' if send_api else 'CONSOLE ONLY'})")
    print(f"Demonstrating sequential event generation with CCTV video evidence metadata:")
    print(" 1. Normal Video In-Bed (Baseline resting)")
    print(" 2. Patient Agitation / Abnormal Movement (Restlessness alert)")
    print(" 3. Patient Left Bed (Vacated bed zone alert)")
    print(" 4. CRITICAL Patient Fall Detected (Triggers CCTV Evidence on Dashboard)")
    print("=" * 68)

    api_client = CVBackendClient(backend_url=backend_url)

    cctv_video = CCTV_VIDEO_MAPPING.get(patient_id, "demo/videos/room101.mp4")
    camera_id = CCTV_CAMERA_MAPPING.get(room_id, f"CAM-{room_id}")

    scenarios = [
        ("STAGE 1: Normal In-Bed", CVState.NORMAL, None),
        ("STAGE 2: Abnormal Movement / Agitation", CVState.ABNORMAL_MOVEMENT,
         CVEventGenerator.create_abnormal_movement_event(
             patient_id=patient_id,
             room_id=room_id,
             motion_score=86.4,
             video_source=CCTV_VIDEO_MAPPING.get("P002", "demo/videos/room102.mp4"),
             camera_id=CCTV_CAMERA_MAPPING.get(room_id, "CAM102")
         )),
        ("STAGE 3: Patient Left Bed", CVState.PATIENT_LEFT_BED,
         CVEventGenerator.create_patient_left_bed_event(
             patient_id=patient_id,
             room_id=room_id,
             video_source=CCTV_VIDEO_MAPPING.get("P003", "demo/videos/room103.mp4"),
             camera_id=CCTV_CAMERA_MAPPING.get(room_id, "CAM103")
         )),
        ("STAGE 4: CRITICAL Fall Detected", CVState.FALL_DETECTED,
         CVEventGenerator.create_fall_detected_event(
             patient_id=patient_id,
             room_id=room_id,
             confidence=0.96,
             video_source=cctv_video,
             camera_id=camera_id
         ))
    ]

    for title, state, event in scenarios:
        print(f"\n---> Now running: {title}")
        time.sleep(1.0)
        if event:
            print(f"🚨 [CV DETECTED]: {event['event_type']} ({event['severity']})")
            print(f"   Payload: {json.dumps(event, indent=2)}")
            if send_api:
                ok = api_client.send_event(event)
                status_str = "SUCCESS" if ok else "FAILED (Backend offline)"
                print(f"   --> Sent to Backend API: {status_str}")
        else:
            print(f"   Status: {state.value} (Normal resting - No abnormal events)")

    print("\n✅ Simulation demo finished successfully.")


def main():
    default_video = resolve_video_path("fall_demo.mp4")
    if not os.path.exists(default_video):
        default_video = "gauri/cv_patient_monitoring/demo/videos/fall_demo.mp4"

    parser = argparse.ArgumentParser(description="SmartPatientCare YOLO Patient Surveillance Demo")
    parser.add_argument("--mode", choices=["video", "simulate", "generate"], default="video",
                        help="Demo mode: video processing, simulation walkthrough, or video generation")
    parser.add_argument("--video", type=str, default=default_video,
                        help="Path to prerecorded video file")
    parser.add_argument("--patient-id", type=str, default="P001", help="Target patient ID")
    parser.add_argument("--room-id", type=str, default="ROOM101", help="Target room ID")
    parser.add_argument("--model", type=str, default="yolo11n.pt", help="Ultralytics model (e.g. yolo11n.pt or yolov8n.pt)")
    parser.add_argument("--confidence", type=float, default=0.35, help="YOLO person confidence threshold")
    parser.add_argument("--backend-url", type=str, default="http://localhost:8000", help="FastAPI backend URL")
    parser.add_argument("--send-api", action="store_true", help="Forward events to backend API")
    parser.add_argument("--show-window", action="store_true", help="Display OpenCV video window")
    parser.add_argument("--output", type=str, default=None, help="Save annotated output video path")
    parser.add_argument("--generate", action="store_true", help="Generate demo videos before running")

    args = parser.parse_args()

    if args.generate or args.mode == "generate":
        try:
            from gauri.cv_patient_monitoring.demo.generate_cctv_videos import main as gen_main
        except ImportError:
            from demo.generate_cctv_videos import main as gen_main
        gen_main()
        if args.mode == "generate":
            return

    if args.mode == "simulate":
        run_simulation_demo(
            patient_id=args.patient_id,
            room_id=args.room_id,
            backend_url=args.backend_url,
            send_api=args.send_api
        )
    else:
        run_video_demo(
            video_path=args.video,
            patient_id=args.patient_id,
            room_id=args.room_id,
            model_path=args.model,
            confidence_threshold=args.confidence,
            backend_url=args.backend_url,
            send_api=args.send_api,
            show_window=args.show_window,
            output_video=args.output
        )


if __name__ == "__main__":
    main()
