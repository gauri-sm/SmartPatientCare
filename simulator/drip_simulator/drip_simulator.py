"""IV Drip Telemetry Simulation Engine.

Simulates IV bag fluid dynamics, optical drop counting, flow anomalies, and generates
standardized events for hackathon demonstration.
DEMO/SIMULATION: All values are simulated mock telemetry for hackathon evaluation.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Callable
import time

from .telemetry_generator import DripTelemetryGenerator
from nifa.drip_monitoring.src.constants import (
    SeverityLevel,
    AlertStatus,
    AlertCategory,
    DripEventType,
    SOURCE_DRIP_SIMULATOR,
    PARAM_FLOW_RATE,
    PARAM_REMAINING_VOLUME,
    PARAM_OCCLUSION_STATE,
    PARAM_AIR_IN_LINE,
    PARAM_DRIP_STATUS,
    UNIT_ML_H,
    UNIT_ML,
    UNIT_STATUS,
    UNIT_BOOLEAN,
)
from nifa.drip_monitoring.src.drip_calculator import DripCalculator


class DripSimulationScenario(str, Enum):
    """Presets for hackathon demonstration."""
    NORMAL = "NORMAL"
    WARNING_LOW_VOLUME = "WARNING_LOW_VOLUME"
    CRITICAL_OCCLUSION = "CRITICAL_OCCLUSION"
    CRITICAL_RUNAWAY = "CRITICAL_RUNAWAY"
    CRITICAL_EMPTY = "CRITICAL_EMPTY"
    CRITICAL_AIR_IN_LINE = "CRITICAL_AIR_IN_LINE"


class IVDripSimulator:
    """Simulates realistic IV infusion mechanics with instant scenario injection."""

    def __init__(
        self,
        patient_id: str = "P001",
        room_id: str = "ROOM101",
        total_volume_ml: float = 500.0,
        prescribed_rate_ml_h: float = 100.0,
        drop_factor: int = 20,
    ):
        self.patient_id = patient_id
        self.room_id = room_id
        self.total_volume_ml = total_volume_ml
        self.prescribed_rate_ml_h = prescribed_rate_ml_h
        self.drop_factor = drop_factor

        # State variables
        self.infused_volume_ml = 0.0
        self.current_flow_rate_ml_h = prescribed_rate_ml_h
        self.active_scenario = DripSimulationScenario.NORMAL
        self.is_paused = False
        self.air_in_line = False
        self.occlusion_active = False

        self.telemetry_generator = DripTelemetryGenerator()
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []

    @property
    def remaining_volume_ml(self) -> float:
        return DripCalculator.calculate_remaining_volume(self.total_volume_ml, self.infused_volume_ml)

    @property
    def volume_percentage(self) -> float:
        return DripCalculator.calculate_volume_percentage(self.remaining_volume_ml, self.total_volume_ml)

    @property
    def drops_per_min(self) -> float:
        return DripCalculator.flow_rate_to_drops_per_min(self.current_flow_rate_ml_h, self.drop_factor)

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe a listener callback to receive generated telemetry events."""
        self.listeners.append(callback)

    def _broadcast(self, event: Dict[str, Any]):
        for listener in self.listeners:
            try:
                listener(event)
            except Exception:
                pass

    def apply_scenario(self, scenario: DripSimulationScenario) -> List[Dict[str, Any]]:
        """Instantly inject a scenario for interactive hackathon demonstration."""
        self.active_scenario = scenario
        generated_events: List[Dict[str, Any]] = []

        if scenario == DripSimulationScenario.NORMAL:
            self.occlusion_active = False
            self.air_in_line = False
            self.current_flow_rate_ml_h = self.prescribed_rate_ml_h
            if self.remaining_volume_ml <= 20.0:
                self.infused_volume_ml = self.total_volume_ml * 0.2  # 80% remaining

            evt = self.telemetry_generator.build_event(
                event_type=DripEventType.DRIP_FLOW_RATE.value,
                patient_id=self.patient_id,
                room_id=self.room_id,
                source=SOURCE_DRIP_SIMULATOR,
                parameter=PARAM_DRIP_STATUS,
                value="NORMAL",
                unit=UNIT_STATUS,
                severity=SeverityLevel.INFO.value,
                message=f"[DEMO/SIMULATED] Infusion operating normally at {self.current_flow_rate_ml_h:.1f} ml/h.",
                status=AlertStatus.ACTIVE.value,
            )
            generated_events.append(evt)

        elif scenario == DripSimulationScenario.WARNING_LOW_VOLUME:
            self.occlusion_active = False
            self.air_in_line = False
            self.current_flow_rate_ml_h = self.prescribed_rate_ml_h
            # Set volume to 10% remaining (e.g. 50 ml out of 500 ml)
            self.infused_volume_ml = self.total_volume_ml * 0.90
            evt = self.telemetry_generator.build_event(
                event_type=DripEventType.DRIP_VOLUME_LOW.value,
                patient_id=self.patient_id,
                room_id=self.room_id,
                source=SOURCE_DRIP_SIMULATOR,
                parameter=PARAM_REMAINING_VOLUME,
                value=self.remaining_volume_ml,
                unit=UNIT_ML,
                severity=SeverityLevel.WARNING.value,
                message=(
                    f"[DEMO/SIMULATED] WARNING: Low IV volume! {self.remaining_volume_ml:.1f} ml remaining "
                    f"({self.volume_percentage:.1f}%). Prepare replacement bag."
                ),
                status=AlertStatus.ACTIVE.value,
            )
            generated_events.append(evt)

        elif scenario == DripSimulationScenario.CRITICAL_OCCLUSION:
            self.occlusion_active = True
            self.air_in_line = False
            self.current_flow_rate_ml_h = 0.0
            if self.remaining_volume_ml <= 10.0:
                self.infused_volume_ml = self.total_volume_ml * 0.4
            evt = self.telemetry_generator.build_event(
                event_type=DripEventType.DRIP_OCCLUSION.value,
                patient_id=self.patient_id,
                room_id=self.room_id,
                source=SOURCE_DRIP_SIMULATOR,
                parameter=PARAM_OCCLUSION_STATE,
                value=True,
                unit=UNIT_BOOLEAN,
                severity=SeverityLevel.CRITICAL.value,
                message=(
                    f"[DEMO/SIMULATED] CRITICAL EQUIPMENT ALERT: IV line occlusion/blockage detected! "
                    f"Flow stopped (0 ml/h) with {self.remaining_volume_ml:.1f} ml remaining."
                ),
                status=AlertStatus.ACTIVE.value,
            )
            generated_events.append(evt)

        elif scenario == DripSimulationScenario.CRITICAL_RUNAWAY:
            self.occlusion_active = False
            self.air_in_line = False
            # Free flow at 2.5x prescribed rate
            self.current_flow_rate_ml_h = self.prescribed_rate_ml_h * 2.5
            evt = self.telemetry_generator.build_event(
                event_type=DripEventType.DRIP_RUNAWAY.value,
                patient_id=self.patient_id,
                room_id=self.room_id,
                source=SOURCE_DRIP_SIMULATOR,
                parameter=PARAM_FLOW_RATE,
                value=self.current_flow_rate_ml_h,
                unit=UNIT_ML_H,
                severity=SeverityLevel.CRITICAL.value,
                message=(
                    f"[DEMO/SIMULATED] CRITICAL PATIENT ALERT: Dangerous IV runaway over-infusion! "
                    f"Flow rate spiked to {self.current_flow_rate_ml_h:.1f} ml/h."
                ),
                status=AlertStatus.ACTIVE.value,
            )
            generated_events.append(evt)

        elif scenario == DripSimulationScenario.CRITICAL_EMPTY:
            self.occlusion_active = False
            self.air_in_line = False
            self.current_flow_rate_ml_h = 0.0
            self.infused_volume_ml = self.total_volume_ml  # 0 ml remaining
            evt = self.telemetry_generator.build_event(
                event_type=DripEventType.DRIP_EMPTY.value,
                patient_id=self.patient_id,
                room_id=self.room_id,
                source=SOURCE_DRIP_SIMULATOR,
                parameter=PARAM_REMAINING_VOLUME,
                value=0.0,
                unit=UNIT_ML,
                severity=SeverityLevel.CRITICAL.value,
                message="[DEMO/SIMULATED] CRITICAL: IV bag empty! Infusion cycle completed (0.0 ml remaining).",
                status=AlertStatus.ACTIVE.value,
            )
            generated_events.append(evt)

        elif scenario == DripSimulationScenario.CRITICAL_AIR_IN_LINE:
            self.air_in_line = True
            evt = self.telemetry_generator.build_event(
                event_type=DripEventType.DRIP_AIR_IN_LINE.value,
                patient_id=self.patient_id,
                room_id=self.room_id,
                source=SOURCE_DRIP_SIMULATOR,
                parameter=PARAM_AIR_IN_LINE,
                value=True,
                unit=UNIT_BOOLEAN,
                severity=SeverityLevel.CRITICAL.value,
                message="[DEMO/SIMULATED] CRITICAL EQUIPMENT ALERT: Air bubble detected in drip chamber/line!",
                status=AlertStatus.ACTIVE.value,
            )
            generated_events.append(evt)

        for evt in generated_events:
            self._broadcast(evt)

        return generated_events

    def step(self, elapsed_seconds: float = 1.0) -> float:
        """Advance the simulation clock by elapsed_seconds. Returns ml infused in this step."""
        if self.is_paused or self.occlusion_active or self.remaining_volume_ml <= 0.0:
            return 0.0

        ml_infused = DripCalculator.calculate_infused_volume_delta(
            self.current_flow_rate_ml_h, elapsed_seconds
        )
        self.infused_volume_ml = min(self.total_volume_ml, self.infused_volume_ml + ml_infused)

        # Check if bag emptied during this step
        if self.remaining_volume_ml <= 0.0 and self.active_scenario != DripSimulationScenario.CRITICAL_EMPTY:
            self.apply_scenario(DripSimulationScenario.CRITICAL_EMPTY)

        return ml_infused

    def reset_bag(self, total_volume_ml: Optional[float] = None):
        """Reset to full bag in Normal infusion mode."""
        if total_volume_ml is not None:
            self.total_volume_ml = total_volume_ml
        self.infused_volume_ml = 0.0
        self.apply_scenario(DripSimulationScenario.NORMAL)
