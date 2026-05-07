from __future__ import annotations

import rclpy
from rclpy.node import Node

from arbiter_can.can_encoder import encode_fusion_to_can_frame
from autodrivelab_msgs.msg import CanFrame, FusionRiskStatus


class FusionToAutodriveLabBridgeNode(Node):
    def __init__(self):
        super().__init__("fusion_to_autodrivelab_bridge_node")
        self._rolling_counter = 0
        self._fusion_pub = self.create_publisher(FusionRiskStatus, "/autodrivelab/fusion/risk_status", 10)
        self._can_pub = self.create_publisher(CanFrame, "/autodrivelab/can/tx", 10)
        self._fusion_sub = self.create_subscription(FusionRiskStatus, "/fusion/risk_status", self.on_fusion_status, 10)
        self.get_logger().info(
            "Fusion bridge started: /fusion/risk_status -> /autodrivelab/fusion/risk_status, /autodrivelab/can/tx"
        )

    def on_fusion_status(self, msg: FusionRiskStatus) -> None:
        self._fusion_pub.publish(msg)
        try:
            can_frame = encode_fusion_to_can_frame(msg, self._rolling_counter)
        except Exception as exc:
            self.get_logger().warn(f"Failed to encode fusion status as CanFrame: {exc}")
            return
        self._rolling_counter = (self._rolling_counter + 1) & 0xFF
        self._can_pub.publish(can_frame)
        self.get_logger().info(
            f"bridged fusion level={int(msg.unified_risk_level)} event={msg.primary_event}",
            throttle_duration_sec=1.0,
        )


def main():
    rclpy.init()
    node = FusionToAutodriveLabBridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
