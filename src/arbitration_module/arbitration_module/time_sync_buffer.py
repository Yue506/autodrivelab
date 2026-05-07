from dataclasses import dataclass, field

from .utils import age_ms, stamp_to_seconds


@dataclass
class SourceStatusData:
    adas_valid: bool = False
    dms_valid: bool = False
    iqa_valid: bool = False
    adas_stamp: object = None
    dms_stamp: object = None
    iqa_stamp: object = None
    adas_age_ms: float = 0.0
    dms_age_ms: float = 0.0
    iqa_age_ms: float = 0.0
    adas_dms_time_diff_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    adas_timeout: bool = False
    dms_timeout: bool = False
    iqa_timeout: bool = False
    perception_degraded: bool = False
    iqa_level: int = 0
    soiled_camera_count: int = 0
    soiled_cameras: list = field(default_factory=list)
    critical_camera_soiled: bool = False


class TimeSyncBuffer:
    def __init__(self, time_window_ms, adas_timeout_ms, dms_timeout_ms, iqa_timeout_ms):
        self.time_window_ms = time_window_ms
        self.adas_timeout_ms = adas_timeout_ms
        self.dms_timeout_ms = dms_timeout_ms
        self.iqa_timeout_ms = iqa_timeout_ms
        self.adas_msg = None
        self.dms_msg = None
        self.iqa_msg = None

    def update_adas(self, msg):
        self.adas_msg = msg

    def update_dms(self, msg):
        self.dms_msg = msg

    def update_iqa(self, msg):
        self.iqa_msg = msg

    def get_latest_tuple(self, now):
        status = SourceStatusData()
        status.adas_stamp = getattr(self.adas_msg, "stamp", None)
        status.dms_stamp = getattr(self.dms_msg, "stamp", None)
        status.iqa_stamp = getattr(self.iqa_msg, "stamp", None)
        status.adas_age_ms = age_ms(now, status.adas_stamp) if self.adas_msg else float("inf")
        status.dms_age_ms = age_ms(now, status.dms_stamp) if self.dms_msg else float("inf")
        status.iqa_age_ms = age_ms(now, status.iqa_stamp) if self.iqa_msg else float("inf")
        status.adas_timeout = self.adas_msg is None or status.adas_age_ms > self.adas_timeout_ms
        status.dms_timeout = self.dms_msg is None or status.dms_age_ms > self.dms_timeout_ms
        status.iqa_timeout = self.iqa_msg is None or status.iqa_age_ms > self.iqa_timeout_ms
        status.adas_valid = bool(self.adas_msg and getattr(self.adas_msg, "valid", True) and not status.adas_timeout)
        status.dms_valid = bool(self.dms_msg and getattr(self.dms_msg, "valid", True) and not status.dms_timeout)
        status.iqa_valid = bool(self.iqa_msg and getattr(self.iqa_msg, "valid", True) and not status.iqa_timeout)
        if self.adas_msg and self.dms_msg:
            status.adas_dms_time_diff_ms = abs(stamp_to_seconds(status.adas_stamp) - stamp_to_seconds(status.dms_stamp)) * 1000.0
        return self.adas_msg, self.dms_msg, self.iqa_msg, status
