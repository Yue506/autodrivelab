from __future__ import annotations

import json
from pathlib import Path


CAMERA_FIELDS = {
    "CAM_FRONT": "cam_front",
    "CAM_FRONT_LEFT": "cam_front_left",
    "CAM_FRONT_RIGHT": "cam_front_right",
    "CAM_BACK": "cam_back",
    "CAM_BACK_LEFT": "cam_back_left",
    "CAM_BACK_RIGHT": "cam_back_right",
}


def read_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def stamp_from_us(clock, timestamp_us: int):
    stamp = clock.now().to_msg()
    if timestamp_us:
        stamp.sec = int(timestamp_us // 1_000_000)
        stamp.nanosec = int((timestamp_us % 1_000_000) * 1000)
    return stamp


def timeline_segment(index: int, total: int, segments: list[dict]) -> dict:
    ratio = index / max(total, 1)
    for segment in segments:
        if float(segment["start_ratio"]) <= ratio < float(segment["end_ratio"]):
            return segment
    return segments[-1]


def default_dms_timeline() -> list[dict]:
    return [
        {"start_ratio": 0.00, "end_ratio": 0.25, "danger_level": 0, "event_type": "DRIVER_NORMAL", "event_description": "驾驶员状态正常"},
        {"start_ratio": 0.25, "end_ratio": 0.45, "danger_level": 2, "event_type": "DRIVER_YAWNING", "event_description": "驾驶员打哈欠，存在疲劳风险"},
        {"start_ratio": 0.45, "end_ratio": 0.70, "danger_level": 3, "event_type": "DRIVER_EYES_CLOSED", "event_description": "驾驶员闭眼危险"},
        {"start_ratio": 0.70, "end_ratio": 1.00, "danger_level": 0, "event_type": "DRIVER_NORMAL", "event_description": "驾驶员状态恢复正常"},
    ]
