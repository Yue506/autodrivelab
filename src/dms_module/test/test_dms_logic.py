import unittest

from dms_module.core_perception import PerceptionResult
from dms_module.event_mapper import EVENT_DRIVER_CALLING, EVENT_DRIVER_NORMAL, map_dms_event
from dms_module.temporal_filter import TemporalFilter


class DmsLogicTest(unittest.TestCase):
    def test_phone_calling_maps_to_danger(self):
        event = map_dms_event(PerceptionResult(phone_calling=True, phone_confidence=0.9))
        self.assertEqual(event.event_type, EVENT_DRIVER_CALLING)
        self.assertEqual(event.danger_level, 3)
        self.assertAlmostEqual(event.confidence, 0.9)

    def test_invalid_result_is_not_danger(self):
        event = map_dms_event(PerceptionResult(valid=False))
        self.assertFalse(event.valid)
        self.assertEqual(event.danger_level, 0)
        self.assertEqual(event.confidence, 0.0)

    def test_temporal_filter_suppresses_single_frame_yawn(self):
        filt = TemporalFilter({"yawning_trigger_frames": 3, "release_frames": 2, "min_hold_time_ms": 0})
        raw = map_dms_event(PerceptionResult(yawning=True, yawning_confidence=0.8))
        self.assertEqual(filt.update(raw).event_type, EVENT_DRIVER_NORMAL)
        self.assertEqual(filt.update(raw).event_type, EVENT_DRIVER_NORMAL)
        self.assertEqual(filt.update(raw).danger_level, 2)


if __name__ == "__main__":
    unittest.main()
