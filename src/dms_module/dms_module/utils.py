from pathlib import Path

import yaml


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_package_path(package_dir, value):
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(package_dir) / path
