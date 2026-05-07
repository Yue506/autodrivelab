from .constants import IQA_LEVEL_DANGER, IQA_LEVEL_MINOR, IQA_LEVEL_NORMAL, IQA_LEVEL_WARNING


def camera_is_soiled(camera, threshold=0.5):
    explicit = bool(getattr(camera, "is_soiled", False))
    state = str(getattr(camera, "quality_state", "")).lower()
    score = float(getattr(camera, "soiling_score", 0.0))
    usable = getattr(camera, "usable", True)
    return explicit or state == "soiling" or score >= threshold or usable is False


def count_soiled_cameras(iqa_msg, config):
    threshold = config.get("soiling_score_threshold", 0.5)
    return [c for c in getattr(iqa_msg, "cameras", []) if camera_is_soiled(c, threshold)]


def has_critical_camera_soiled(cameras, config):
    critical = set(config.get("critical_cameras", []))
    return any(getattr(c, "camera_name", "") in critical or bool(getattr(c, "is_critical", False)) for c in cameras)


def compute_iqa_level(iqa_msg, config):
    explicit_level = int(getattr(iqa_msg, "iqa_level", 0))
    if explicit_level > 0:
        return min(explicit_level, IQA_LEVEL_DANGER)
    soiled = count_soiled_cameras(iqa_msg, config)
    soiled_count = len(soiled)
    if has_critical_camera_soiled(soiled, config):
        return IQA_LEVEL_DANGER
    if soiled_count >= config.get("level3_soiled_count", 3):
        return IQA_LEVEL_DANGER
    if soiled_count >= config.get("level2_soiled_count", 2):
        return IQA_LEVEL_WARNING
    if soiled_count >= config.get("level1_soiled_count", 1):
        return IQA_LEVEL_MINOR
    return IQA_LEVEL_NORMAL


def apply_iqa_gate(base_level, iqa_level, iqa_valid, config):
    perception_degraded = False
    if not iqa_valid:
        return base_level, perception_degraded
    if iqa_level >= config.get("mark_degraded_from_level", 2):
        perception_degraded = True
    if iqa_level == IQA_LEVEL_MINOR:
        final_level = max(base_level, 1)
    elif iqa_level == IQA_LEVEL_WARNING:
        final_level = max(base_level, config.get("min_level_when_iqa_level2", 2))
    elif iqa_level == IQA_LEVEL_DANGER:
        final_level = max(base_level, config.get("min_level_when_iqa_level3", 2))
    else:
        final_level = base_level
    return final_level, perception_degraded
