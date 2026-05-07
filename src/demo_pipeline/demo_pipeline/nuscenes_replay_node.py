from pathlib import Path
import time

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import NuscenesFrame, Object2DOrBEV, ObjectList

from .common import CAMERA_FIELDS, read_jsonl, stamp_from_us


class NuscenesReplayNode(Node):
    def __init__(self):
        super().__init__("nuscenes_replay_node")
        self.declare_parameter("cache_dir", "demo_outputs/scene_000/demo_cache")
        self.declare_parameter("fps", 10)
        self.declare_parameter("loop", False)
        self.cache_dir = Path(self.get_parameter("cache_dir").value)
        self.frames = read_jsonl(self.cache_dir / "frames.jsonl")
        self.gt_rows = read_jsonl(self.cache_dir / "gt_objects.jsonl")
        self.index = 0
        self.start_time = time.time()
        self.loop = bool(self.get_parameter("loop").value)
        self.frame_pub = self.create_publisher(NuscenesFrame, "/nuscenes/frame", 10)
        self.objects_pub = self.create_publisher(ObjectList, "/nuscenes/gt_objects", 10)
        period = 1.0 / max(float(self.get_parameter("fps").value), 0.1)
        self.timer = self.create_timer(period, self.on_timer)
        self.get_logger().info(f"nuScenes replay loaded {len(self.frames)} frames from {self.cache_dir}")

    def on_timer(self):
        if time.time() - self.start_time < 1.5:
            return
        if self.index >= len(self.frames):
            if self.loop:
                self.index = 0
            else:
                self.timer.cancel()
                return
        frame = self.frames[self.index]
        objects = self.gt_rows[self.index]
        stamp = self.get_clock().now().to_msg()
        frame_msg = NuscenesFrame(stamp=stamp, frame_index=int(frame["frame_index"]), scene_token=frame["scene_token"], sample_token=frame["sample_token"])
        for camera, field in CAMERA_FIELDS.items():
            setattr(frame_msg, field, str(self.cache_dir / frame.get("camera_images", {}).get(camera, "")))
        object_msg = ObjectList(stamp=stamp, frame_index=int(frame["frame_index"]))
        for obj in objects.get("objects", []):
            x, y, z = [float(v) for v in obj.get("translation_ego", [0.0, 0.0, 0.0])]
            size = obj.get("size", [0.0, 0.0, 0.0])
            object_msg.objects.append(
                Object2DOrBEV(
                    object_id=obj.get("instance_token") or obj.get("sample_annotation_token", ""),
                    class_name=obj.get("category_name", "unknown"),
                    x=x,
                    y=y,
                    z=z,
                    distance=(x * x + y * y) ** 0.5,
                    width=float(size[0]) if len(size) > 0 else 0.0,
                    length=float(size[1]) if len(size) > 1 else 0.0,
                    height=float(size[2]) if len(size) > 2 else 0.0,
                    confidence=1.0,
                )
            )
        self.frame_pub.publish(frame_msg)
        self.objects_pub.publish(object_msg)
        self.index += 1


def main():
    rclpy.init()
    node = NuscenesReplayNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
