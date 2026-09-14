# Computer Vision Demo Instructions 🎥

**Module:** `gauri/cv_patient_monitoring/demo/`  
**Author:** Gauri (Frontend & CV Lead)

This guide explains how to demonstrate the computer vision patient surveillance prototype during the hackathon presentation without requiring physical cameras or external hardware.

---

## 🎬 Demo Workflow

The demo showcases the complete end-to-end event lifecycle:

```text
NORMAL VIDEO STREAM
         ↓
Patient abnormal movement / fall
         ↓
CV detects event (Bounding box, velocity & Bed ROI analysis)
         ↓
CV creates standardized event payload
         ↓
Event transmitted to Backend API (POST /api/events)
         ↓
Nursing Dashboard receives real-time alert (WebSocket /ws/alerts)
```

---

## 🚀 Running the Demos

All commands can be executed from the repository root:

### Option 1: End-to-End Video Demo (Recommended)
This runs the detector against a synthetic hospital bedside video (generating it automatically if not present):
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py
```
To forward detected events to the FastAPI backend:
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py --send-api
```
To save the annotated video with visual bounding boxes, Bed ROI, and HUD overlay:
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py --output demo/annotated_output.mp4
```

### Option 2: Step-by-Step Simulation Mode (Ultra-Reliable Pitch Mode)
If presenting in a fast-paced environment or without video decoding:
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py --mode simulate
```
Or with backend forwarding:
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py --mode simulate --send-api
```

### Option 3: Using Your Own Prerecorded Video
If you recorded a custom MP4 or smartphone clip of a simulated patient:
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py --video path/to/my_video.mp4 --patient-id P001 --room-id ROOM101
```

### Option 4: Inspecting Sample Event Payloads
To verify JSON schema conformance:
```bash
python gauri/cv_patient_monitoring/demo/sample_events.py
```

---

## ⚠️ Presentation Disclaimer

> [!CAUTION]
> **Engineering Prototype Notice:**  
> This system is built for a hackathon proof-of-concept. It is NOT medically certified or clinically validated. Always state during your presentation that this is an engineering research prototype designed to demonstrate software architecture and multimodal telemetry fusion.
