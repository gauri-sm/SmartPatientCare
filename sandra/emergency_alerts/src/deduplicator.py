"""
Alert Deduplicator and Throttler
================================
Suppresses rapid repetitive alerts to avoid nurse alarm fatigue,
while ensuring critical severity escalations are pushed immediately.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from datetime import datetime, timezone
from typing import Dict, Tuple, Optional
from sandra.emergency_alerts.src.models import SmartPatientCareEvent, SeverityLevel


SEVERITY_RANK = {
    SeverityLevel.CRITICAL: 5,
    SeverityLevel.HIGH: 4,
    SeverityLevel.WARNING: 3,
    SeverityLevel.MEDIUM: 2,
    SeverityLevel.LOW: 1,
    SeverityLevel.INFO: 0,
}


class AlertDeduplicator:
    """
    Manages alert throttling, suppression, and escalation.
    Prevents repeated events (e.g. consecutive CCTV frames or sensor jitter)
    from flooding the station dashboard.
    """

    def __init__(self, cooldown_seconds: float = 30.0):
        self.cooldown_seconds = cooldown_seconds
        # Key: (patient_id, parameter) -> entry
        self._cache: Dict[Tuple[str, str], Dict] = {}
        # Set of recently processed event_ids
        self._seen_event_ids: Dict[str, datetime] = {}

    def should_emit(self, event: SmartPatientCareEvent) -> Tuple[bool, Optional[str]]:
        """
        Determines whether the incoming event should be emitted as a new/updated alert.
        Suppresses rapid duplicate video frames or sensor jitter within cooldown window,
        while immediately allowing severity escalations (e.g. WARNING -> CRITICAL).
        Returns: (should_emit: bool, reason: str)
        """
        key = (event.patient_id, event.parameter or event.event_type)
        now = datetime.now(timezone.utc)

        if key not in self._cache:
            self._cache[key] = {
                "last_timestamp": now,
                "severity": event.severity,
                "last_value": event.value,
                "suppressed_count": 0,
            }
            return True, "new_alert"

        entry = self._cache[key]
        last_time: datetime = entry["last_timestamp"]
        last_sev: SeverityLevel = entry["severity"]
        time_elapsed = (now - last_time).total_seconds()

        # Severity escalation check (e.g., WARNING -> HIGH or CRITICAL)
        current_rank = SEVERITY_RANK.get(event.severity, 0)
        last_rank = SEVERITY_RANK.get(last_sev, 0)

        if current_rank > last_rank:
            entry["last_timestamp"] = now
            entry["severity"] = event.severity
            entry["last_value"] = event.value
            entry["suppressed_count"] = 0
            return True, f"severity_escalated_to_{event.severity.value}"

        # If within cooldown window and severity didn't increase
        if time_elapsed < self.cooldown_seconds:
            entry["suppressed_count"] += 1
            entry["last_value"] = event.value
            return False, f"throttled_cooldown_active ({entry['suppressed_count']} suppressed)"

        # Cooldown expired: re-emit alert
        entry["last_timestamp"] = now
        entry["severity"] = event.severity
        entry["last_value"] = event.value
        entry["suppressed_count"] = 0
        return True, "cooldown_expired"

    def clear(self, patient_id: Optional[str] = None):
        """
        Clears cached state for a patient or entirely.
        """
        if patient_id is None:
            self._cache.clear()
        else:
            keys_to_del = [k for k in self._cache if k[0] == patient_id]
            for k in keys_to_del:
                del self._cache[k]
