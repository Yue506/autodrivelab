import math

from geometry_msgs.msg import Point, Quaternion
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker


def yaw_to_quaternion(yaw_rad: float) -> Quaternion:
    half = 0.5 * yaw_rad
    quat = Quaternion()
    quat.x = 0.0
    quat.y = 0.0
    quat.z = math.sin(half)
    quat.w = math.cos(half)
    return quat


def rgba_to_msg(rgba: tuple[float, float, float, float], alpha_scale: float = 1.0) -> ColorRGBA:
    color = ColorRGBA()
    color.r = float(rgba[0])
    color.g = float(rgba[1])
    color.b = float(rgba[2])
    color.a = max(0.08, min(1.0, float(rgba[3]) * alpha_scale))
    return color


def make_delete_all_marker(frame_id: str) -> Marker:
    marker = Marker()
    marker.header.frame_id = frame_id
    marker.ns = "autodrivelab_clear"
    marker.id = 0
    marker.action = Marker.DELETEALL
    return marker


def make_velocity_arrow(frame_id: str, marker_id: int, obj, color: ColorRGBA) -> Marker:
    marker = Marker()
    marker.header.frame_id = frame_id
    marker.ns = "autodrivelab_velocity"
    marker.id = marker_id
    marker.type = Marker.ARROW
    marker.action = Marker.ADD

    start = Point()
    start.x = float(obj.x_m)
    start.y = float(obj.y_m)
    start.z = 0.35

    end = Point()
    end.x = float(obj.x_m) + float(obj.vx_mps) * 0.55
    end.y = float(obj.y_m) + float(obj.vy_mps) * 0.55
    end.z = 0.35

    marker.points = [start, end]
    marker.scale.x = 0.08
    marker.scale.y = 0.18
    marker.scale.z = 0.22
    marker.color = color
    return marker
