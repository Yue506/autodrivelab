import math

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import AdasStatus, ObjectList, Object2DOrBEV


RISK_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle", "pedestrian"}


def normalize_class(name: str) -> str:
    if name.startswith("vehicle.car"):
        return "car"
    if name.startswith("vehicle.truck"):
        return "truck"
    if name.startswith("vehicle.bus"):
        return "bus"
    if name.startswith("vehicle.motorcycle"):
        return "motorcycle"
    if name.startswith("vehicle.bicycle"):
        return "bicycle"
    if name.startswith("human.pedestrian"):
        return "pedestrian"
    return name


def level_for_ttc(ttc: float | None) -> tuple[int, str, str]:
    if ttc is None or not math.isfinite(ttc):
        return 0, "ADAS_NORMAL", "前方无明显碰撞风险"
    if ttc < 3.0:
        return 4, "FCW_EMERGENCY", "TTC 小于 3 秒，触发前向紧急碰撞风险"
    if ttc <= 5.0:
        return 3, "FCW_POTENTIAL", "TTC 在 3 到 5 秒内，触发前向潜在碰撞风险"
    return 0, "ADAS_NORMAL", "前方目标 TTC 未达到告警阈值"


class AdasGtAdapterNode(Node):
    def __init__(self):
        super().__init__("adas_gt_adapter_node")
        self.declare_parameter("front_y_abs_max", 3.5)
        self.status_pub = self.create_publisher(AdasStatus, "/adas/status", 10)
        self.objects_pub = self.create_publisher(ObjectList, "/adas/objects", 10)
        self.create_subscription(ObjectList, "/nuscenes/gt_objects", self.on_objects, 10)
        self.prev_distance_by_id: dict[str, tuple[int, float]] = {}

    def compute_ttc(self, object_id: str, frame_index: int, distance: float) -> tuple[float | None, float]:
        prev = self.prev_distance_by_id.get(object_id)
        relative_speed = 0.0
        ttc = None
        if prev:
            dt = max((int(frame_index) - prev[0]) / 5.0, 1e-3)
            relative_speed = (prev[1] - distance) / dt
            if relative_speed > 0.1:
                ttc = distance / relative_speed
        self.prev_distance_by_id[object_id] = (int(frame_index), distance)
        return ttc, relative_speed

    def on_objects(self, msg: ObjectList):
        front_y = float(self.get_parameter("front_y_abs_max").value)
        out = ObjectList(stamp=msg.stamp, frame_index=msg.frame_index)
        best = None
        for obj in msg.objects:
            cls = normalize_class(obj.class_name)
            distance = math.hypot(float(obj.x), float(obj.y))
            is_front = cls in RISK_CLASSES and obj.x > 0.0 and abs(obj.y) < front_y
            ttc, relative_speed = self.compute_ttc(obj.object_id, msg.frame_index, distance) if is_front else (None, 0.0)
            level, _, _ = level_for_ttc(ttc)
            item = Object2DOrBEV(
                object_id=obj.object_id,
                class_name=cls,
                x=obj.x,
                y=obj.y,
                z=obj.z,
                distance=distance,
                width=obj.width,
                length=obj.length,
                height=obj.height,
                is_front_risk=bool(is_front and level > 0),
                risk_level=level if is_front else 0,
                confidence=1.0,
            )
            out.objects.append(item)
            candidate = {
                "item": item,
                "level": int(level),
                "ttc": float(ttc) if ttc is not None else None,
                "relative_speed": float(relative_speed),
            }
            if item.is_front_risk and (
                best is None
                or candidate["level"] > best["level"]
                or (
                    candidate["level"] == best["level"]
                    and (candidate["ttc"] or float("inf")) < (best["ttc"] or float("inf"))
                )
            ):
                best = candidate
        best_item = best["item"] if best else None
        level, event, desc = level_for_ttc(best["ttc"] if best else None)
        status = AdasStatus(
            stamp=msg.stamp,
            frame_id="base_link",
            frame_index=msg.frame_index,
            adas_level=int(level),
            event_type=event,
            event_description=desc,
            distance=float(best_item.distance) if best_item else 0.0,
            target_object_id=best_item.object_id if best_item else "",
            confidence=1.0,
            valid=True,
        )
        status.ttc = float(best["ttc"]) if best and best["ttc"] is not None else 0.0
        status.relative_speed = float(best["relative_speed"]) if best else 0.0
        status.fcw_active = level >= 3
        status.aeb_active = level >= 4
        self.objects_pub.publish(out)
        self.status_pub.publish(status)


def main():
    rclpy.init()
    node = AdasGtAdapterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
