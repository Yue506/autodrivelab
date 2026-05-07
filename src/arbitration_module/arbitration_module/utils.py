import yaml


def clamp_int(value, low, high):
    return max(low, min(high, int(value)))


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def stamp_to_seconds(stamp):
    if stamp is None:
        return 0.0
    return float(getattr(stamp, "sec", 0)) + float(getattr(stamp, "nanosec", 0)) / 1e9


def age_ms(now, stamp):
    return max(0.0, (stamp_to_seconds(now) - stamp_to_seconds(stamp)) * 1000.0)
