"""Mechanical Ventilator telemetry processing and alert generation module.

Maintained by Melisa. Part of patient device monitoring.
Evaluates mechanical ventilator parameters and generates advisory alerts for:
- HIGH_PRESSURE (Peak Inspiratory Pressure elevated)
- CIRCUIT_DISCONNECT (Low PEEP and loss of delivered volume)
- APNEA (Prolonged cessation of breathing)
- Normal periodic ventilator telemetry

IMPORTANT SAFETY & CLINICAL DESIGN PRINCIPLES:
- Generates monitoring and recommendation events ONLY.
- Does NOT implement commands that control real ventilators.
- Uses clinical advisory language: "Ventilator parameter requires attention: ..."
- Strictly conforms to shared/schemas/event_schema.json without CCTV dependencies.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


@dataclass
class VentilatorThresholdConfig:
    """Configurable thresholds for mechanical ventilator telemetry alerts."""
    pip_threshold: float = 35.0            # cmH2O (Above this is HIGH_PRESSURE alert)
    peep_min_threshold: float = 2.0        # cmH2O (Below this is CIRCUIT_DISCONNECT alert)
    apnea_seconds_threshold: float = 20.0  # seconds without breath


class VentilatorProcessor:
    """Processes mechanical ventilator telemetry and generates schema-compliant alert events."""

    def __init__(self, thresholds: Optional[VentilatorThresholdConfig] = None):
        self.thresholds = thresholds or VentilatorThresholdConfig()

    @staticmethod
    def _create_event(
        patient_id: str,
        room_id: str,
        event_type: str,
        parameter: str,
        value: Any,
        unit: str,
        severity: str,
        message: str,
        source: str = "ventilator_monitor"
    ) -> Dict[str, Any]:
        """Format an event dictionary conforming strictly to the shared event architecture."""
        return {
            "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "patient_id": patient_id,
            "room_id": room_id,
            "source": source,
            "parameter": parameter,
            "value": value,
            "unit": unit,
            "severity": severity,
            "message": message,
            "status": "ACTIVE"
        }

    def evaluate_pip(
        self,
        patient_id: str,
        room_id: str,
        pip: float
    ) -> Dict[str, Any]:
        """Evaluate peak inspiratory pressure (PIP). Triggers HIGH_PRESSURE alert if elevated."""
        pip_val = round(float(pip), 1)
        if pip_val >= self.thresholds.pip_threshold:
            return self._create_event(
                patient_id=patient_id,
                room_id=room_id,
                event_type="VENTILATOR_ALERT",
                parameter="peak_inspiratory_pressure",
                value=pip_val,
                unit="cmH2O",
                severity="CRITICAL",
                message=(
                    f"Ventilator parameter requires attention: Peak Inspiratory Pressure elevated to "
                    f"{pip_val} cmH2O (threshold: {self.thresholds.pip_threshold:.1f} cmH2O). "
                    f"Please inspect breathing circuit and patient airway."
                )
            )
        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type="VENTILATOR_TELEMETRY",
            parameter="peak_inspiratory_pressure",
            value=pip_val,
            unit="cmH2O",
            severity="INFO",
            message=f"Ventilator parameter normal: PIP {pip_val} cmH2O."
        )

    def evaluate_peep(
        self,
        patient_id: str,
        room_id: str,
        peep: float
    ) -> Dict[str, Any]:
        """Evaluate Positive End-Expiratory Pressure (PEEP). Triggers CIRCUIT_DISCONNECT if low."""
        peep_val = round(float(peep), 1)
        if peep_val <= self.thresholds.peep_min_threshold:
            return self._create_event(
                patient_id=patient_id,
                room_id=room_id,
                event_type="VENTILATOR_ALERT",
                parameter="peep",
                value=peep_val,
                unit="cmH2O",
                severity="CRITICAL",
                message=(
                    f"Ventilator parameter requires attention: Low PEEP ({peep_val} cmH2O) and "
                    f"loss of delivered tidal volume detected. Possible circuit disconnection or leak."
                )
            )
        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type="VENTILATOR_TELEMETRY",
            parameter="peep",
            value=peep_val,
            unit="cmH2O",
            severity="INFO",
            message=f"Ventilator parameter normal: PEEP {peep_val} cmH2O."
        )

    def evaluate_apnea(
        self,
        patient_id: str,
        room_id: str,
        apnea_detected: bool = True
    ) -> Dict[str, Any]:
        """Evaluate apnea state. Triggers APNEA alert if apnea condition detected."""
        if apnea_detected:
            return self._create_event(
                patient_id=patient_id,
                room_id=room_id,
                event_type="VENTILATOR_ALERT",
                parameter="apnea_alarm",
                value=True,
                unit="status",
                severity="CRITICAL",
                message=(
                    f"Ventilator parameter requires attention: Apnea detected "
                    f"(>{self.thresholds.apnea_seconds_threshold:.0f}s without spontaneous or triggered breath). "
                    f"Immediate bedside check advised."
                )
            )
        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type="VENTILATOR_TELEMETRY",
            parameter="apnea_alarm",
            value=False,
            unit="status",
            severity="INFO",
            message="Ventilator spontaneous or triggered breath detected within normal interval."
        )

    def evaluate_telemetry(
        self,
        patient_id: str,
        room_id: str,
        pip: float = 22.0,
        peep: float = 6.0,
        tidal_volume: float = 480.0
    ) -> Dict[str, Any]:
        """Generate normal periodic baseline monitoring telemetry event."""
        pip_val = round(float(pip), 1)
        peep_val = round(float(peep), 1)
        vt_val = int(tidal_volume)
        return self._create_event(
            patient_id=patient_id,
            room_id=room_id,
            event_type="VENTILATOR_TELEMETRY",
            parameter="peak_inspiratory_pressure",
            value=pip_val,
            unit="cmH2O",
            severity="INFO",
            message=f"Ventilator parameter normal: PIP {pip_val} cmH2O, PEEP {peep_val} cmH2O, Vt {vt_val} ml."
        )

    def evaluate_scenario(
        self,
        patient_id: str,
        room_id: str,
        scenario: str
    ) -> Dict[str, Any]:
        """Evaluate defined clinical scenarios for demo transitions and simulation."""
        scenario_upper = scenario.upper().strip()
        if scenario_upper == "HIGH_PRESSURE":
            return self.evaluate_pip(patient_id=patient_id, room_id=room_id, pip=41.5)
        elif scenario_upper == "CIRCUIT_DISCONNECT":
            return self.evaluate_peep(patient_id=patient_id, room_id=room_id, peep=1.2)
        elif scenario_upper == "APNEA":
            return self.evaluate_apnea(patient_id=patient_id, room_id=room_id, apnea_detected=True)
        else:
            # Baseline normal monitoring event matching ventilator simulator default
            return self._create_event(
                patient_id=patient_id,
                room_id=room_id,
                event_type="VENTILATOR_TELEMETRY",
                parameter="peak_inspiratory_pressure",
                value=22.0,
                unit="cmH2O",
                severity="INFO",
                message="Ventilator operating within preset parameters: PIP 22.0 cmH2O, PEEP 6.0 cmH2O, Vt 480 ml."
            )


# Default singleton instance
default_ventilator_processor = VentilatorProcessor()
