"""IV Drip Telemetry Simulation Engine.

Simulates IV drip depletion and generates state-transition events:
NORMAL DRIP -> DRIP LOW -> DRIP FINISHED

Features:
- Configurable demo sequence (100% -> 80% -> 60% -> 40% -> 20% -> 10% -> 5% -> 0%)
- Configurable low threshold (default: 15% or 10%)
- Configurable severity: DRIP_LOW -> HIGH, DRIP_FINISHED -> HIGH
- State-gated duplicate event prevention (no event flooding)
- Sends events to centralized backend via POST /api/events with configurable BACKEND_URL
- Conforms strictly to shared/schemas/event_schema.json with source="DRIP_MONITOR"
- Zero CCTV / video dependencies
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Callable
import time
import requests

from .telemetry_generator import DripTelemetryGenerator
from nifa.drip_monitoring.src.constants import (
    SeverityLevel,
    AlertStatus,
    DripEventType,
    DripStatus,
    SOURCE_DRIP_MONITOR,
    PARAM_DRIP_STATUS,
    DEFAULT_BACKEND_URL,
    DEFAULT_LOW_THRESHOLD_PCT,
    DEFAULT_LOW_SEVERITY,
    DEFAULT_FINISHED_SEVERITY,
)
from nifa.drip_monitoring.src.anomaly_detector import DripStateMonitor


class IVDripSimulator:
    """Simulates IV drip progression, state transitions, and backend API telemetry dispatch."""

    def __init__(
        self,
        patient_id: str = "P001",
        room_id: str = "ROOM101",
        total_volume_ml: float = 500.0,
        prescribed_rate_ml_h: float = 100.0,
        drop_factor: int = 20,
        low_threshold_pct: float = DEFAULT_LOW_THRESHOLD_PCT,
        low_severity: str = DEFAULT_LOW_SEVERITY,
        finished_severity: str = DEFAULT_FINISHED_SEVERITY,
        backend_url: str = DEFAULT_BACKEND_URL,
        source: str = SOURCE_DRIP_MONITOR,
        post_to_backend: bool = True,
    ):
        self.patient_id = patient_id
        self.room_id = room_id
        self.total_volume_ml = total_volume_ml
        self.prescribed_rate_ml_h = prescribed_rate_ml_h
        self.drop_factor = drop_factor
        self.low_threshold_pct = low_threshold_pct
        self.low_severity = low_severity
        self.finished_severity = finished_severity
        self.backend_url = backend_url.rstrip("/") if backend_url else None
        self.source = source
        self.post_to_backend = post_to_backend

        # State tracking
        self.current_level_pct: float = 100.0
        self.state_monitor = DripStateMonitor(
            patient_id=self.patient_id,
            room_id=self.room_id,
            low_threshold_pct=self.low_threshold_pct,
            low_severity=self.low_severity,
            finished_severity=self.finished_severity,
            source=self.source,
        )

        self.telemetry_generator = DripTelemetryGenerator()
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []
        self.event_history: List[Dict[str, Any]] = []

    @property
    def remaining_volume_ml(self) -> float:
        return round(self.total_volume_ml * (self.current_level_pct / 100.0), 1)

    @property
    def current_state(self) -> DripStatus:
        return self.state_monitor.current_state

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe a listener to receive generated telemetry events."""
        self.listeners.append(callback)

    def set_level_pct(self, level_pct: float) -> Optional[Dict[str, Any]]:
        """Set the current fluid percentage and evaluate state transition.

        Returns the generated event if a transition occurred (DRIP_LOW or DRIP_FINISHED),
        or None if no state change occurred (duplicate suppression).
        """
        self.current_level_pct = max(0.0, min(100.0, float(level_pct)))
        event = self.state_monitor.process_level_pct(self.current_level_pct)

        if event:
            # Validate against schema
            self.telemetry_generator.validate(event)
            self.event_history.append(event)

            # Broadcast to in-process listeners
            for listener in self.listeners:
                try:
                    listener(event)
                except Exception:
                    pass

            # Dispatch via HTTP POST to backend if configured
            if self.post_to_backend and self.backend_url:
                self.dispatch_to_backend(event)

        return event

    def dispatch_to_backend(self, event: Dict[str, Any]) -> bool:
        """Send event payload to POST /api/events endpoint on backend."""
        if not self.backend_url:
            return False

        endpoint = f"{self.backend_url}/api/events"
        try:
            resp = requests.post(
                endpoint,
                json=event,
                headers={"Content-Type": "application/json"},
                timeout=2.0,
            )
            if resp.status_code in (200, 201):
                print(f"[POST /api/events] SUCCESS: {event['event_type']} ({event['event_id']}) delivered. (Status: {resp.status_code})")
                return True
            else:
                print(f"[POST /api/events] WARNING: Received status {resp.status_code} from {endpoint}: {resp.text}")
                return False
        except requests.exceptions.RequestException as err:
            # Safe degradation: do not crash simulation if backend is offline or on another machine
            print(f"[POST /api/events] NOTICE: Backend offline at {self.backend_url} ({err.__class__.__name__}). Continuing local simulation.")
            return False

    def run_sequence(
        self,
        sequence: Optional[List[float]] = None,
        delay_seconds: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Run standard demo sequence (e.g. 100%, 80%, 60%, 40%, 20%, 10%, 5%, 0%).

        Returns all events generated during the sequence.
        """
        if sequence is None:
            sequence = [100.0, 80.0, 60.0, 40.0, 20.0, 10.0, 5.0, 0.0]

        generated_events: List[Dict[str, Any]] = []

        for level in sequence:
            event = self.set_level_pct(level)
            status_label = self.current_state.value
            event_tag = f" -> Emitted {event['event_type']}" if event else ""
            print(f"[*] Drip Level: {level:5.1f}% | State: {status_label:8s}{event_tag}")

            if event:
                generated_events.append(event)

            if delay_seconds > 0:
                time.sleep(delay_seconds)

        return generated_events

    def reset(self, level_pct: float = 100.0):
        """Reset fluid level and state monitor back to NORMAL."""
        self.state_monitor.reset()
        self.current_level_pct = level_pct
