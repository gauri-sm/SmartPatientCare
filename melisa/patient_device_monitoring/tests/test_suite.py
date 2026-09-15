"""Standalone test runner and validation suite for Melisa's device monitoring module.

Can be run with:
  python -m melisa.patient_device_monitoring.tests.test_suite
or with:
  pytest melisa/patient_device_monitoring/tests/
"""

import json
import os
import sys

# Ensure root directory is on PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from melisa.patient_device_monitoring.src.vitals_processor import (
    VitalsProcessor,
    VitalsThresholdConfig,
)
from melisa.patient_device_monitoring.src.ecg_analyzer import ECGAnalyzer
from melisa.patient_device_monitoring.src.ventilator_processor import (
    VentilatorProcessor,
    VentilatorThresholdConfig,
)
from simulator.device_simulator.vitals_simulator import normalize_backend_url
from simulator.ventilator_simulator.ventilator_simulator import (
    normalize_backend_url as normalize_vent_url,
)


def assert_event_contract(event: dict, test_name: str):
    """Verify that event meets all architectural criteria."""
    required_keys = [
        "event_id", "timestamp", "event_type", "patient_id", "room_id",
        "source", "parameter", "value", "unit", "severity", "message", "status"
    ]
    for k in required_keys:
        if k not in event or event[k] is None:
            raise AssertionError(f"[{test_name}] Missing or null key '{k}' in event: {event}")

    if event["status"] != "ACTIVE":
        raise AssertionError(f"[{test_name}] Status must be 'ACTIVE', got {event['status']}")

    if event["severity"] not in ("INFO", "LOW", "MEDIUM", "WARNING", "HIGH", "CRITICAL"):
        raise AssertionError(f"[{test_name}] Invalid severity '{event['severity']}'")

    # Ensure no CCTV / YOLO fields leaked into medical telemetry
    cctv_fields = ["camera_id", "video_source", "bounding_box", "yolo_confidence"]
    for c_field in cctv_fields:
        if c_field in event:
            raise AssertionError(f"[{test_name}] CCTV field '{c_field}' must NOT be in medical event")

    # Ensure JSON serializability
    json.dumps(event)


def run_all_tests() -> bool:
    """Run all verification tests and report pass/fail."""
    tests_run = 0
    tests_passed = 0

    print("==================================================")
    print("Running Melisa's Medical Device Monitoring Test Suite")
    print("==================================================")

    # 1. Normal values test
    tests_run += 1
    try:
        proc = VitalsProcessor()
        e_spo2 = proc.evaluate_spo2("P001", "ROOM101", 98.0)
        assert_event_contract(e_spo2, "test_normal_spo2")
        assert e_spo2["severity"] == "INFO"
        assert e_spo2["event_type"] == "VITAL_SIGN"

        e_hr = proc.evaluate_heart_rate("P001", "ROOM101", 75.0)
        assert_event_contract(e_hr, "test_normal_hr")
        assert e_hr["severity"] == "INFO"

        e_bp = proc.evaluate_blood_pressure("P001", "ROOM101", "120/80")
        assert_event_contract(e_bp, "test_normal_bp")
        assert e_bp["severity"] == "INFO"

        e_temp = proc.evaluate_temperature("P001", "ROOM101", 37.0)
        assert_event_contract(e_temp, "test_normal_temp")
        assert e_temp["severity"] == "INFO"

        e_rr = proc.evaluate_respiratory_rate("P001", "ROOM101", 16.0)
        assert_event_contract(e_rr, "test_normal_rr")
        assert e_rr["severity"] == "INFO"
        assert e_rr["event_type"] == "VITAL_SIGN"

        print(" [PASS] 1. Normal values (SpO2, HR, BP, Temp, RR -> INFO)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 1. Normal values: {exc}")

    # 2. LOW_SPO2 abnormal test
    tests_run += 1
    try:
        proc = VitalsProcessor()
        # High severity
        e_high = proc.evaluate_spo2("P002", "ROOM102", 92.0)
        assert_event_contract(e_high, "test_low_spo2_high")
        assert e_high["event_type"] == "LOW_SPO2"
        assert e_high["severity"] == "HIGH"

        # Critical severity
        e_crit = proc.evaluate_spo2("P002", "ROOM102", 87.0)
        assert_event_contract(e_crit, "test_low_spo2_crit")
        assert e_crit["event_type"] == "LOW_SPO2"
        assert e_crit["severity"] == "CRITICAL"

        print(" [PASS] 2. LOW_SPO2 abnormal events (HIGH & CRITICAL)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 2. LOW_SPO2 abnormal events: {exc}")

    # 3. ABNORMAL_HEART_RATE test
    tests_run += 1
    try:
        proc = VitalsProcessor()
        # Tachycardia HIGH
        e_tach_high = proc.evaluate_heart_rate("P004", "ROOM104", 112.0)
        assert_event_contract(e_tach_high, "test_abnormal_hr_high")
        assert e_tach_high["event_type"] == "ABNORMAL_HEART_RATE"
        assert e_tach_high["severity"] == "HIGH"

        # Tachycardia CRITICAL
        e_tach_crit = proc.evaluate_heart_rate("P004", "ROOM104", 135.0)
        assert_event_contract(e_tach_crit, "test_abnormal_hr_crit")
        assert e_tach_crit["event_type"] == "ABNORMAL_HEART_RATE"
        assert e_tach_crit["severity"] == "CRITICAL"

        # Bradycardia HIGH
        e_brady = proc.evaluate_heart_rate("P001", "ROOM101", 50.0)
        assert_event_contract(e_brady, "test_abnormal_hr_brady")
        assert e_brady["event_type"] == "ABNORMAL_HEART_RATE"
        assert e_brady["severity"] == "HIGH"

        print(" [PASS] 3. ABNORMAL_HEART_RATE events (Tachycardia & Bradycardia)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 3. ABNORMAL_HEART_RATE events: {exc}")

    # 4. ABNORMAL_BP test
    tests_run += 1
    try:
        proc = VitalsProcessor()
        # Hypertension HIGH
        e_bp_high = proc.evaluate_blood_pressure("P004", "ROOM104", "150/95")
        assert_event_contract(e_bp_high, "test_abnormal_bp_high")
        assert e_bp_high["event_type"] == "ABNORMAL_BP"
        assert e_bp_high["severity"] == "HIGH"

        # Hypertensive Crisis CRITICAL
        e_bp_crit = proc.evaluate_blood_pressure("P004", "ROOM104", "185/125")
        assert_event_contract(e_bp_crit, "test_abnormal_bp_crit")
        assert e_bp_crit["event_type"] == "ABNORMAL_BP"
        assert e_bp_crit["severity"] == "CRITICAL"

        print(" [PASS] 4. ABNORMAL_BP events (HIGH & CRITICAL)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 4. ABNORMAL_BP events: {exc}")

    # 5. ABNORMAL_TEMPERATURE test
    tests_run += 1
    try:
        proc = VitalsProcessor()
        # Fever MEDIUM
        e_fever = proc.evaluate_temperature("P002", "ROOM102", 38.5)
        assert_event_contract(e_fever, "test_abnormal_temp_medium")
        assert e_fever["event_type"] == "ABNORMAL_TEMPERATURE"
        assert e_fever["severity"] == "MEDIUM"

        # Hyperpyrexia HIGH
        e_hyper = proc.evaluate_temperature("P002", "ROOM102", 39.8)
        assert_event_contract(e_hyper, "test_abnormal_temp_high")
        assert e_hyper["event_type"] == "ABNORMAL_TEMPERATURE"
        assert e_hyper["severity"] == "HIGH"

        print(" [PASS] 5. ABNORMAL_TEMPERATURE events (MEDIUM & HIGH)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 5. ABNORMAL_TEMPERATURE events: {exc}")

    # 6. ABNORMAL_ECG test
    tests_run += 1
    try:
        # Normal rhythm
        e_ecg_norm = ECGAnalyzer.evaluate_rhythm("P001", "ROOM101", 72)
        assert_event_contract(e_ecg_norm, "test_ecg_norm")
        assert e_ecg_norm["event_type"] == "NORMAL_ECG"
        assert e_ecg_norm["severity"] == "INFO"

        # VTach CRITICAL
        e_vtach = ECGAnalyzer.evaluate_rhythm("P002", "ROOM102", 155)
        assert_event_contract(e_vtach, "test_ecg_vtach")
        assert e_vtach["event_type"] == "ABNORMAL_ECG"
        assert e_vtach["severity"] == "CRITICAL"

        # Asystole CRITICAL
        e_asystole = ECGAnalyzer.evaluate_rhythm("P001", "ROOM101", 0)
        assert_event_contract(e_asystole, "test_ecg_asystole")
        assert e_asystole["event_type"] == "ABNORMAL_ECG"
        assert e_asystole["severity"] == "CRITICAL"

        print(" [PASS] 6. ABNORMAL_ECG events (Normal -> VTach & Asystole CRITICAL)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 6. ABNORMAL_ECG events: {exc}")

    # 7. Threshold transition sequence test
    tests_run += 1
    try:
        proc = VitalsProcessor()
        spo2_sequence = [98.0, 97.0, 96.0, 94.0, 92.0, 90.0, 88.0]
        results = [proc.evaluate_spo2("P001", "ROOM101", val) for val in spo2_sequence]

        # 98, 97, 96 -> INFO
        assert all(r["severity"] == "INFO" for r in results[:3])
        # 94, 92 -> HIGH
        assert all(r["severity"] == "HIGH" for r in results[3:5])
        # 90, 88 -> CRITICAL
        assert all(r["severity"] == "CRITICAL" for r in results[5:])

        print(" [PASS] 7. Stepwise threshold transition (98 -> 92 -> 88% SpO2)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 7. Stepwise threshold transition: {exc}")

    # 8. Multi-laptop URL normalization test
    tests_run += 1
    try:
        url1 = normalize_backend_url("http://192.168.1.100:8000")
        assert url1 == "http://192.168.1.100:8000/api/events"

        url2 = normalize_backend_url("http://10.0.0.5:8000/api/events/")
        assert url2 == "http://10.0.0.5:8000/api/events"

        vent_url = normalize_vent_url("http://192.168.1.200:8000")
        assert vent_url == "http://192.168.1.200:8000/api/events"

        print(" [PASS] 8. Multi-laptop remote URL normalization (BACKEND_URL)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 8. Multi-laptop URL normalization: {exc}")

    # 9. ABNORMAL_RESPIRATORY_RATE test
    tests_run += 1
    try:
        proc = VitalsProcessor()
        # Tachypnea HIGH (>20 breaths/min)
        e_rr_high = proc.evaluate_respiratory_rate("P002", "ROOM102", 24.0)
        assert_event_contract(e_rr_high, "test_abnormal_rr_high")
        assert e_rr_high["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
        assert e_rr_high["severity"] == "HIGH"
        assert e_rr_high["parameter"] == "respiratory_rate"
        assert e_rr_high["value"] == 24.0
        assert e_rr_high["unit"] == "breaths/min"

        # Tachypnea CRITICAL (>=30 breaths/min)
        e_rr_crit = proc.evaluate_respiratory_rate("P002", "ROOM102", 34.0)
        assert_event_contract(e_rr_crit, "test_abnormal_rr_crit")
        assert e_rr_crit["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
        assert e_rr_crit["severity"] == "CRITICAL"

        # Bradypnea HIGH (<12 breaths/min)
        e_rr_low = proc.evaluate_respiratory_rate("P001", "ROOM101", 10.0)
        assert_event_contract(e_rr_low, "test_abnormal_rr_low")
        assert e_rr_low["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
        assert e_rr_low["severity"] == "HIGH"

        # Bradypnea CRITICAL (<=8 breaths/min)
        e_rr_crit_low = proc.evaluate_respiratory_rate("P001", "ROOM101", 6.0)
        assert_event_contract(e_rr_crit_low, "test_abnormal_rr_crit_low")
        assert e_rr_crit_low["event_type"] == "ABNORMAL_RESPIRATORY_RATE"
        assert e_rr_crit_low["severity"] == "CRITICAL"

        # Batch evaluation
        batch = {
            "spo2": 98,
            "heart_rate": 75,
            "blood_pressure": "120/80",
            "temperature": 36.8,
            "respiratory_rate": 16
        }
        batch_events = proc.evaluate_all("P001", "ROOM101", batch)
        assert len(batch_events) == 5
        rr_in_batch = next(e for e in batch_events if e["parameter"] == "respiratory_rate")
        assert rr_in_batch["event_type"] == "VITAL_SIGN"
        assert rr_in_batch["severity"] == "INFO"

        print(" [PASS] 9. ABNORMAL_RESPIRATORY_RATE events & batch evaluation")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 9. ABNORMAL_RESPIRATORY_RATE events: {exc}")

    # 10. Ventilator monitoring processor test
    tests_run += 1
    try:
        vent_proc = VentilatorProcessor()

        # Normal telemetry
        e_norm = vent_proc.evaluate_telemetry("P002", "ROOM102", 22.0, 6.0, 480.0)
        assert_event_contract(e_norm, "test_vent_norm")
        assert e_norm["event_type"] == "VENTILATOR_TELEMETRY"
        assert e_norm["severity"] == "INFO"

        # High pressure CRITICAL
        e_hp = vent_proc.evaluate_pip("P002", "ROOM102", 41.5)
        assert_event_contract(e_hp, "test_vent_hp")
        assert e_hp["event_type"] == "VENTILATOR_ALERT"
        assert e_hp["severity"] == "CRITICAL"

        # Circuit disconnect CRITICAL
        e_cd = vent_proc.evaluate_peep("P002", "ROOM102", 1.2)
        assert_event_contract(e_cd, "test_vent_cd")
        assert e_cd["event_type"] == "VENTILATOR_ALERT"
        assert e_cd["severity"] == "CRITICAL"

        # Apnea CRITICAL
        e_ap = vent_proc.evaluate_apnea("P004", "ROOM104", True)
        assert_event_contract(e_ap, "test_vent_ap")
        assert e_ap["event_type"] == "VENTILATOR_ALERT"
        assert e_ap["severity"] == "CRITICAL"

        print(" [PASS] 10. Ventilator monitoring processor (Normal, High Pressure, Disconnect, Apnea)")
        tests_passed += 1
    except Exception as exc:
        print(f" [FAIL] 10. Ventilator monitoring processor: {exc}")

    print("==================================================")
    print(f"Results: {tests_passed}/{tests_run} tests passed.")
    print("==================================================")
    return tests_passed == tests_run


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
