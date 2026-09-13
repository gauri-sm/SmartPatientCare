# Contributing to SmartPatientCare 🤝

Welcome to the **SmartPatientCare** hackathon project! To ensure rapid development and prevent code collisions, please read and follow these collaboration guidelines carefully.

---

## 1. 🛡️ Module Isolation (Work in Your Assigned Folders)

To minimize merge conflicts and keep ownership clear, **each team member must work strictly inside their assigned directories**:

- **Gauri**:
  - `frontend/dashboard/`
  - `gauri/cv_patient_monitoring/`
- **Melisa**:
  - `backend/`
  - `melisa/patient_device_monitoring/`
  - `simulator/device_simulator/`
  - `simulator/ventilator_simulator/`
- **Nifa**:
  - `nifa/drip_monitoring/`
  - `simulator/drip_simulator/`
- **Sandra**:
  - `sandra/emergency_alerts/`
  - `simulator/emergency_simulator/`

> [!IMPORTANT]
> Avoid modifying files outside your designated directories without prior discussion with the module owner.

---

## 2. 🌿 Git Branching Strategy

- **Never commit directly to `main`**. The `main` branch is reserved for stable, integrated releases.
- **Always branch off from `main`** when starting new work:
  ```bash
  git checkout main
  git pull origin main
  git checkout -b <branch-name>
  ```
- **Branch Naming Convention**:
  Prefix all feature branches with your name and feature summary:
  - Gauri: `feature/gauri/<feature-name>` (e.g., `feature/gauri/fall-detection-pipeline`, `feature/gauri/dashboard-layout`)
  - Melisa: `feature/melisa/<feature-name>` (e.g., `feature/melisa/fastapi-setup`, `feature/melisa/vitals-simulator`)
  - Nifa: `feature/nifa/<feature-name>` (e.g., `feature/nifa/drip-calculation`, `feature/nifa/drip-simulator`)
  - Sandra: `feature/sandra/<feature-name>` (e.g., `feature/sandra/alert-engine`, `feature/sandra/integration-tests`)

---

## 3. 📦 Shared Directory Protocols (`shared/`)

The `shared/` directory holds the contract agreements for the entire system:
- `shared/schemas/event_schema.json` — Standardized event telemetry format
- `shared/mock_data/patients.json` — Standard patient IDs (`P001`-`P004`) and rooms (`ROOM101`-`ROOM104`)
- `shared/constants/` — System-wide shared constants

> [!WARNING]
> **Do NOT modify files in `shared/` unilaterally.**
> Any change to data structures or schemas affects all 4 components. Propose and agree on schema changes as a team before updating shared files.

---

## 4. 🧪 Testing & Integration

- Keep tests isolated inside your module's `tests/` directory.
- Verify that your module runs independently with mock data before connecting to the backend.
- Sandra coordinates overall system integration tests under `sandra/emergency_alerts/tests/`.

---

## 5. 🔀 Pull Requests & Merging

1. Push your branch to the remote repository.
2. Open a Pull Request targeting `main`.
3. Provide a brief description of the changes and any required environment variables/dependencies.
4. Request review from affected team members before merging.
