from .constants import (
    EVENT_CAMERA_SOILING,
    EVENT_PERCEPTION_DEGRADED,
    EVENT_SAFE,
    EVENT_SENSOR_INVALID,
    SOURCE_ADAS,
    SOURCE_DMS,
    SOURCE_FUSION,
    SOURCE_IQA,
)


def make_event(source, event_type, level, description, confidence):
    return {
        "source": source,
        "event_type": event_type,
        "level": int(level),
        "description": description,
        "confidence": float(confidence),
    }


def build_fusion_events(adas_msg, dms_msg, iqa_msg, unified_level, source_status):
    events = []
    if source_status.adas_valid and int(getattr(adas_msg, "adas_level", 0)) > 0:
        events.append(make_event(SOURCE_ADAS, adas_msg.event_type, adas_msg.adas_level, adas_msg.event_description, adas_msg.confidence))
    if source_status.dms_valid and int(getattr(dms_msg, "danger_level", 0)) > 0:
        events.append(make_event(SOURCE_DMS, dms_msg.event_type, dms_msg.danger_level, dms_msg.event_description, dms_msg.confidence))
    if source_status.iqa_valid and source_status.iqa_level > 0:
        names = ", ".join(source_status.soiled_cameras) if source_status.soiled_cameras else "unknown"
        desc = f"Camera soiling detected: {names}; perception reliability degraded"
        events.append(make_event(SOURCE_IQA, EVENT_CAMERA_SOILING, source_status.iqa_level, desc, getattr(iqa_msg, "confidence", 0.0)))
    if source_status.perception_degraded:
        events.append(make_event(SOURCE_IQA, EVENT_PERCEPTION_DEGRADED, source_status.iqa_level, "Perception degraded by camera quality", getattr(iqa_msg, "confidence", 0.0)))
    if not events:
        if not (source_status.adas_valid or source_status.dms_valid or source_status.iqa_valid):
            events.append(make_event(SOURCE_FUSION, EVENT_SENSOR_INVALID, 0, "All sources invalid or timed out", 0.0))
        else:
            events.append(make_event(SOURCE_FUSION, EVENT_SAFE, 0, "All active sources normal", 1.0))

    primary = choose_primary_event(events)
    confidence = max(event["confidence"] for event in events) if events else 0.0
    return primary["source"], primary["event_type"], primary["description"], events, confidence


def choose_primary_event(events):
    priority = {
        (SOURCE_ADAS, 4): 100,
        (SOURCE_ADAS, 3): 90,
        (SOURCE_DMS, 3): 80,
        (SOURCE_ADAS, 2): 70,
        (SOURCE_DMS, 2): 60,
        (SOURCE_IQA, 3): 50,
        (SOURCE_IQA, 2): 40,
        (SOURCE_ADAS, 1): 30,
        (SOURCE_DMS, 1): 20,
        (SOURCE_IQA, 1): 10,
    }
    return max(events, key=lambda event: priority.get((event["source"], event["level"]), 0))
