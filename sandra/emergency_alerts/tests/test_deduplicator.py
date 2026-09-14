"""
Unit tests for Sandra's Alert Deduplicator
"""

from sandra.emergency_alerts.src.deduplicator import AlertDeduplicator
from sandra.emergency_alerts.src.models import (
    SmartPatientCareEvent,
    SeverityLevel,
    AlertStatus,
)


def make_event(param="heart_rate", value=145, severity=SeverityLevel.CRITICAL):
    return SmartPatientCareEvent(
        event_id="e1",
        timestamp="2026-09-14T12:00:00Z",
        event_type="VITAL_SIGN",
        patient_id="P001",
        room_id="ROOM101",
        source="test",
        parameter=param,
        value=value,
        unit="bpm",
        severity=severity,
        message="High heart rate",
        status=AlertStatus.ACTIVE,
    )


def test_first_alert_emits():
    dedup = AlertDeduplicator(cooldown_seconds=30.0)
    ev = make_event()
    should_emit, reason = dedup.should_emit(ev)
    assert should_emit is True
    assert reason == "new_alert"


def test_rapid_duplicate_suppressed():
    dedup = AlertDeduplicator(cooldown_seconds=30.0)
    ev = make_event()
    dedup.should_emit(ev)

    # Second event immediately afterwards with same severity
    ev2 = make_event(value=146)
    should_emit, reason = dedup.should_emit(ev2)
    assert should_emit is False
    assert "throttled" in reason


def test_severity_escalation_bypasses_cooldown():
    dedup = AlertDeduplicator(cooldown_seconds=30.0)
    # Start with WARNING
    ev1 = make_event(value=115, severity=SeverityLevel.WARNING)
    emit1, _ = dedup.should_emit(ev1)
    assert emit1 is True

    # Escalate to CRITICAL immediately
    ev2 = make_event(value=160, severity=SeverityLevel.CRITICAL)
    emit2, reason = dedup.should_emit(ev2)
    assert emit2 is True
    assert "severity_escalated" in reason
