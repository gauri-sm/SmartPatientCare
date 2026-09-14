# SmartPatientCare — Nursing Station Dashboard 🏥

**Owner:** Gauri (`frontend/dashboard/`)  
**Purpose:** Real-time central monitoring console for hospital nursing stations. Integrates telemetry from simulated patient monitors, IV drip sensors, ventilator units, and computer vision surveillance into an intuitive hospital dashboard.

---

## 🚀 Quick Start

The dashboard requires **no Node.js or npm dependencies**. It runs in any modern browser directly.

### Option 1: Using the built-in lightweight Python server (Recommended)
From this directory:
```bash
python serve.py
```
Or specify a custom port:
```bash
python serve.py 3000
```
Then open: **`http://localhost:3000`**

### Option 2: Open directly in browser
Double-click `index.html` or open it directly in Chrome, Edge, or Firefox.

---

## 🌟 Dashboard Features

1. **Header & System Telemetry Status:**
   - Hospital brand logo and "Nursing Station" badge.
   - Dynamic system status pill:
     - 🟢 `WebSocket Live` (connected to real backend)
     - 🟡 `REST Live (WS Offline)`
     - 🔵 `Simulated Mode (Standalone)` (offline fallback)
   - Real-time digital clock and date.
   - Total active alerts counter badge.

2. **Patient Overview (Fictional Demo Patients P001 - P004):**
   - **P001 - Room 101:** Eleanor Vance (72F, Post-op Hip Replacement)
   - **P002 - Room 102:** Marcus Brody (58M, ARDS - Critical)
   - **P003 - Room 103:** Amina Al-Mansoor (45F, Dehydration & Electrolyte Imbalance)
   - **P004 - Room 104:** David Sterling (67M, Congestive Heart Failure)
   - Live vitals preview: HR, SpO2, BP, Resp rate, Temp, IV Drip status, and active alert counter.
   - Visual status indicators: `NORMAL`, `WARNING`, `CRITICAL` with pulse glow.
   - Clicking any patient card selects them into the Detailed Monitoring Workspace.

3. **Vital Monitoring & ECG Oscilloscope (Selected Patient):**
   - Real-time HTML5 Canvas ECG oscilloscope rendering Lead II P-Q-R-S-T rhythm with glowing green phosphor beam.
   - Dynamic heart rate coupling (oscilloscope sweep phase adapts to patient BPM).
   - High-contrast numerical vitals: Heart Rate (with animated heartbeat), SpO2, Blood Pressure, Respiratory Rate, and Temperature.

4. **IV Drip Status Monitor:**
   - Visual infusion bag graphic with fill level percentage.
   - Statuses: `Normal`, `Low`, `Nearly Finished`, `Finished`.
   - Live infusion rate display in ml/hr.

5. **Computer Vision Surveillance Feed:**
   - Displays real-time CV surveillance state:
     - `Normal in bed`
     - `FALL DETECTED`
     - `PATIENT LEFT BED`
     - `ABNORMAL MOVEMENT`
     - `UNUSUAL POSITION`
   - Feed activity timestamp and status callout.

6. **Real-Time Alert Center & Action Buttons:**
   - Filter tabs: `Active`, `Critical`, `All`, `Resolved`.
   - Detailed event metadata: Severity (`INFO`, `WARNING`, `CRITICAL`), Patient ID, Room, Source (`computer_vision`, `device_simulator`, etc.), event type, and message.
   - Action buttons:
     - **Acknowledge:** Updates state to `ACKNOWLEDGED`.
     - **Resolve:** Marks event as `RESOLVED`.
   - Clicking an alert automatically selects the relevant patient for inspection.

7. **Prominent Emergency Notification Modal:**
   - Automatically surfaces when a `CRITICAL` or `FALL_DETECTED` event occurs.
   - Highlights room location, timestamp, and emergency message.
   - Provides quick "Acknowledge & Attend Room" action.

8. **⚡ Quick Demo Control Bar:**
   - Pre-configured buttons to instantly demonstrate:
     - `🚨 Trigger CV Fall (R101)`
     - `⚠️ Trigger CV Left Bed (R103)`
     - `⚠️ Trigger CV Position (R101)`
     - `💨 Ventilator Alarm (R102)`
     - `❤️ Tachycardia (R104)`
     - `Auto-Sim: ON/OFF` (toggle autonomous hospital telemetry generator)

---

## 🔌 Backend Integration Interface

The dashboard is built to seamlessly integrate with Melisa's FastAPI backend:

- **Configuration:** [`js/config.js`](js/config.js)
  - `BACKEND_URL`: defaults to `http://localhost:8000` (override via `window.ENV_BACKEND_URL`).
- **REST Endpoints:**
  - `GET /api/patients` — List patients
  - `GET /api/patients/{id}` — Single patient details
  - `GET /api/events` — All events
  - `GET /api/events/active` — Active/unresolved events
  - `POST /api/events` — Ingest new event
  - `POST /api/events/{id}/acknowledge` — Acknowledge alert
  - `POST /api/events/{id}/resolve` — Resolve alert
- **WebSocket:**
  - `/ws/alerts` — Real-time event broadcasting
- **Graceful Offline Fallback:**
  - If the backend or WebSocket is unavailable, the dashboard automatically falls back to [`js/mockData.js`](js/mockData.js) and initiates internal simulation without crashing.

---

## 📁 File Structure

```text
frontend/dashboard/
├── index.html           # Main nursing station interface
├── css/
│   └── style.css        # Clinical dark-theme styles & animations
├── js/
│   ├── config.js        # Backend endpoints and environment configuration
│   ├── mockData.js      # Seed patients, baseline vitals, initial alerts & scenarios
│   ├── apiService.js    # REST API & WebSocket client with offline fallback
│   ├── ecgWaveform.js   # Real-time HTML5 Canvas ECG oscilloscope renderer
│   └── dashboard.js     # UI event handling, state coordination, and alerts
├── serve.py             # Zero-dependency Python server
└── README.md            # Documentation & setup guide
```

---

## ⚠️ Medical Disclaimer

This software is an engineering prototype developed for a hackathon demonstration. It does **not** provide medical diagnoses, clinical decision support, or direct control of medical hardware. All patient names, rooms, and telemetry values are entirely fictional.
