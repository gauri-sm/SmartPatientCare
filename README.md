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
