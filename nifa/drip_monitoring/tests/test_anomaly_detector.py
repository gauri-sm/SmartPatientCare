"""Unit tests for IV Drip Anomaly Detector."""

import unittest
from nifa.drip_monitoring.src.anomaly_detector import DripAnomalyDetector
from nifa.drip_monitoring.src.constants import (
    SeverityLevel,
    AlertCategory,
    DripEventType,
)


class TestDripAnomalyDetector(unittest.TestCase):
    """Test suite for DripAnomalyDetector."""

    def setUp(self):
        self.detector = DripAnomalyDetector()

    def test_normal_infusion(self):
        # 500ml bag, 400ml left (80%), running at 100 ml/h with 100 ml/h target
        results = self.detector.evaluate(
            remaining_volume_ml=400.0,
            total_volume_ml=500.0,
            current_flow_rate_ml_h=100.0,
            prescribed_rate_ml_h=100.0,
        )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_anomaly)
        self.assertEqual(results[0].severity, SeverityLevel.INFO)
        self.assertEqual(results[0].value, "NORMAL")

    def test_low_volume_warning(self):
        # 500ml bag, 50ml left (10% <= 15%), flow normal at 100 ml/h
        results = self.detector.evaluate(
            remaining_volume_ml=50.0,
            total_volume_ml=500.0,
            current_flow_rate_ml_h=100.0,
            prescribed_rate_ml_h=100.0,
        )
        self.assertTrue(any(r.event_type in (DripEventType.DRIP_LOW, DripEventType.DRIP_VOLUME_LOW) for r in results))
        warning = [r for r in results if r.event_type in (DripEventType.DRIP_LOW, DripEventType.DRIP_VOLUME_LOW)][0]
        self.assertIn(warning.severity, (SeverityLevel.HIGH, SeverityLevel.WARNING))
        self.assertEqual(warning.category, AlertCategory.EQUIPMENT_ALERT)

    def test_empty_drip_completion(self):
        # Bag is at 0.0 ml
        results = self.detector.evaluate(
            remaining_volume_ml=0.0,
            total_volume_ml=500.0,
            current_flow_rate_ml_h=0.0,
            prescribed_rate_ml_h=100.0,
        )
        self.assertTrue(any(r.event_type in (DripEventType.DRIP_FINISHED, DripEventType.DRIP_EMPTY) for r in results))
        empty = [r for r in results if r.event_type in (DripEventType.DRIP_FINISHED, DripEventType.DRIP_EMPTY)][0]
        self.assertIn(empty.severity, (SeverityLevel.HIGH, SeverityLevel.CRITICAL))
        self.assertEqual(empty.category, AlertCategory.PATIENT_AND_EQUIPMENT_ALERT)

    def test_occlusion_detection(self):
        # 300 ml remaining, but flow rate drops to 0.0 ml/h
        results = self.detector.evaluate(
            remaining_volume_ml=300.0,
            total_volume_ml=500.0,
            current_flow_rate_ml_h=0.0,
            prescribed_rate_ml_h=100.0,
        )
        self.assertTrue(any(r.event_type == DripEventType.DRIP_OCCLUSION for r in results))
        occlusion = [r for r in results if r.event_type == DripEventType.DRIP_OCCLUSION][0]
        self.assertEqual(occlusion.severity, SeverityLevel.CRITICAL)
        self.assertEqual(occlusion.category, AlertCategory.EQUIPMENT_ALERT)
        self.assertEqual(occlusion.parameter, "occlusion_detected")

    def test_runaway_free_flow(self):
        # Target is 100 ml/h, actual flow spiked to 250 ml/h (> 2x)
        results = self.detector.evaluate(
            remaining_volume_ml=350.0,
            total_volume_ml=500.0,
            current_flow_rate_ml_h=250.0,
            prescribed_rate_ml_h=100.0,
        )
        self.assertTrue(any(r.event_type == DripEventType.DRIP_RUNAWAY for r in results))
        runaway = [r for r in results if r.event_type == DripEventType.DRIP_RUNAWAY][0]
        self.assertEqual(runaway.severity, SeverityLevel.CRITICAL)
        self.assertEqual(runaway.category, AlertCategory.PATIENT_AND_EQUIPMENT_ALERT)

    def test_air_in_line_detection(self):
        # Air sensor triggered
        results = self.detector.evaluate(
            remaining_volume_ml=350.0,
            total_volume_ml=500.0,
            current_flow_rate_ml_h=100.0,
            prescribed_rate_ml_h=100.0,
            air_in_line_detected=True,
        )
        self.assertTrue(any(r.event_type == DripEventType.DRIP_AIR_IN_LINE for r in results))
        air = [r for r in results if r.event_type == DripEventType.DRIP_AIR_IN_LINE][0]
        self.assertEqual(air.severity, SeverityLevel.CRITICAL)
        self.assertEqual(air.category, AlertCategory.EQUIPMENT_ALERT)

    def test_flow_rate_deviation_warning(self):
        # Target 100 ml/h, actual 130 ml/h (+30% deviation, below 200% runaway)
        results = self.detector.evaluate(
            remaining_volume_ml=300.0,
            total_volume_ml=500.0,
            current_flow_rate_ml_h=130.0,
            prescribed_rate_ml_h=100.0,
        )
        self.assertTrue(any(r.event_type == DripEventType.DRIP_RATE_DEVIATION for r in results))
        dev = [r for r in results if r.event_type == DripEventType.DRIP_RATE_DEVIATION][0]
        self.assertEqual(dev.severity, SeverityLevel.WARNING)


if __name__ == "__main__":
    unittest.main()
