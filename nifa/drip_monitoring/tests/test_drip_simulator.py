"""Unit tests for IV Drip Simulator engine."""

import unittest
from simulator.drip_simulator.drip_simulator import (
    IVDripSimulator,
    DripSimulationScenario,
)
from nifa.drip_monitoring.src.constants import SeverityLevel


class TestDripSimulator(unittest.TestCase):
    """Test suite for IVDripSimulator."""

    def setUp(self):
        self.sim = IVDripSimulator(
            patient_id="P001",
            room_id="ROOM101",
            total_volume_ml=500.0,
            prescribed_rate_ml_h=100.0,
            drop_factor=20,
        )

    def test_initial_state(self):
        self.assertEqual(self.sim.remaining_volume_ml, 500.0)
        self.assertEqual(self.sim.volume_percentage, 100.0)
        self.assertEqual(self.sim.current_flow_rate_ml_h, 100.0)
        self.assertEqual(self.sim.drops_per_min, 33.3)

    def test_normal_scenario(self):
        events = self.sim.apply_scenario(DripSimulationScenario.NORMAL)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["severity"], SeverityLevel.INFO.value)
        self.assertEqual(events[0]["parameter"], "drip_status")

    def test_low_volume_scenario(self):
        events = self.sim.apply_scenario(DripSimulationScenario.WARNING_LOW_VOLUME)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["severity"], SeverityLevel.WARNING.value)
        self.assertEqual(events[0]["value"], 50.0)
        self.assertEqual(self.sim.volume_percentage, 10.0)

    def test_occlusion_scenario(self):
        events = self.sim.apply_scenario(DripSimulationScenario.CRITICAL_OCCLUSION)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["severity"], SeverityLevel.CRITICAL.value)
        self.assertEqual(self.sim.current_flow_rate_ml_h, 0.0)
        self.assertEqual(self.sim.drops_per_min, 0.0)
        self.assertTrue(self.sim.occlusion_active)

    def test_runaway_scenario(self):
        events = self.sim.apply_scenario(DripSimulationScenario.CRITICAL_RUNAWAY)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["severity"], SeverityLevel.CRITICAL.value)
        self.assertEqual(self.sim.current_flow_rate_ml_h, 250.0)

    def test_air_in_line_scenario(self):
        events = self.sim.apply_scenario(DripSimulationScenario.CRITICAL_AIR_IN_LINE)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["severity"], SeverityLevel.CRITICAL.value)
        self.assertTrue(self.sim.air_in_line)

    def test_empty_bag_scenario(self):
        events = self.sim.apply_scenario(DripSimulationScenario.CRITICAL_EMPTY)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["severity"], SeverityLevel.CRITICAL.value)
        self.assertEqual(self.sim.remaining_volume_ml, 0.0)

    def test_step_advancement(self):
        # Step 36 seconds at 100 ml/h = 1.0 ml infused
        ml = self.sim.step(36.0)
        self.assertEqual(ml, 1.0)
        self.assertEqual(self.sim.remaining_volume_ml, 499.0)

    def test_reset_bag(self):
        self.sim.apply_scenario(DripSimulationScenario.CRITICAL_EMPTY)
        self.assertEqual(self.sim.remaining_volume_ml, 0.0)
        self.sim.reset_bag(500.0)
        self.assertEqual(self.sim.remaining_volume_ml, 500.0)
        self.assertEqual(self.sim.current_flow_rate_ml_h, 100.0)

    def test_subscriber_listener(self):
        received = []
        self.sim.subscribe(lambda evt: received.append(evt))
        self.sim.apply_scenario(DripSimulationScenario.NORMAL)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["event_type"], "DRIP_FLOW_RATE")


if __name__ == "__main__":
    unittest.main()
