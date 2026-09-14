# SmartPatientCare 🏥

An intelligent multi-patient monitoring and alerting platform for modern hospital nursing stations. **SmartPatientCare** integrates telemetry from patient vitals, ventilators, IV drip monitors, and computer-vision-based patient fall/movement detection into a unified, real-time alert and dashboard system.

---

## 👥 Team Ownership & Responsibilities

To ensure smooth collaboration during the hackathon and avoid merge conflicts, the codebase is partitioned into distinct module boundaries:

| Team Member | Core Folders & Modules | Primary Responsibilities |
| :--- | :--- | :--- |
| **GAURI** | `frontend/dashboard/`<br>`gauri/cv_patient_monitoring/` | • Nursing Station real-time UI/dashboard<br>• Computer vision fall detection (using prerecorded video)<br>• Alert UI integration & patient room status display |
| **MELISA** | `backend/`<br>`melisa/patient_device_monitoring/`<br>`simulator/device_simulator/`<br>`simulator/ventilator_simulator/` | • FastAPI backend core & REST/WebSocket APIs<br>• Database schemas and storage<br>• Patient vital signs & ECG simulation<br>• Ventilator telemetry simulation |
| **NIFA** | `nifa/drip_monitoring/`<br>`simulator/drip_simulator/` | • IV/drip rate & volume monitoring algorithms<br>• Drip telemetry simulator (empty drip, flow rate anomalies)<br>• Telemetry generation for infusion systems |
| **SANDRA** | `sandra/emergency_alerts/`<br>`simulator/emergency_simulator/` | • Emergency alert engine & prioritization logic<br>• Critical condition & emergency scenario simulation<br>• Integration testing across all modules |

---

## 📁 Repository Structure

```text
SmartPatientCare/
├── frontend/
│   └── dashboard/                  # [GAURI] Nursing Station dashboard application
├── backend/                        # [MELISA] Central FastAPI backend service
│   ├── api/                        # API route handlers & endpoints (REST/WebSocket)
│   ├── database/                   # Database connection, sessions, & migrations
│   ├── models/                     # Backend data models & ORM definitions
│   └── services/                   # Business logic, ingest, & telemetry dispatchers
├── gauri/                          # [GAURI] Computer Vision patient monitoring module
│   └── cv_patient_monitoring/
│       ├── src/                    # CV detection pipelines (fall detection, pose/motion)
│       ├── demo/                   # Prerecorded sample video demos & test clips
│       └── tests/                  # Unit tests for CV algorithms
├── melisa/                         # [MELISA] Patient device monitoring research & logic
│   └── patient_device_monitoring/
│       ├── src/                    # Vital signs & ECG processing logic
│       └── tests/                  # Tests for device monitoring algorithms
├── nifa/                           # [NIFA] IV drip monitoring module
│   └── drip_monitoring/
│       ├── src/                    # Infusion & drip rate tracking algorithms
│       └── tests/                  # Tests for drip rate calculation & alerts
├── sandra/                         # [SANDRA] Emergency alerts & alert engine
│   └── emergency_alerts/
│       ├── src/                    # Rules engine, alert deduplication, priority queue
│       └── tests/                  # Integration tests & alert engine tests
├── simulator/                      # System telemetry simulators
│   ├── device_simulator/          # [MELISA] Simulates patient vitals (HR, SpO2, BP)
│   ├── drip_simulator/            # [NIFA] Simulates IV drip flow rates & levels
│   ├── ventilator_simulator/      # [MELISA] Simulates ventilator pressure & respiration
│   └── emergency_simulator/       # [SANDRA] Simulates crisis scenarios & code blue triggers
├── shared/                         # Shared contracts across the entire team
│   ├── schemas/                    # Standardized JSON/Pydantic schemas (event_schema.json)
│   ├── constants/                  # System constants, enum definitions, thresholds
│   └── mock_data/                  # Mock patient and room configurations (patients.json)
└── docs/                           # Documentation
    ├── architecture/               # System diagrams & architecture specifications
    ├── api/                        # API documentation and payloads
    └── demo/                       # Hackathon presentation and demo walk-through scripts
```

---

## 📜 Shared Data Contracts

All modules (simulators, CV pipelines, backend, alert engine, and frontend) must adhere to shared contracts located in `shared/`:

- **Event Schema (`shared/schemas/event_schema.json`)**: All events published by simulators, CV monitoring, and device telemetry must strictly validate against this schema.
  - **Severity levels**: `INFO`, `WARNING`, `CRITICAL`
  - **Status levels**: `ACTIVE`, `ACKNOWLEDGED`, `RESOLVED`
- **Mock Patients (`shared/mock_data/patients.json`)**: Provides 4 standard patients (`P001` - `P004`) across rooms `ROOM101` - `ROOM104` for development and demo continuity.

---

## 🚀 Hackathon Guidelines

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for Git branch naming conventions, workflow instructions, and team collaboration rules.

---

## 💧 IV Drip Monitoring & Simulator (Nifa's Module)

### 📌 Overview
The IV Drip Monitoring module provides infusion tracking algorithms, flow anomaly detection, lifecycle alert management, and a telemetry simulation engine for hospital nursing stations.

> [!WARNING]
> **DISCLAIMER: Hackathon Demonstration Prototype Only**
> This system is designed and built solely for a 2-day hackathon presentation. It is **NOT** a certified medical device, clinical diagnostic tool, or validated infusion controller. All vital signs, fluid mechanics, and sensor readings are simulated.

### ⚙️ Implemented Features
1. **Mathematical Infusion Engine (`nifa/drip_monitoring/src/drip_calculator.py`)**:
   - Bi-directional conversion between flow rate (mL/h) and drop frequency (drops/min / gtt/min) across standard drop factors (10, 15, 20, 60 gtt/mL).
   - Real-time remaining fluid volume and percentage depletion tracking.
   - Dynamic estimated time to completion (ETA / Run-out time).
   - Flow rate variance calculation against physician target prescriptions.

2. **Safety Anomaly Detector (`nifa/drip_monitoring/src/anomaly_detector.py`)**:
   - **`NORMAL`** (INFO): Flow within normal ±10% range.
   - **`DRIP_VOLUME_LOW`** (WARNING): Fluid volume drops $\le 15\%$ (Equipment Alert).
   - **`DRIP_RATE_DEVIATION`** (WARNING): Unintended flow variation $\ge 20\%$ (Equipment Alert).
   - **`DRIP_OCCLUSION`** (CRITICAL): Complete line blockage / kink / closed clamp with fluid remaining (Equipment Alert).
   - **`DRIP_RUNAWAY`** (CRITICAL): Free-flow over-infusion $> 200\%$ prescribed rate (Patient & Equipment Alert).
   - **`DRIP_AIR_IN_LINE`** (CRITICAL): Air bubble detected in drip chamber/line (Equipment Alert).
   - **`DRIP_EMPTY / IV COMPLETED`** (CRITICAL): Bag completely empty (0 mL remaining).

3. **In-App Notification & Alert Manager (`nifa/drip_monitoring/src/alert_manager.py`)**:
   - Manages alert lifecycle: `ACTIVE` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `RESOLVED`.
   - Event deduplication and chronologically sorted severity queues.
   - Generates event payloads strictly conforming to `shared/schemas/event_schema.json`.

4. **Multi-Patient Infusion Coordinator (`nifa/drip_monitoring/src/infusion_manager.py`)**:
   - Integrates with `shared/mock_data/patients.json` for patients `P001` through `P004`.
   - Pre-configured with clinical mock prescriptions (Normal Saline, Norepinephrine, Lactated Ringer's, D5W).

5. **Telemetry Simulation Engine (`simulator/drip_simulator/`)**:
   - Physical IV fluid chamber simulation with time-stepped fluid consumption.
   - Instant scenario injection for hackathon demonstrations.
   - `DripTelemetryGenerator`: Validates all outgoing events against JSON Schema via `jsonschema`.

### 🖥️ Interactive Nursing Station Dashboard (`nifa/drip_monitoring/dashboard.py`)
Built with Streamlit for live demonstration without hospital hardware:
- Live multi-patient selector (`P001` - `P004`).
- Visual IV bag level progress bar and fluid depletion indicators.
- Live telemetry metrics: Flow Rate (mL/h), Drip Rate (gtt/min), Volume Remaining (mL), Run-out ETA.
- Prominent status banners: `NORMAL`, `WARNING`, `CRITICAL`, `IV COMPLETED`.
- Alert categorization: `[EQUIPMENT ALERT]` vs `[PATIENT ALERT]`.
- **Hackathon Demo Control Panel**: 1-click scenario triggers:
  - 🟢 Normal Infusion (100 mL/h)
  - 🟡 Low Volume Warning (10% left)
  - 🔴 Line Occlusion / Blockage (0 mL/h)
  - 🔴 Runaway Free-Flow (250 mL/h)
  - ⚠️ Air Bubble in Line
  - 🟣 IV Completed / Empty Bag (0 mL)
  - 🔄 Reset Bag (New 500 mL bag)
- Alert Station with **Acknowledge** and **Resolve** interaction.
- Live event inspection with strict schema validation badge.

### 🚀 How to Run & Demo

#### 1. Run Unit Tests (36 Tests)
```bash
python -m unittest discover -s nifa/drip_monitoring/tests -v
```

#### 2. Run Headless Simulator CLI
```bash
# Automated multi-scenario demo
python -m simulator.drip_simulator.cli --demo

# Specific scenario
python -m simulator.drip_simulator.cli --patient P001 --scenario CRITICAL_OCCLUSION
```

#### 3. Launch Interactive Nursing Station Dashboard
```bash
streamlit run nifa/drip_monitoring/dashboard.py
```
Open your browser at `http://localhost:8501`.

