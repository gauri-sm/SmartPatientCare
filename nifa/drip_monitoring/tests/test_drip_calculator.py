"""Unit tests for IV Drip Calculator math and conversions."""

import unittest
from nifa.drip_monitoring.src.drip_calculator import DripCalculator


class TestDripCalculator(unittest.TestCase):
    """Test suite for DripCalculator."""

    def test_flow_rate_to_drops_per_min(self):
        # 100 ml/h with 20 gtt/ml factor = 33.3 gtt/min
        self.assertEqual(DripCalculator.flow_rate_to_drops_per_min(100.0, 20), 33.3)
        # 60 ml/h with 60 gtt/ml microdrip = 60.0 gtt/min
        self.assertEqual(DripCalculator.flow_rate_to_drops_per_min(60.0, 60), 60.0)
        # Zero flow rate = 0 gtt/min
        self.assertEqual(DripCalculator.flow_rate_to_drops_per_min(0.0, 20), 0.0)
        # Negative rate clamped to 0
        self.assertEqual(DripCalculator.flow_rate_to_drops_per_min(-10.0, 20), 0.0)

    def test_invalid_drop_factor(self):
        with self.assertRaises(ValueError):
            DripCalculator.flow_rate_to_drops_per_min(100.0, 0)
        with self.assertRaises(ValueError):
            DripCalculator.drops_per_min_to_flow_rate(30.0, -10)

    def test_drops_per_min_to_flow_rate(self):
        # 33.3 gtt/min with 20 drop factor ~ 99.9 ml/h
        rate = DripCalculator.drops_per_min_to_flow_rate(33.3, 20)
        self.assertAlmostEqual(rate, 99.9, places=1)
        # 60 gtt/min with 60 drop factor = 60 ml/h
        self.assertEqual(DripCalculator.drops_per_min_to_flow_rate(60.0, 60), 60.0)

    def test_calculate_remaining_volume(self):
        # Normal subtraction
        self.assertEqual(DripCalculator.calculate_remaining_volume(500.0, 150.0), 350.0)
        # Exactly full
        self.assertEqual(DripCalculator.calculate_remaining_volume(500.0, 0.0), 500.0)
        # Infused exceeds total -> clamps to 0
        self.assertEqual(DripCalculator.calculate_remaining_volume(500.0, 550.0), 0.0)

    def test_calculate_volume_percentage(self):
        self.assertEqual(DripCalculator.calculate_volume_percentage(250.0, 500.0), 50.0)
        self.assertEqual(DripCalculator.calculate_volume_percentage(0.0, 500.0), 0.0)
        self.assertEqual(DripCalculator.calculate_volume_percentage(500.0, 500.0), 100.0)
        self.assertEqual(DripCalculator.calculate_volume_percentage(100.0, 0.0), 0.0)

    def test_calculate_time_to_completion(self):
        # 500 ml remaining at 100 ml/h -> 5 hours
        hours, eta_str = DripCalculator.calculate_time_to_completion(500.0, 100.0)
        self.assertEqual(hours, 5.0)
        self.assertEqual(eta_str, "5h 0m")

        # 50 ml remaining at 100 ml/h -> 30 mins
        hours, eta_str = DripCalculator.calculate_time_to_completion(50.0, 100.0)
        self.assertEqual(hours, 0.5)
        self.assertEqual(eta_str, "30m")

        # Stopped flow
        hours, eta_str = DripCalculator.calculate_time_to_completion(500.0, 0.0)
        self.assertIsNone(hours)
        self.assertEqual(eta_str, "Stopped / Occluded")

        # Empty bag
        hours, eta_str = DripCalculator.calculate_time_to_completion(0.0, 100.0)
        self.assertEqual(hours, 0.0)
        self.assertEqual(eta_str, "Completed")

    def test_calculate_flow_deviation(self):
        # 120 vs 100 -> +20%
        self.assertEqual(DripCalculator.calculate_flow_deviation(120.0, 100.0), 20.0)
        # 80 vs 100 -> -20%
        self.assertEqual(DripCalculator.calculate_flow_deviation(80.0, 100.0), -20.0)
        # Prescribed is 0
        self.assertEqual(DripCalculator.calculate_flow_deviation(100.0, 0.0), 0.0)

    def test_calculate_infused_volume_delta(self):
        # 100 ml/h over 3600 seconds = 100 ml
        self.assertEqual(DripCalculator.calculate_infused_volume_delta(100.0, 3600.0), 100.0)
        # 100 ml/h over 1800 seconds = 50 ml
        self.assertEqual(DripCalculator.calculate_infused_volume_delta(100.0, 1800.0), 50.0)
        # Zero duration
        self.assertEqual(DripCalculator.calculate_infused_volume_delta(100.0, 0.0), 0.0)

    def test_compute_infusion_summary(self):
        summary = DripCalculator.compute_infusion_summary(
            total_volume_ml=500.0,
            infused_volume_ml=100.0,
            current_flow_rate_ml_h=100.0,
            prescribed_rate_ml_h=100.0,
            drop_factor=20,
        )
        self.assertEqual(summary["total_volume_ml"], 500.0)
        self.assertEqual(summary["remaining_volume_ml"], 400.0)
        self.assertEqual(summary["volume_percentage"], 80.0)
        self.assertEqual(summary["flow_rate_ml_h"], 100.0)
        self.assertEqual(summary["drops_per_min"], 33.3)
        self.assertEqual(summary["is_completed"], False)


if __name__ == "__main__":
    unittest.main()
