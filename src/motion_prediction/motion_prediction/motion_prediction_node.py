import math

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import BevObjects, EgoState, RiskMetrics


class MotionPredictionNode(Node):
    def __init__(self):
        super().__init__("motion_prediction_node")
        self.ego = None
        self.publisher = self.create_publisher(RiskMetrics, "/autodrivelab/risk_metrics", 10)
        self.ego_sub = self.create_subscription(EgoState, "/autodrivelab/ego_state", self.on_ego, 10)
        self.bev_sub = self.create_subscription(BevObjects, "/autodrivelab/bev/objects", self.on_bev, 10)
        self.get_logger().info("Motion prediction node started.")

    def on_ego(self, ego: EgoState):
        self.ego = ego

    def on_bev(self, bev: BevObjects):
        if self.ego is None:
            return

        min_ttc = float("inf")
        events = []
        for obj in bev.objects:
            distance = math.hypot(obj.x_m, obj.y_m)
            closing_speed = max(self.ego.speed_mps - obj.vx_mps, 0.0)
            ttc = distance / closing_speed if closing_speed > 0.1 else float("inf")
            min_ttc = min(min_ttc, ttc)
            if -15.0 <= obj.x_m <= 2.0 and 1.5 <= obj.y_m <= 4.5:
                events.append("BSD_ACTIVE")
            if ttc < 5.0 and obj.x_m > 0.0:
                events.append("FCW_POTENTIAL")

        msg = RiskMetrics()
        msg.header.stamp = bev.header.stamp
        msg.header.frame_id = "base_link"
        msg.min_ttc_s = 999.0 if math.isinf(min_ttc) else float(min_ttc)
        msg.active_events = sorted(set(events))
        if min_ttc < 3.0:
            msg.risk_level = 4
        elif min_ttc < 5.0:
            msg.risk_level = 3
        elif "BSD_ACTIVE" in msg.active_events:
            msg.risk_level = 2
        else:
            msg.risk_level = 1
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = MotionPredictionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
