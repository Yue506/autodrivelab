import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

from autodrivelab_msgs.msg import DmsStatus

from .core_perception import CorePerception
from .event_mapper import map_dms_event
from .temporal_filter import TemporalFilter
from .utils import load_yaml
from .visualizer import draw_dms_overlay


class DmsNode(Node):
    def __init__(self):
        super().__init__("dms_node")
        self.declare_parameter("config_path", "")
        config_path = self.get_parameter("config_path").get_parameter_value().string_value
        self.config = load_yaml(config_path) if config_path else {}
        self.ros_cfg = self.config.get("ros", {})
        self.runtime_cfg = self.config.get("runtime", {})

        from cv_bridge import CvBridge

        self.bridge = CvBridge()
        self.perception = CorePerception(self.config)
        self.temporal_filter = TemporalFilter(self.config.get("temporal_filter", {}))
        self.status_pub = self.create_publisher(
            DmsStatus, self.ros_cfg.get("output_status_topic", "/dms/status"), 10
        )
        self.vis_pub = None
        if self.ros_cfg.get("publish_visualization", True):
            self.vis_pub = self.create_publisher(Image, self.ros_cfg.get("output_vis_topic", "/dms/vis_image"), 10)
        self.image_sub = self.create_subscription(
            Image, self.ros_cfg.get("input_image_topic", "/camera/dms/image_raw"), self.on_image, 10
        )
        self.get_logger().info("DMS node started.")

    def on_image(self, image_msg):
        start = time.perf_counter()
        try:
            frame = self.bridge.imgmsg_to_cv2(image_msg, desired_encoding="bgr8")
            perception_result = self.perception.process(frame)
        except Exception as exc:
            self.get_logger().warning(f"DMS frame processing failed: {exc}")
            frame = None
            perception_result = self.perception.process(None)
            perception_result.error = str(exc)

        raw_event = map_dms_event(perception_result)
        event = self.temporal_filter.update(raw_event)
        latency_ms = (time.perf_counter() - start) * 1000.0
        max_latency_ms = self.runtime_cfg.get("max_latency_ms", 100)
        valid = bool(event.valid and latency_ms <= max_latency_ms)
        if not valid:
            event = map_dms_event(type("Invalid", (), {"valid": False})())

        status = self._build_status(image_msg, event, perception_result, latency_ms, valid)
        self.status_pub.publish(status)
        if self.vis_pub is not None and frame is not None:
            vis = draw_dms_overlay(frame.copy(), event, perception_result)
            self.vis_pub.publish(self.bridge.cv2_to_imgmsg(vis, encoding="bgr8"))

    def _build_status(self, image_msg, event, perception_result, latency_ms, valid):
        msg = DmsStatus()
        msg.stamp = image_msg.header.stamp
        msg.frame_id = image_msg.header.frame_id or "dms_camera"
        msg.danger_level = int(event.danger_level if valid else 0)
        msg.event_type = event.event_type if valid else "DMS_INVALID"
        msg.event_description = event.event_description if valid else "DMS data invalid"
        msg.fatigue_level = int(event.fatigue_level if valid else 0)
        msg.distraction_level = int(event.distraction_level if valid else 0)
        msg.violation_level = int(event.violation_level if valid else 0)
        msg.is_fatigue = msg.fatigue_level > 0
        msg.is_distracted = bool(getattr(perception_result, "distracted", False))
        msg.is_phone_calling = bool(getattr(perception_result, "phone_calling", False))
        msg.is_smoking = bool(getattr(perception_result, "smoking", False))
        msg.is_yawning = bool(getattr(perception_result, "yawning", False))
        msg.eye_closure_ratio = float(getattr(perception_result, "eye_closure_ratio", 0.0))
        msg.mouth_open_ratio = float(getattr(perception_result, "mouth_open_ratio", 0.0))
        msg.head_pose_yaw = float(getattr(perception_result, "head_pose_yaw", 0.0))
        msg.head_pose_pitch = float(getattr(perception_result, "head_pose_pitch", 0.0))
        msg.confidence = float(event.confidence if valid else 0.0)
        msg.fatigue_confidence = float(getattr(perception_result, "fatigue_confidence", 0.0))
        msg.distraction_confidence = float(getattr(perception_result, "distraction_confidence", 0.0))
        msg.phone_confidence = float(getattr(perception_result, "phone_confidence", 0.0))
        msg.smoking_confidence = float(getattr(perception_result, "smoking_confidence", 0.0))
        msg.yawning_confidence = float(getattr(perception_result, "yawning_confidence", 0.0))
        msg.valid = valid
        msg.latency_ms = float(latency_ms)
        return msg


def main():
    rclpy.init()
    node = DmsNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
