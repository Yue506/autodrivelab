from dataclasses import dataclass


DMS_LEVEL_NORMAL = 0
DMS_LEVEL_ATTENTION = 1
DMS_LEVEL_WARNING = 2
DMS_LEVEL_DANGER = 3

EVENT_DRIVER_NORMAL = "DRIVER_NORMAL"
EVENT_DRIVER_DISTRACTED = "DRIVER_DISTRACTED"
EVENT_DRIVER_YAWNING = "DRIVER_YAWNING"
EVENT_DRIVER_SMOKING = "DRIVER_SMOKING"
EVENT_DRIVER_EYES_CLOSED = "DRIVER_EYES_CLOSED"
EVENT_DRIVER_CALLING = "DRIVER_CALLING"
EVENT_DMS_INVALID = "DMS_INVALID"


@dataclass
class DmsEvent:
    danger_level: int = DMS_LEVEL_NORMAL
    event_type: str = EVENT_DRIVER_NORMAL
    event_description: str = "Driver normal"
    fatigue_level: int = DMS_LEVEL_NORMAL
    distraction_level: int = DMS_LEVEL_NORMAL
    violation_level: int = DMS_LEVEL_NORMAL
    confidence: float = 1.0
    valid: bool = True


def map_dms_event(perception_result):
    if not perception_result.valid:
        return DmsEvent(
            event_type=EVENT_DMS_INVALID,
            event_description="DMS data invalid",
            confidence=0.0,
            valid=False,
        )

    fatigue_level = DMS_LEVEL_NORMAL
    distraction_level = DMS_LEVEL_NORMAL
    violation_level = DMS_LEVEL_NORMAL

    if perception_result.eyes_closed:
        fatigue_level = DMS_LEVEL_DANGER
    elif perception_result.yawning:
        fatigue_level = DMS_LEVEL_WARNING
    elif perception_result.short_eye_closure:
        fatigue_level = DMS_LEVEL_ATTENTION

    if perception_result.distracted:
        distraction_level = max(distraction_level, DMS_LEVEL_ATTENTION)

    if perception_result.phone_calling:
        violation_level = DMS_LEVEL_DANGER
    elif perception_result.smoking:
        violation_level = DMS_LEVEL_WARNING

    danger_level = max(fatigue_level, distraction_level, violation_level)
    priority = [
        (perception_result.eyes_closed, EVENT_DRIVER_EYES_CLOSED, "Driver eyes closed", perception_result.fatigue_confidence),
        (perception_result.phone_calling, EVENT_DRIVER_CALLING, "Driver phone calling", perception_result.phone_confidence),
        (perception_result.smoking, EVENT_DRIVER_SMOKING, "Driver smoking", perception_result.smoking_confidence),
        (perception_result.yawning, EVENT_DRIVER_YAWNING, "Driver yawning", perception_result.yawning_confidence),
        (perception_result.distracted, EVENT_DRIVER_DISTRACTED, "Driver distracted", perception_result.distraction_confidence),
    ]
    for active, event_type, description, confidence in priority:
        if active:
            return DmsEvent(
                danger_level=danger_level,
                event_type=event_type,
                event_description=description,
                fatigue_level=fatigue_level,
                distraction_level=distraction_level,
                violation_level=violation_level,
                confidence=max(0.0, min(1.0, float(confidence))),
            )

    return DmsEvent(
        danger_level=DMS_LEVEL_NORMAL,
        event_type=EVENT_DRIVER_NORMAL,
        event_description="Driver normal",
        confidence=1.0,
    )
