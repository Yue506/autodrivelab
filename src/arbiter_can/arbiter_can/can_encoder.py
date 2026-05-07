from __future__ import annotations

from types import SimpleNamespace
from typing import Any


CAN_ID_FUSION_RISK_STATUS = 0x321
SEMANTIC_NAME_FUSION_RISK_STATUS = "FUSION_RISK_STATUS"

EVENT_CODE_MAP = {
    "SAFE": 0,
    "FCW_WARNING": 1,
    "FCW_EMERGENCY": 2,
    "AEB_TRIGGER": 3,
    "BSD_ACTIVE": 4,
    "DRIVER_YAWNING": 10,
    "DRIVER_EYES_CLOSED": 11,
    "DRIVER_CALLING": 12,
    "DRIVER_SMOKING": 13,
    "CAMERA_SOILING": 20,
    "PERCEPTION_DEGRADED": 21,
    "SENSOR_INVALID": 30,
}

SOURCE_CODE_MAP = {
    "FUSION": 0,
    "ADAS": 1,
    "DMS": 2,
    "IQA": 3,
}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _make_can_frame():
    try:
        from autodrivelab_msgs.msg import CanFrame

        return CanFrame()
    except Exception:
        return SimpleNamespace(header=None, can_id=0, data=[], is_extended=False, semantic_name="")


def _clamp_u8(value: Any) -> int:
    try:
        return max(0, min(255, int(value)))
    except (TypeError, ValueError):
        return 0


def _source_flags(source_status: Any) -> int:
    flags = 0
    if bool(_get(source_status, "adas_valid", False)):
        flags |= 0x01
    if bool(_get(source_status, "dms_valid", False)):
        flags |= 0x02
    if bool(_get(source_status, "iqa_valid", False)):
        flags |= 0x04
    if bool(_get(source_status, "perception_degraded", False)):
        flags |= 0x08
    return flags


def encode_fusion_to_can_frame(fusion_msg: Any, rolling_counter: int = 0):
    source_status = _get(fusion_msg, "source_status", {})
    primary_event = str(_get(fusion_msg, "primary_event", "SAFE") or "SAFE").upper()
    primary_source = str(_get(fusion_msg, "primary_source", "FUSION") or "FUSION").upper()
    data = [
        _clamp_u8(_get(fusion_msg, "unified_risk_level", 0)),
        _source_flags(source_status),
        EVENT_CODE_MAP.get(primary_event, 255),
        _clamp_u8(_get(source_status, "iqa_level", 0)),
        _clamp_u8(_get(source_status, "soiled_camera_count", 0)),
        SOURCE_CODE_MAP.get(primary_source, 255),
        _clamp_u8(rolling_counter),
        0,
    ]
    data[7] = sum(data[:7]) & 0xFF

    frame = _make_can_frame()
    header = _get(fusion_msg, "header", None)
    if header is not None and hasattr(frame, "header"):
        frame.header = header
    frame.can_id = CAN_ID_FUSION_RISK_STATUS
    frame.semantic_name = SEMANTIC_NAME_FUSION_RISK_STATUS
    frame.is_extended = False
    frame.data = data
    return frame
