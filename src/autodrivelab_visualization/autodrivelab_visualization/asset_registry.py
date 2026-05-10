from dataclasses import dataclass

from visualization_msgs.msg import Marker


@dataclass(frozen=True)
class MarkerSpec:
    marker_type: int
    size_xyz: tuple[float, float, float]
    color_rgba: tuple[float, float, float, float]
    label: str


CLASS_ALIASES = {
    "car": "vehicle",
    "truck": "vehicle",
    "bus": "vehicle",
    "trailer": "vehicle",
    "vehicle": "vehicle",
    "ped": "pedestrian",
    "person": "pedestrian",
    "pedestrian": "pedestrian",
    "bike": "cyclist",
    "bicycle": "cyclist",
    "motorcycle": "cyclist",
    "cyclist": "cyclist",
    "barrier": "barrier",
    "traffic_cone": "cone",
    "cone": "cone",
}


MARKER_SPECS = {
    "vehicle": MarkerSpec(Marker.CUBE, (3.8, 1.7, 1.5), (0.16, 0.46, 0.95, 0.88), "vehicle"),
    "pedestrian": MarkerSpec(Marker.CYLINDER, (0.7, 0.7, 1.7), (0.98, 0.70, 0.12, 0.90), "pedestrian"),
    "cyclist": MarkerSpec(Marker.CUBE, (1.8, 0.7, 1.4), (0.19, 0.78, 0.46, 0.88), "cyclist"),
    "barrier": MarkerSpec(Marker.CUBE, (1.6, 0.45, 0.8), (0.72, 0.75, 0.78, 0.58), "barrier"),
    "cone": MarkerSpec(Marker.CYLINDER, (0.55, 0.55, 0.9), (1.00, 0.42, 0.10, 0.70), "cone"),
    "unknown": MarkerSpec(Marker.CUBE, (1.0, 1.0, 1.0), (0.60, 0.60, 0.65, 0.60), "unknown"),
}


def normalize_class(object_class: str) -> str:
    key = (object_class or "").strip().lower().replace(".", "_").replace("-", "_")
    return CLASS_ALIASES.get(key, "unknown")


def get_marker_spec(object_class: str) -> MarkerSpec:
    return MARKER_SPECS[normalize_class(object_class)]
