"""Unit tests for IV Drip Simulator engine."""

import unittest
from simulator.drip_simulator.drip_simulator import IVDripSimulator
from nifa.drip_monitoring.src.constants import (
    DripEventType,
    DripStatus,
    SOURCE_DRIP_MONITOR,
)


class TestDripSimulator(unittest.TestCase):
    """Test suite for IVDripSimulator."""

    def setUp(self):
        self.sim = IVDripSimulator(
            patient_id="P001",
            room_id="ROOM101",
            total_volume_ml=500.0,
            prescribed_rate_ml_h=100.0,
            post_to_backend=False,
        )

    def test_initial_state(self):
        self.assertEqual(self.sim.remaining_volume_ml, 500.0)
        self.assertEqual(self.sim.current_level_pct, 100.0)
        self.assertEqual(self.sim.current_state, DripStatus.NORMAL)

    def test_normal_sequence(self):
        for level in [100.0, 80.0, 60.0, 40.0, 20.0]:
            evt = self.sim.set_level_pct(level)
            self.assertIsNone(evt)
            self.assertEqual(self.sim.current_state, DripStatus.NORMAL)

    def test_low_level_transition(self):
        evt = self.sim.set_level_pct(10.0)
        self.assertIsNotNone(evt)
        self.assertEqual(evt["event_type"], DripEventType.DRIP_LOW.value)
        self.assertEqual(evt["source"], SOURCE_DRIP_MONITOR)
        self.assertEqual(self.sim.current_state, DripStatus.LOW)

    def test_duplicate_suppression_in_low(self):
        self.sim.set_level_pct(10.0)
        # Next lower step within LOW
        evt2 = self.sim.set_level_pct(5.0)
        self.assertIsNone(evt2, "Subsequent drop in LOW state must not emit duplicate alert")
        self.assertEqual(self.sim.current_state, DripStatus.LOW)

    def test_finished_transition(self):
        self.sim.set_level_pct(10.0)
        evt_fin = self.sim.set_level_pct(0.0)
        self.assertIsNotNone(evt_fin)
        self.assertEqual(evt_fin["event_type"], DripEventType.DRIP_FINISHED.value)
        self.assertEqual(self.sim.current_state, DripStatus.FINISHED)

    def test_run_sequence(self):
        sim = IVDripSimulator(patient_id="P001", room_id="ROOM101", post_to_backend=False)
        events = sim.run_sequence([100.0, 80.0, 60.0, 40.0, 20.0, 10.0, 5.0, 0.0], delay_seconds=0.0)
        # Exactly 2 state transition events: DRIP_LOW (at 10%) and DRIP_FINISHED (at 0%)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_type"], DripEventType.DRIP_LOW.value)
        self.assertEqual(events[1]["event_type"], DripEventType.DRIP_FINISHED.value)

    def test_reset(self):
        self.sim.set_level_pct(0.0)
        self.assertEqual(self.sim.current_state, DripStatus.FINISHED)
        self.sim.reset(100.0)
        self.assertEqual(self.sim.current_state, DripStatus.NORMAL)
        self.assertEqual(self.sim.remaining_volume_ml, 500.0)

    def test_subscriber_listener(self):
        received = []
        self.sim.subscribe(lambda evt: received.append(evt))
        self.sim.set_level_pct(10.0)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["event_type"], DripEventType.DRIP_LOW.value)


if __name__ == "__main__":
    unittest.main()
