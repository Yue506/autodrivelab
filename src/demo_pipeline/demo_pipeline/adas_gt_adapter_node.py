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


def level_for_distance(distance: float) -> tuple[int, str, str]:
    if distance <= 4.0:
        return 4, "FCW_EMERGENCY", "前方目标距离极近，触发紧急风险"
    if distance <= 8.0:
        return 3, "FCW_WARNING", "前方目标距离过近，请减速"
    if distance <= 15.0:
        return 2, "FRONT_OBJECT_ATTENTION", "前方目标较近，请保持注意"
    if distance <= 30.0:
        return 1, "FRONT_OBJECT_NEARBY", "前方目标进入关注区域"
    return 0, "ADAS_NORMAL", "前方无明显碰撞风险"


class AdasGtAdapterNode(Node):
    def __init__(self):
        super().__init__("adas_gt_adapter_node")
        self.declare_parameter("front_y_abs_max", 3.5)
        self.status_pub = self.create_publisher(AdasStatus, "/adas/status", 10)
        self.objects_pub = self.create_publisher(ObjectList, "/adas/objects", 10)
        self.create_subscription(ObjectList, "/nuscenes/gt_objects", self.on_objects, 10)

    def on_objects(self, msg: ObjectList):
        front_y = float(self.get_parameter("front_y_abs_max").value)
        out = ObjectList(stamp=msg.stamp, frame_index=msg.frame_index)
        best = None
        for obj in msg.objects:
            cls = normalize_class(obj.class_name)
            distance = math.hypot(float(obj.x), float(obj.y))
            level, _, _ = level_for_distance(distance)
            is_front = cls in RISK_CLASSES and obj.x > 0.0 and abs(obj.y) < front_y
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
            if item.is_front_risk and (best is None or item.distance < best.distance):
                best = item
        level, event, desc = level_for_distance(best.distance) if best else level_for_distance(float("inf"))
        status = AdasStatus(
            stamp=msg.stamp,
            frame_id="base_link",
            frame_index=msg.frame_index,
            adas_level=int(level),
            event_type=event,
            event_description=desc,
            distance=float(best.distance) if best else 0.0,
            target_object_id=best.object_id if best else "",
            confidence=1.0,
            valid=True,
        )
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
