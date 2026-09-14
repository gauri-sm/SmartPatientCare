# Computer Vision Patient Surveillance & CCTV Evidence System 👁️📹

**Owner:** Gauri (`gauri/cv_patient_monitoring/` and `frontend/dashboard/` CCTV integration)  
**Purpose:** Real-time optical surveillance prototype for hospital bedside patient monitoring. Replaces classical MOG2 background subtraction with Ultralytics YOLO person detection coupled with explainable multi-frame temporal rules. Automatically links detected incidents with CCTV video evidence streamed directly onto the nursing station dashboard.

> [!IMPORTANT]
> **Prototype Disclaimer:** This software is an engineering hackathon prototype developed solely for educational and demonstration purposes. It is **NOT** a certified medical device, has **NOT** been clinically validated, and MUST NOT be used for real-time diagnostic or clinical decision-making.

---

## 🎯 Detection Capabilities & Explainable Temporal Rules

Instead of volatile single-frame thresholding or classical pixel background subtraction, this module combines single-model **Ultralytics YOLO person detection** (filtered strictly to COCO class `0`: person) with an **explainable multi-frame temporal state engine**:

1. **🚨 Fall Detection (`FALL_DETECTED` - CRITICAL):**
   - **Kinematic Rule:** Centroid downward drop velocity $\ge 18\text{ px/frame}$ or deep floor positioning ($y \ge y_{\text{bed}} + 0.95 \cdot h_{\text{bed}}$).
   - **Postural Rule:** Aspect ratio $h/w \le 0.70$ (horizontal lying posture).
   - **Temporal Rule:** Must persist across $\ge 5$ consecutive frames ($0.25\text{ s}$ at $20\text{ FPS}$) to avoid transient artifacts.
2. **⚠️ Patient Leaving Bed (`PATIENT_LEFT_BED` - WARNING):**
   - **Spatial Rule:** Patient centroid completely exits the calibrated Bed Region of Interest (Bed ROI).
   - **Temporal Rule:** Must persist outside bed for $\ge 10$ consecutive frames ($0.5\text{ s}$) before triggering alert.
3. **⚠️ Unusual Movement / Agitation (`ABNORMAL_MOVEMENT` - WARNING):**
   - **Kinematic Rule:** Sustained velocity displacement $\ge 22\text{ px/frame}$ while remaining in the bed area.
   - **Temporal Rule:** Must persist for $\ge 5$ consecutive frames.
4. **⚠️ Unusual Patient Position (`UNUSUAL_POSITION` - WARNING):**
   - **Spatial Rule:** Patient remains positioned at the precarious edge perimeter of the mattress ($< 16\%$ or $> 84\%$ of bed boundaries).
   - **Temporal Rule:** Must persist for $\ge 12$ consecutive frames.
5. **🛡️ Cooldown Debouncing:**
   - Alerts of the same state type are debounced with an 8-second cooldown timer to avoid flooding the nursing station or backend API.

---

## 📹 CCTV Video Evidence System

When a critical or warning event is generated, it is automatically bundled with CCTV video evidence metadata:
- `video_source`: Relative path or URL to the prerecorded CCTV video file (e.g., `demo/videos/room101.mp4`).
- `camera_id`: Camera feed identifier (e.g., `CAM101`, `CAM-ROOM101`).
- `evidence_type`: `CCTV_VIDEO`.

### Default Camera & Video Mappings:
| Patient ID | Room ID | Camera ID | Prerecorded Video Feed | Scenario |
|:---:|:---:|:---:|:---:|:---:|
| `P001` | `ROOM101` | `CAM101` | `demo/videos/room101.mp4` / `fall_demo.mp4` | Patient Fall Incident |
| `P002` | `ROOM102` | `CAM102` | `demo/videos/room102.mp4` | Agitation / Abnormal Movement |
| `P003` | `ROOM103` | `CAM103` | `demo/videos/room103.mp4` | Patient Left Bed |
| `P004` | `ROOM104` | `CAM104` | `demo/videos/room104.mp4` | Normal In-Bed Resting |

---

## 🏗️ Architecture & File Layout

```text
gauri/cv_patient_monitoring/
├── src/
│   ├── __init__.py           # Package exports (PatientCVDetector, YOLOPersonDetector, etc.)
│   ├── yolo_detector.py      # Ultralytics YOLO person detector wrapper (yolo11n.pt / yolov8n.pt)
│   ├── fall_detector.py      # Temporal state machine with explainable kinematic & postural rules
│   ├── cv_detector.py        # Integrated PatientCVDetector combining YOLO + Temporal Engine + HUD
│   ├── event_generator.py    # Schema-compliant event builder with CCTV metadata mapping
│   └── api_client.py         # HTTP client for POST /api/events with timeout & offline resilience
├── demo/
│   ├── generate_cctv_videos.py  # Generates realistic MP4 CCTV feeds with human figures
│   ├── demo_runner.py        # CLI video & simulation demo runner
│   └── videos/               # Prerecorded CCTV demo video files (.mp4)
├── tests/
│   ├── test_event_generator.py  # Validates JSON schema & CCTV metadata fields
│   └── test_cv_detector.py      # Unit tests for YOLO mock, temporal counters, fall rules & debouncing
└── README.md
```

---

## 💻 Installation & Dependencies

From the repository root:
```bash
pip install -r requirements.txt
```
Dependencies:
- `ultralytics>=8.3.0` (YOLO model inference)
- `opencv-python>=4.8.0` (Computer vision rendering & video I/O)
- `numpy>=1.24.0` (Array manipulations)

The YOLO model (`yolo11n.pt`, 5.4 MB) will automatically download to the repository directory on first run if not already present.

---

## 🎬 Running the System

### 1. Run YOLO CV Surveillance on Prerecorded CCTV Video
Processes video through YOLO person detection, executes temporal rules, and displays annotated output:
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py --video gauri/cv_patient_monitoring/demo/videos/fall_demo.mp4 --patient-id P001 --room-id ROOM101
```

### 2. Forward Events to FastAPI Backend
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py --video gauri/cv_patient_monitoring/demo/videos/fall_demo.mp4 --patient-id P001 --room-id ROOM101 --send-api
```

### 3. Display Real-time OpenCV Surveillance Window
```bash
python gauri/cv_patient_monitoring/demo/demo_runner.py --video gauri/cv_patient_monitoring/demo/videos/fall_demo.mp4 --show-window
```

### 4. Regenerate All CCTV Videos
```bash
python gauri/cv_patient_monitoring/demo/generate_cctv_videos.py
```

### 5. Launch the Nursing Station Dashboard
Start the local dashboard server (pure Python standard library, zero Node.js/npm dependencies):
```bash
python frontend/dashboard/serve.py 3000
```
Then navigate to:
```
http://localhost:3000
```
When a critical fall alert arrives (or when clicking **CCTV Evidence** in the alert list or patient card), the **CCTV Event Evidence Panel** slides open and streams the synchronised camera recording with timeline metadata.

---

## 🧪 Running Unit Tests

To run the unit test suite:
```bash
python -m unittest discover -s gauri/cv_patient_monitoring/tests -p "test_*.py"
```
All 13 unit tests execute without GPU hardware or external network access.
