import json
from pathlib import Path

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import CameraQuality, IqaStatus, NuscenesFrame


CRITICAL = {"CAM_FRONT", "CAM_FRONT_LEFT", "CAM_FRONT_RIGHT"}


def read_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class IqaAdapterNode(Node):
    def __init__(self):
        super().__init__("iqa_adapter_node")
        self.declare_parameter("mode", "scripted")
        self.declare_parameter("iqa_result", "")
        self.declare_parameter("total_frames", 80)
        self.mode = str(self.get_parameter("mode").value)
        result_path = str(self.get_parameter("iqa_result").value)
        self.results = read_jsonl(result_path) if result_path else []
        self.status_by_frame = {int(row.get("frame_index", idx)): row for idx, row in enumerate(self.results)}
        self.pub = self.create_publisher(IqaStatus, "/iqa/status", 10)
        self.create_subscription(NuscenesFrame, "/nuscenes/frame", self.on_frame, 10)
        self.get_logger().info(f"IQA adapter mode={self.mode}, results={len(self.results)}")

    def scripted_row(self, frame: NuscenesFrame) -> dict:
        ratio = frame.frame_index / max(int(self.get_parameter("total_frames").value), 1)
        soiled = 0.50 <= ratio < 0.75
        return {
            "frame_index": frame.frame_index,
            "timestamp": 0,
            "iqa_level": 3 if soiled else 0,
            "soiled_camera_count": 1 if soiled else 0,
            "soiled_cameras": ["CAM_FRONT"] if soiled else [],
            "critical_camera_soiled": soiled,
            "confidence": 0.92 if soiled else 1.0,
            "source": "scripted",
            "source_image": "",
            "quality_state": "soiling" if soiled else "normal",
        }

    def on_frame(self, frame: NuscenesFrame):
        row = self.status_by_frame.get(frame.frame_index) if self.mode in {"offline_result", "offline_test_result"} else None
        if row is None:
            row = self.scripted_row(frame)
        cameras = []
        states = row.get("camera_states", {})
        if states:
            for name, state in states.items():
                cameras.append(self.to_camera(name, state))
        else:
            for name in row.get("soiled_cameras", []):
                cameras.append(self.to_camera(name, {"quality_state": "soiling", "soiling_score": row.get("confidence", 1.0), "is_soiled": True}))
        msg = IqaStatus(
            stamp=frame.stamp,
            frame_id="base_link",
            frame_index=frame.frame_index,
            cameras=cameras,
            iqa_level=int(row.get("iqa_level", 0)),
            soiled_camera_count=int(row.get("soiled_camera_count", len(row.get("soiled_cameras", [])))),
            soiled_cameras=list(row.get("soiled_cameras", [])),
            critical_camera_soiled=bool(row.get("critical_camera_soiled", False)),
            confidence=float(row.get("confidence", 1.0)),
            source=str(row.get("source", "custom_iqa_test_dataset" if self.mode != "scripted" else "scripted")),
            source_image=str(row.get("source_image", "")),
            quality_state=str(row.get("quality_state", "soiling" if row.get("soiled_cameras") else "normal")),
            valid=bool(row.get("valid", True)),
        )
        self.pub.publish(msg)

    def to_camera(self, name: str, state: dict) -> CameraQuality:
        score = float(state.get("soiling_score", 0.0))
        is_soiled = bool(state.get("is_soiled", state.get("quality_state") == "soiling" or score >= 0.5))
        return CameraQuality(
            camera_name=name,
            usable=not is_soiled,
            quality_state="soiling" if is_soiled else "normal",
            soiling_score=score,
            is_soiled=is_soiled,
            is_critical=name in CRITICAL,
        )


def main():
    rclpy.init()
    node = IqaAdapterNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
