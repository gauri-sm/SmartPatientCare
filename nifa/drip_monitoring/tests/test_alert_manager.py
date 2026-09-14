"""Unit tests for Drip Alert Manager."""

import unittest
from nifa.drip_monitoring.src.alert_manager import DripAlertManager
from nifa.drip_monitoring.src.constants import (
    SeverityLevel,
    AlertStatus,
    DripEventType,
)


class TestDripAlertManager(unittest.TestCase):
    """Test suite for DripAlertManager."""

    def setUp(self):
        self.manager = DripAlertManager()

    def test_create_event(self):
        evt = self.manager.create_event(
            event_type=DripEventType.DRIP_OCCLUSION.value,
            patient_id="P001",
            room_id="ROOM101",
            parameter="occlusion_detected",
            value=True,
            unit="boolean",
            severity=SeverityLevel.CRITICAL,
            message="IV line occlusion detected.",
        )
        self.assertTrue(evt["event_id"].startswith("EVT-DRIP-"))
        self.assertEqual(evt["patient_id"], "P001")
        self.assertEqual(evt["room_id"], "ROOM101")
        self.assertEqual(evt["severity"], "CRITICAL")
        self.assertEqual(evt["status"], "ACTIVE")

    def test_register_and_get_active_alerts(self):
        evt1 = self.manager.create_event(
            event_type=DripEventType.DRIP_VOLUME_LOW.value,
            patient_id="P001",
            room_id="ROOM101",
            parameter="remaining_volume_ml",
            value=50.0,
            unit="ml",
            severity=SeverityLevel.WARNING,
            message="Low volume warning.",
        )
        evt2 = self.manager.create_event(
            event_type=DripEventType.DRIP_OCCLUSION.value,
            patient_id="P001",
            room_id="ROOM101",
            parameter="occlusion_detected",
            value=True,
            unit="boolean",
            severity=SeverityLevel.CRITICAL,
            message="Critical line occlusion.",
        )
        self.manager.register_event(evt1)
        self.manager.register_event(evt2)

        active = self.manager.get_active_alerts(patient_id="P001")
        self.assertEqual(len(active), 2)
        # CRITICAL should be sorted before WARNING
        self.assertEqual(active[0]["severity"], "CRITICAL")
        self.assertEqual(active[1]["severity"], "WARNING")

    def test_acknowledge_alert(self):
        evt = self.manager.create_event(
            event_type=DripEventType.DRIP_VOLUME_LOW.value,
            patient_id="P001",
            room_id="ROOM101",
            parameter="remaining_volume_ml",
            value=50.0,
            unit="ml",
            severity=SeverityLevel.WARNING,
            message="Low volume warning.",
        )
        self.manager.register_event(evt)
        ack_res = self.manager.acknowledge_alert(evt["event_id"])
        self.assertIsNotNone(ack_res)
        self.assertEqual(ack_res["status"], AlertStatus.ACKNOWLEDGED.value)

        # Still considered in active alerts, but with ACKNOWLEDGED status
        active = self.manager.get_active_alerts(patient_id="P001")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["status"], "ACKNOWLEDGED")

    def test_resolve_alert(self):
        evt = self.manager.create_event(
            event_type=DripEventType.DRIP_VOLUME_LOW.value,
            patient_id="P001",
            room_id="ROOM101",
            parameter="remaining_volume_ml",
            value=50.0,
            unit="ml",
            severity=SeverityLevel.WARNING,
            message="Low volume warning.",
        )
        self.manager.register_event(evt)
        res_result = self.manager.resolve_alert(evt["event_id"])
        self.assertIsNotNone(res_result)
        self.assertEqual(res_result["status"], AlertStatus.RESOLVED.value)

        # Once resolved, no longer in active alerts
        active = self.manager.get_active_alerts(patient_id="P001")
        self.assertEqual(len(active), 0)

        # But remains in history with RESOLVED status
        history = self.manager.get_alert_history(patient_id="P001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["status"], "RESOLVED")

    def test_deduplication_helper(self):
        evt = self.manager.create_event(
            event_type=DripEventType.DRIP_OCCLUSION.value,
            patient_id="P002",
            room_id="ROOM102",
            parameter="occlusion_detected",
            value=True,
            unit="boolean",
            severity=SeverityLevel.CRITICAL,
            message="Occlusion test",
        )
        self.manager.register_event(evt)
        self.assertTrue(self.manager.has_active_alert_of_type("P002", DripEventType.DRIP_OCCLUSION.value))
        self.assertFalse(self.manager.has_active_alert_of_type("P002", DripEventType.DRIP_VOLUME_LOW.value))
        self.assertFalse(self.manager.has_active_alert_of_type("P001", DripEventType.DRIP_OCCLUSION.value))


if __name__ == "__main__":
    unittest.main()
