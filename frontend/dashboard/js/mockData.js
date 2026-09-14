/**
 * SmartPatientCare - Mock Data & Simulation Engine
 * Author: Gauri (Frontend & CV Lead)
 * 
 * Contains fictional patients P001-P004, baseline vitals, initial alerts,
 * and realistic telemetry event generators with CCTV evidence mapping.
 */

const MOCK_DATA = {
  // CCTV Video & Camera mappings
  cctvMapping: {
    "P001": { video: "videos/room101.mp4", camera: "CAM101", room: "ROOM101" },
    "P002": { video: "videos/room102.mp4", camera: "CAM102", room: "ROOM102" },
    "P003": { video: "videos/room103.mp4", camera: "CAM103", room: "ROOM103" },
    "P004": { video: "videos/room104.mp4", camera: "CAM104", room: "ROOM104" }
  },

  // 4 Fictional demo patients across rooms ROOM101-ROOM104
  patients: [
    {
      patient_id: "P001",
      room_id: "ROOM101",
      name: "Eleanor Vance",
      age: 72,
      gender: "Female",
      condition: "Post-operative Hip Replacement",
      status: "NORMAL", // NORMAL | WARNING | CRITICAL
      heart_rate: 74,
      spo2: 97,
      blood_pressure: "125/80",
      temperature: 36.8,
      respiratory_rate: 16,
      drip_status: "Normal",
      drip_rate: 100,
      drip_level: 65,
      active_alert_count: 0,
      cv_status: "Normal in bed",
      cv_last_event: null,
      devices: ["ECG_MONITOR", "PULSE_OXIMETER", "IV_DRIP", "CV_CAMERA"],
      assigned_doctor: "Dr. Sarah Chen",
      assigned_nurse: "Nurse Alex Taylor"
    },
    {
      patient_id: "P002",
      room_id: "ROOM102",
      name: "Marcus Brody",
      age: 58,
      gender: "Male",
      condition: "Acute Respiratory Distress (ARDS)",
      status: "CRITICAL",
      heart_rate: 112,
      spo2: 89,
      blood_pressure: "142/92",
      temperature: 38.4,
      respiratory_rate: 26,
      drip_status: "Low",
      drip_rate: 60,
      drip_level: 25,
      active_alert_count: 2,
      cv_status: "Unusual movement detected",
      cv_last_event: "ABNORMAL_MOVEMENT",
      devices: ["ECG_MONITOR", "PULSE_OXIMETER", "VENTILATOR", "IV_DRIP", "CV_CAMERA"],
      assigned_doctor: "Dr. Robert Martinez",
      assigned_nurse: "Nurse Jordan Lee"
    },
    {
      patient_id: "P003",
      room_id: "ROOM103",
      name: "Amina Al-Mansoor",
      age: 45,
      gender: "Female",
      condition: "Severe Dehydration & Electrolyte Imbalance",
      status: "NORMAL",
      heart_rate: 80,
      spo2: 98,
      blood_pressure: "118/76",
      temperature: 37.0,
      respiratory_rate: 15,
      drip_status: "Nearly Finished",
      drip_rate: 125,
      drip_level: 10,
      active_alert_count: 1,
      cv_status: "Normal in bed",
      cv_last_event: null,
      devices: ["ECG_MONITOR", "IV_DRIP", "CV_CAMERA"],
      assigned_doctor: "Dr. Sarah Chen",
      assigned_nurse: "Nurse Alex Taylor"
    },
    {
      patient_id: "P004",
      room_id: "ROOM104",
      name: "David Sterling",
      age: 67,
      gender: "Male",
      condition: "Congestive Heart Failure",
      status: "WARNING",
      heart_rate: 98,
      spo2: 92,
      blood_pressure: "148/96",
      temperature: 37.3,
      respiratory_rate: 22,
      drip_status: "Finished",
      drip_rate: 0,
      drip_level: 0,
      active_alert_count: 1,
      cv_status: "Patient in chair",
      cv_last_event: null,
      devices: ["ECG_MONITOR", "PULSE_OXIMETER", "VENTILATOR", "IV_DRIP", "CV_CAMERA"],
      assigned_doctor: "Dr. Robert Martinez",
      assigned_nurse: "Nurse Jordan Lee"
    }
  ],

  // Seed alert events matching shared/schemas/event_schema.json
  initialAlerts: [
    {
      event_id: "EVT-2026-001",
      timestamp: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
      event_type: "LOW_SPO2",
      patient_id: "P002",
      room_id: "ROOM102",
      source: "device_simulator",
      parameter: "spo2",
      value: 89,
      unit: "%",
      severity: "CRITICAL",
      message: "Patient SpO2 dropped below critical threshold (89%)",
      status: "ACTIVE",
      video_source: "videos/room102.mp4",
      camera_id: "CAM102",
      evidence_type: "CCTV_VIDEO"
    },
    {
      event_id: "EVT-2026-002",
      timestamp: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
      event_type: "PATIENT_ABNORMALITY",
      patient_id: "P002",
      room_id: "ROOM102",
      source: "computer_vision",
      parameter: "movement_intensity",
      value: "high",
      unit: "score",
      severity: "WARNING",
      message: "Unusual patient movement detected in bed (YOLO Person Tracking)",
      status: "ACTIVE",
      video_source: "videos/room102.mp4",
      camera_id: "CAM102",
      evidence_type: "CCTV_VIDEO"
    },
    {
      event_id: "EVT-2026-003",
      timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      event_type: "DRIP_NEARLY_FINISHED",
      patient_id: "P003",
      room_id: "ROOM103",
      source: "drip_sensor",
      parameter: "infusion_level",
      value: 10,
      unit: "%",
      severity: "WARNING",
      message: "Saline IV infusion bag level critical (<= 10% remaining)",
      status: "ACTIVE",
      video_source: "videos/room103.mp4",
      camera_id: "CAM103",
      evidence_type: "CCTV_VIDEO"
    },
    {
      event_id: "EVT-2026-004",
      timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
      event_type: "DRIP_FINISHED",
      patient_id: "P004",
      room_id: "ROOM104",
      source: "drip_sensor",
      parameter: "infusion_level",
      value: 0,
      unit: "%",
      severity: "WARNING",
      message: "IV drip infusion is empty/finished. Action required.",
      status: "ACTIVE",
      video_source: "videos/room104.mp4",
      camera_id: "CAM104",
      evidence_type: "CCTV_VIDEO"
    },
    {
      event_id: "EVT-2026-005",
      timestamp: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
      event_type: "VITALS_CHECK",
      patient_id: "P001",
      room_id: "ROOM101",
      source: "device_simulator",
      parameter: "vitals_routine",
      value: "stable",
      unit: "",
      severity: "INFO",
      message: "Scheduled routine vitals check completed - all parameters stable",
      status: "RESOLVED"
    }
  ],

  // Pre-configured simulated event scenarios for demo purposes
  demoScenarios: [
    {
      name: "CV Fall Detected in Room 101",
      event: {
        event_type: "FALL_DETECTED",
        patient_id: "P001",
        room_id: "ROOM101",
        source: "computer_vision",
        parameter: "fall_state",
        value: true,
        unit: "boolean",
        severity: "CRITICAL",
        message: "CRITICAL: Possible patient fall detected near bed area!",
        status: "ACTIVE",
        video_source: "videos/room101.mp4",
        camera_id: "CAM101",
        evidence_type: "CCTV_VIDEO"
      }
    },
    {
      name: "CV Patient Left Bed in Room 103",
      event: {
        event_type: "PATIENT_ABNORMALITY",
        patient_id: "P003",
        room_id: "ROOM103",
        source: "computer_vision",
        parameter: "bed_occupancy",
        value: "unoccupied",
        unit: "",
        severity: "WARNING",
        message: "Patient has vacated bed without nursing assistance (Unplanned exit)",
        status: "ACTIVE",
        video_source: "videos/room103.mp4",
        camera_id: "CAM103",
        evidence_type: "CCTV_VIDEO"
      }
    },
    {
      name: "Ventilator Disconnect Alarm in Room 102",
      event: {
        event_type: "VENTILATOR_DISCONNECT",
        patient_id: "P002",
        room_id: "ROOM102",
        source: "ventilator_simulator",
        parameter: "airway_pressure",
        value: 3,
        unit: "cmH2O",
        severity: "CRITICAL",
        message: "EMERGENCY: Ventilator circuit low pressure disconnect detected!",
        status: "ACTIVE",
        video_source: "videos/room102.mp4",
        camera_id: "CAM102",
        evidence_type: "CCTV_VIDEO"
      }
    },
    {
      name: "Tachycardia Spike in Room 104",
      event: {
        event_type: "HIGH_HEART_RATE",
        patient_id: "P004",
        room_id: "ROOM104",
        source: "device_simulator",
        parameter: "heart_rate",
        value: 142,
        unit: "bpm",
        severity: "CRITICAL",
        message: "Severe Sinus Tachycardia detected: Heart Rate 142 bpm",
        status: "ACTIVE",
        video_source: "videos/room104.mp4",
        camera_id: "CAM104",
        evidence_type: "CCTV_VIDEO"
      }
    },
    {
      name: "CV Unusual Patient Position in Room 101",
      event: {
        event_type: "PATIENT_ABNORMALITY",
        patient_id: "P001",
        room_id: "ROOM101",
        source: "computer_vision",
        parameter: "patient_position",
        value: "slumped_edge",
        unit: "",
        severity: "WARNING",
        message: "Unusual patient position detected - slumping towards bed edge",
        status: "ACTIVE",
        video_source: "videos/room101.mp4",
        camera_id: "CAM101",
        evidence_type: "CCTV_VIDEO"
      }
    }
  ],

  generateRandomEvent() {
    const templates = [
      {
        patient_id: "P001",
        room_id: "ROOM101",
        event_type: "PATIENT_ABNORMALITY",
        source: "computer_vision",
        parameter: "body_position",
        value: "unusual_orientation",
        unit: "",
        severity: "WARNING",
        message: "CV alert: Unusual patient position detected on bed boundary.",
        video_source: "videos/room101.mp4",
        camera_id: "CAM101",
        evidence_type: "CCTV_VIDEO"
      },
      {
        patient_id: "P001",
        room_id: "ROOM101",
        event_type: "FALL_DETECTED",
        source: "computer_vision",
        parameter: "fall_state",
        value: true,
        unit: "boolean",
        severity: "CRITICAL",
        message: "EMERGENCY: Vision detection triggered - patient fall detected on floor!",
        video_source: "videos/room101.mp4",
        camera_id: "CAM101",
        evidence_type: "CCTV_VIDEO"
      },
      {
        patient_id: "P002",
        room_id: "ROOM102",
        event_type: "ARRHYTHMIA_PVC",
        source: "device_simulator",
        parameter: "ecg_rhythm",
        value: "frequent_pvc",
        unit: "",
        severity: "WARNING",
        message: "Telemetry: Premature ventricular contractions observed in Lead II.",
        video_source: "videos/room102.mp4",
        camera_id: "CAM102",
        evidence_type: "CCTV_VIDEO"
      },
      {
        patient_id: "P003",
        room_id: "ROOM103",
        event_type: "DRIP_LOW",
        source: "drip_sensor",
        parameter: "infusion_level",
        value: 15,
        unit: "%",
        severity: "WARNING",
        message: "IV Drip: Infusion bag volume below 15%.",
        video_source: "videos/room103.mp4",
        camera_id: "CAM103",
        evidence_type: "CCTV_VIDEO"
      },
      {
        patient_id: "P004",
        room_id: "ROOM104",
        event_type: "RESPIRATORY_DISTRESS",
        source: "ventilator_simulator",
        parameter: "respiratory_rate",
        value: 29,
        unit: "rpm",
        severity: "CRITICAL",
        message: "Tachypnea warning: Respiratory rate elevated to 29 breaths/min.",
        video_source: "videos/room104.mp4",
        camera_id: "CAM104",
        evidence_type: "CCTV_VIDEO"
      }
    ];

    const chosen = templates[Math.floor(Math.random() * templates.length)];
    return {
      event_id: `EVT-${Date.now().toString().slice(-6)}`,
      timestamp: new Date().toISOString(),
      ...chosen,
      status: "ACTIVE"
    };
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = MOCK_DATA;
}
