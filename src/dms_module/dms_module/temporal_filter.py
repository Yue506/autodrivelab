from time import monotonic

from .event_mapper import DMS_LEVEL_DANGER, DMS_LEVEL_NORMAL, DmsEvent, EVENT_DRIVER_NORMAL


class TemporalFilter:
    def __init__(self, config):
        self.config = config or {}
        self.enabled = self.config.get("enable", True)
        self.trigger_frames = {
            "DRIVER_EYES_CLOSED": self.config.get("eyes_closed_trigger_frames", 10),
            "DRIVER_YAWNING": self.config.get("yawning_trigger_frames", 8),
            "DRIVER_CALLING": self.config.get("phone_trigger_frames", 5),
            "DRIVER_SMOKING": self.config.get("smoking_trigger_frames", 5),
            "DRIVER_DISTRACTED": self.config.get("distracted_trigger_frames", 8),
        }
        self.release_frames = self.config.get("release_frames", 15)
        self.min_hold_time_s = self.config.get("min_hold_time_ms", 1000) / 1000.0
        self.reset()

    def reset(self):
        self.event_counts = {event_type: 0 for event_type in self.trigger_frames}
        self.normal_count = 0
        self.last_level = DMS_LEVEL_NORMAL
        self.last_event_type = EVENT_DRIVER_NORMAL
        self.last_event = DmsEvent()
        self.last_update_time = monotonic()

    def update(self, raw_event):
        if not self.enabled or not raw_event.valid:
            self._remember(raw_event)
            return raw_event

        now = monotonic()
        if raw_event.event_type in self.event_counts:
            self.event_counts[raw_event.event_type] += 1
            self.normal_count = 0
        else:
            self.normal_count += 1
            for event_type in self.event_counts:
                self.event_counts[event_type] = 0

        trigger = self.trigger_frames.get(raw_event.event_type, 1)
        if raw_event.danger_level >= DMS_LEVEL_DANGER or self.event_counts.get(raw_event.event_type, 0) >= trigger:
            self._remember(raw_event)
            return raw_event
        if raw_event.danger_level > DMS_LEVEL_NORMAL:
            return self.last_event

        hold_active = (now - self.last_update_time) < self.min_hold_time_s
        if self.last_level > raw_event.danger_level and (hold_active or self.normal_count < self.release_frames):
            return self.last_event

        if raw_event.danger_level == DMS_LEVEL_NORMAL and self.normal_count < self.release_frames:
            return self.last_event

        self._remember(raw_event)
        return raw_event

    def _remember(self, event):
        self.last_level = event.danger_level
        self.last_event_type = event.event_type
        self.last_event = event
        self.last_update_time = monotonic()
