import json
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import AdasStatus, DmsStatus, FusionRiskStatus, IqaStatus, NuscenesFrame, ObjectList

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools"))
from demo.offline_mvp import render_video, write_jsonl  # noqa: E402


class RenderRecorderNode(Node):
    def __init__(self):
        super().__init__("render_recorder_node")
        self.declare_parameter("cache_dir", "demo_outputs/scene_000/demo_cache")
        self.declare_parameter("scene_dir", "demo_outputs/scene_000")
        self.declare_parameter("out", "demo_outputs/scene_000/demo_ros2.mp4")
        self.declare_parameter("fps", 10)
        self.declare_parameter("expected_frames", 0)
        self.scene_dir = Path(str(self.get_parameter("scene_dir").value))
        self.cache_dir = Path(str(self.get_parameter("cache_dir").value))
        self.expected_frames = int(self.get_parameter("expected_frames").value)
        self.frames = {}
        self.objects = {}
        self.adas = {}
        self.dms = {}
        self.iqa = {}
        self.fusion = {}
        self.done = False
        self.last_update = time.time()
        self.create_timer(1.0, self.maybe_finalize)
        self.create_subscription(NuscenesFrame, "/nuscenes/frame", self.on_frame, 10)
        self.create_subscription(ObjectList, "/adas/objects", self.on_objects, 10)
        self.create_subscription(AdasStatus, "/adas/status", self.on_adas, 10)
        self.create_subscription(DmsStatus, "/dms/status", self.on_dms, 10)
        self.create_subscription(IqaStatus, "/iqa/status", self.on_iqa, 10)
        self.create_subscription(FusionRiskStatus, "/fusion/risk_status", self.on_fusion, 10)

    def on_frame(self, msg):
        self.last_update = time.time()
        self.frames[msg.frame_index] = {"frame_index": msg.frame_index, "timestamp": msg.stamp.sec * 1_000_000 + msg.stamp.nanosec // 1000, "camera_images": {}}
        self.check_done()

    def on_objects(self, msg):
        self.last_update = time.time()
        self.objects[msg.frame_index] = {"frame_index": msg.frame_index, "timestamp": 0, "objects": [self.object_to_dict(o) for o in msg.objects]}
        self.check_done()

    def on_adas(self, msg):
        self.last_update = time.time()
        self.adas[msg.frame_index] = {"frame_index": msg.frame_index, "timestamp": 0, "adas_level": msg.adas_level, "event_type": msg.event_type, "event_description": msg.event_description, "target_object_id": msg.target_object_id, "front_object_distance": msg.distance or None, "confidence": msg.confidence, "valid": msg.valid}
        self.check_done()

    def on_dms(self, msg):
        self.last_update = time.time()
        self.dms[msg.frame_index] = {"frame_index": msg.frame_index, "timestamp": 0, "danger_level": msg.danger_level, "event_type": msg.event_type, "event_description": msg.event_description, "confidence": msg.confidence, "valid": msg.valid}
        self.check_done()

    def on_iqa(self, msg):
        self.last_update = time.time()
        self.iqa[msg.frame_index] = {"frame_index": msg.frame_index, "timestamp": 0, "iqa_level": msg.iqa_level, "soiled_camera_count": msg.soiled_camera_count, "soiled_cameras": list(msg.soiled_cameras), "critical_camera_soiled": msg.critical_camera_soiled, "confidence": msg.confidence, "source": msg.source, "source_image": msg.source_image, "quality_state": msg.quality_state, "valid": msg.valid}
        self.check_done()

    def on_fusion(self, msg):
        self.last_update = time.time()
        self.fusion[msg.frame_index] = {"frame_index": msg.frame_index, "timestamp": 0, "unified_risk_level": msg.unified_risk_level, "primary_source": msg.primary_source, "primary_event": msg.primary_event, "primary_description": msg.primary_description, "triggered_events": [{"source": e.source, "event_type": e.event_type, "level": e.level, "description": e.description, "confidence": e.confidence} for e in msg.triggered_events], "source_status": {"perception_degraded": msg.source_status.perception_degraded, "iqa_level": msg.source_status.iqa_level, "soiled_camera_count": msg.source_status.soiled_camera_count, "soiled_cameras": list(msg.source_status.soiled_cameras), "critical_camera_soiled": msg.source_status.critical_camera_soiled}, "valid": msg.valid, "confidence": msg.confidence}
        self.check_done()

    def maybe_finalize(self):
        if self.done or not self.expected_frames:
            return
        if len(self.frames) >= self.expected_frames and time.time() - self.last_update > 2.0:
            self.done = True
            self.render()

    def object_to_dict(self, obj):
        return {"object_id": obj.object_id, "class_name": obj.class_name, "x": obj.x, "y": obj.y, "z": obj.z, "distance": obj.distance, "is_front_risk": obj.is_front_risk, "risk_level": obj.risk_level, "size": [obj.width, obj.length, obj.height]}

    def check_done(self):
        if self.done or not self.expected_frames:
            return
        stores = [self.objects, self.adas, self.dms, self.iqa, self.fusion]
        if len(self.fusion) >= self.expected_frames and all(len(s) >= self.expected_frames for s in stores):
            self.done = True
            self.render()

    def render(self):
        self.scene_dir.mkdir(parents=True, exist_ok=True)
        object_rows = self.fill_rows(self.objects, {"objects": []})
        adas_rows = self.fill_rows(self.adas, {"adas_level": 0, "event_type": "ADAS_NORMAL", "event_description": "前方无明显碰撞风险", "target_object_id": "", "front_object_distance": None, "confidence": 1.0, "valid": True})
        dms_rows = self.fill_rows(self.dms, {"danger_level": 0, "event_type": "DRIVER_NORMAL", "event_description": "驾驶员状态正常", "confidence": 1.0, "valid": True})
        iqa_rows = self.fill_rows(self.iqa, {"iqa_level": 0, "soiled_camera_count": 0, "soiled_cameras": [], "critical_camera_soiled": False, "confidence": 1.0, "source": "scripted", "source_image": "", "quality_state": "normal", "valid": True})
        fusion_rows = self.fill_rows(self.fusion, {"unified_risk_level": 0, "primary_source": "FUSION", "primary_event": "SAFE", "primary_description": "All active sources normal", "triggered_events": [], "source_status": {"perception_degraded": False, "iqa_level": 0, "soiled_camera_count": 0, "soiled_cameras": [], "critical_camera_soiled": False}, "valid": True, "confidence": 1.0})
        write_jsonl(self.scene_dir / "ros2_adas_objects.jsonl", object_rows)
        write_jsonl(self.scene_dir / "ros2_adas_status.jsonl", adas_rows)
        write_jsonl(self.scene_dir / "ros2_dms_status.jsonl", dms_rows)
        write_jsonl(self.scene_dir / "ros2_iqa_status.jsonl", iqa_rows)
        write_jsonl(self.scene_dir / "ros2_fusion_status.jsonl", fusion_rows)
        args = type("Args", (), {"cache": self.cache_dir, "adas_objects": self.scene_dir / "ros2_adas_objects.jsonl", "adas_status": self.scene_dir / "ros2_adas_status.jsonl", "dms_status": self.scene_dir / "ros2_dms_status.jsonl", "iqa_status": self.scene_dir / "ros2_iqa_status.jsonl", "fusion_status": self.scene_dir / "ros2_fusion_status.jsonl", "out": Path(str(self.get_parameter("out").value)), "fps": int(self.get_parameter("fps").value)})
        render_video(args)
        self.get_logger().info(f"ROS2 demo video written: {args.out}")

    def fill_rows(self, store, default):
        latest = dict(default)
        rows = []
        for i in range(self.expected_frames):
            if i in store:
                latest = dict(store[i])
            row = dict(latest)
            row.setdefault("timestamp", 0)
            row["frame_index"] = i
            rows.append(row)
        return rows


def main():
    rclpy.init()
    node = RenderRecorderNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
