"""
Unit tests for Sandra's Priority Alert Manager
"""

from sandra.emergency_alerts.src.priority_queue import PriorityAlertManager
from sandra.emergency_alerts.src.models import (
    SmartPatientCareEvent,
    SeverityLevel,
    AlertStatus,
)


def create_event(pid, param, sev, val, unit="bpm"):
    return SmartPatientCareEvent(
        event_id=f"ev_{pid}_{param}",
        timestamp="2026-09-14T12:00:00Z",
        event_type="VITAL_SIGN",
        patient_id=pid,
        room_id="ROOM101",
        source="test",
        parameter=param,
        value=val,
        unit=unit,
        severity=sev,
        message=f"{sev.value} on {param}",
        status=AlertStatus.ACTIVE,
    )


def test_priority_ordering():
    mgr = PriorityAlertManager()

    # Ingest INFO, WARNING, CRITICAL
    ev_info = create_event("P001", "temp", SeverityLevel.INFO, 37.4, "°C")
    ev_crit = create_event("P002", "spo2", SeverityLevel.CRITICAL, 82, "%")
    ev_warn = create_event("P003", "hr", SeverityLevel.WARNING, 115, "bpm")

    mgr.ingest_event(ev_info, "Patient 1")
    mgr.ingest_event(ev_crit, "Patient 2")
    mgr.ingest_event(ev_warn, "Patient 3")

    alerts = mgr.get_all_alerts()
    assert len(alerts) == 3
    # Top alert must be CRITICAL
    assert alerts[0].severity == SeverityLevel.CRITICAL
    assert alerts[0].patient_id == "P002"
    # Second must be WARNING
    assert alerts[1].severity == SeverityLevel.WARNING
    assert alerts[1].patient_id == "P003"
    # Third must be INFO
    assert alerts[2].severity == SeverityLevel.INFO
    assert alerts[2].patient_id == "P001"


def test_alert_lifecycle():
    mgr = PriorityAlertManager()
    ev = create_event("P001", "spo2", SeverityLevel.CRITICAL, 84, "%")
    alert = mgr.ingest_event(ev, "Eleanor Vance")
    assert alert.status == AlertStatus.ACTIVE

    # Acknowledge
    ack = mgr.acknowledge_alert(alert.alert_id, "Nurse Alex")
    assert ack is not None
    assert ack.status == AlertStatus.ACKNOWLEDGED
    assert ack.acknowledged_by == "Nurse Alex"

    # Resolve
    res = mgr.resolve_alert(alert.alert_id, "O2 mask applied")
    assert res is not None
    assert res.status == AlertStatus.RESOLVED
    assert res.resolution_note == "O2 mask applied"
