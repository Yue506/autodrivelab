from dataclasses import dataclass
from time import perf_counter

from .utils import clamp


@dataclass
class PerceptionResult:
    eyes_closed: bool = False
    short_eye_closure: bool = False
    yawning: bool = False
    distracted: bool = False
    phone_calling: bool = False
    smoking: bool = False
    eye_closure_ratio: float = 0.0
    mouth_open_ratio: float = 0.0
    head_pose_yaw: float = 0.0
    head_pose_pitch: float = 0.0
    fatigue_confidence: float = 0.0
    distraction_confidence: float = 0.0
    phone_confidence: float = 0.0
    smoking_confidence: float = 0.0
    yawning_confidence: float = 0.0
    valid: bool = True
    latency_ms: float = 0.0
    error: str = ""


class CorePerception:
    """Thin perception wrapper that preserves room for MediaPipe and YOLO.

    The current repository only had a placeholder DMS. This class keeps the
    algorithm boundary explicit and returns a stable PerceptionResult even when
    optional detector dependencies are unavailable.
    """

    def __init__(self, config):
        self.config = config
        self.face_cfg = config.get("face", {})
        self.model_cfg = config.get("model", {})
        self._validate_yolo_config()

    def _validate_yolo_config(self):
        weight_path = self.model_cfg.get("yolo_weight_path", "")
        if self.model_cfg.get("require_yolo_weights", False) and weight_path:
            from pathlib import Path

            if not Path(weight_path).exists():
                raise FileNotFoundError(f"YOLO weight file not found: {weight_path}")

    def process(self, frame):
        start = perf_counter()
        result = PerceptionResult()
        if frame is None or getattr(frame, "size", 0) == 0:
            result.valid = False
            result.error = "empty_frame"
            result.latency_ms = (perf_counter() - start) * 1000.0
            return result

        # Placeholder heuristic until MediaPipe and YOLO are wired in this repo:
        # a valid image with no detections is treated as normal with high
        # confidence. The detector-specific code can fill the same dataclass.
        result.eye_closure_ratio = 0.0
        result.mouth_open_ratio = 0.0
        result.fatigue_confidence = 0.0
        result.distraction_confidence = 0.0
        result.phone_confidence = 0.0
        result.smoking_confidence = 0.0
        result.yawning_confidence = 0.0
        result.latency_ms = (perf_counter() - start) * 1000.0
        return result


def confidence_from_threshold(value, threshold, direction):
    if threshold <= 0:
        return 0.0
    if direction == "below":
        return clamp((threshold - value) / threshold)
    return clamp((value - threshold) / threshold)
