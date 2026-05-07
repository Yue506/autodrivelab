import time

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import AdasStatus, DmsStatus, FusionEvent, FusionRiskStatus, IqaStatus, SourceStatus

from .event_builder import build_fusion_events
from .iqa_gate import apply_iqa_gate, compute_iqa_level, count_soiled_cameras, has_critical_camera_soiled
from .risk_matrix import fuse_adas_dms
from .time_sync_buffer import TimeSyncBuffer
from .utils import load_yaml


class ArbitrationNode(Node):
    def __init__(self):
        super().__init__("arbitration_node")
        self.declare_parameter("config_path", "")
        config_path = self.get_parameter("config_path").get_parameter_value().string_value
        self.config = load_yaml(config_path) if config_path else {}
        ros_cfg = self.config.get("ros", {})
        sync_cfg = self.config.get("sync", {})
        self.iqa_cfg = self.config.get("iqa", {})
        self.risk_cfg = self.config.get("risk", {})
        self.buffer = TimeSyncBuffer(
            sync_cfg.get("time_window_ms", 100),
            sync_cfg.get("adas_timeout_ms", 200),
            sync_cfg.get("dms_timeout_ms", 500),
            sync_cfg.get("iqa_timeout_ms", 1500),
        )
        self.publisher = self.create_publisher(FusionRiskStatus, ros_cfg.get("fusion_topic", "/fusion/risk_status"), 10)
        self.create_subscription(AdasStatus, ros_cfg.get("adas_topic", "/adas/status"), self.on_adas, 10)
        self.create_subscription(DmsStatus, ros_cfg.get("dms_topic", "/dms/status"), self.on_dms, 10)
        self.create_subscription(IqaStatus, ros_cfg.get("iqa_topic", "/iqa/status"), self.on_iqa, 10)
        self.get_logger().info("Arbitration node started.")

    def on_adas(self, msg):
        self.buffer.update_adas(msg)
        if int(getattr(msg, "adas_level", 0)) >= self.config.get("priority", {}).get("immediate_adas_level", 3):
            self.publish_fusion()

    def on_dms(self, msg):
        self.buffer.update_dms(msg)
        self.publish_fusion()

    def on_iqa(self, msg):
        self.buffer.update_iqa(msg)
        self.publish_fusion()

    def publish_fusion(self):
        start = time.perf_counter()
        now = self.get_clock().now().to_msg()
        adas, dms, iqa, status = self.buffer.get_latest_tuple(now)
        adas_level = int(getattr(adas, "adas_level", 0))
        dms_level = int(getattr(dms, "danger_level", 0))
        base_level = fuse_adas_dms(adas_level, dms_level, status.adas_valid, status.dms_valid)

        if status.iqa_valid and iqa is not None:
            soiled = count_soiled_cameras(iqa, self.iqa_cfg)
            status.soiled_camera_count = len(soiled)
            status.soiled_cameras = [c.camera_name for c in soiled]
            status.critical_camera_soiled = has_critical_camera_soiled(soiled, self.iqa_cfg)
            status.iqa_level = compute_iqa_level(iqa, self.iqa_cfg)
        if self.risk_cfg.get("enable_iqa_gate", True):
            unified_level, status.perception_degraded = apply_iqa_gate(
                base_level, status.iqa_level, status.iqa_valid, self.iqa_cfg
            )
        else:
            unified_level = base_level

        status.fusion_latency_ms = (time.perf_counter() - start) * 1000.0
        primary_source, primary_event, primary_description, events, confidence = build_fusion_events(
            adas, dms, iqa, unified_level, status
        )
        msg = self._build_msg(now, adas, unified_level, primary_source, primary_event, primary_description, events, status, confidence)
        self.publisher.publish(msg)

    def _build_msg(self, now, adas, unified_level, primary_source, primary_event, primary_description, events, status, confidence):
        msg = FusionRiskStatus()
        msg.stamp = now
        msg.frame_id = getattr(adas, "frame_id", "base_link") if adas is not None else "base_link"
        msg.frame_index = int(getattr(adas, "frame_index", getattr(status, "frame_index", -1)))
        msg.unified_risk_level = int(unified_level)
        msg.primary_source = primary_source
        msg.primary_event = primary_event
        msg.primary_description = primary_description
        msg.triggered_events = [self._to_event(event) for event in events]
        msg.source_status = self._to_source_status(status)
        msg.valid = bool(status.adas_valid or status.dms_valid or status.iqa_valid)
        msg.confidence = float(confidence if msg.valid else 0.0)
        return msg

    def _to_event(self, data):
        msg = FusionEvent()
        msg.source = data["source"]
        msg.event_type = data["event_type"]
        msg.level = int(data["level"])
        msg.description = data["description"]
        msg.confidence = float(data["confidence"])
        return msg

    def _to_source_status(self, data):
        msg = SourceStatus()
        msg.adas_valid = data.adas_valid
        msg.dms_valid = data.dms_valid
        msg.iqa_valid = data.iqa_valid
        if data.adas_stamp is not None:
            msg.adas_stamp = data.adas_stamp
        if data.dms_stamp is not None:
            msg.dms_stamp = data.dms_stamp
        if data.iqa_stamp is not None:
            msg.iqa_stamp = data.iqa_stamp
        msg.adas_age_ms = float(data.adas_age_ms)
        msg.dms_age_ms = float(data.dms_age_ms)
        msg.iqa_age_ms = float(data.iqa_age_ms)
        msg.adas_dms_time_diff_ms = float(data.adas_dms_time_diff_ms)
        msg.fusion_latency_ms = float(data.fusion_latency_ms)
        msg.adas_timeout = data.adas_timeout
        msg.dms_timeout = data.dms_timeout
        msg.iqa_timeout = data.iqa_timeout
        msg.perception_degraded = data.perception_degraded
        msg.iqa_level = int(data.iqa_level)
        msg.soiled_camera_count = int(data.soiled_camera_count)
        msg.soiled_cameras = list(data.soiled_cameras)
        msg.critical_camera_soiled = data.critical_camera_soiled
        return msg


def main():
    rclpy.init()
    node = ArbitrationNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
