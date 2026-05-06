import math

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import BevObject, BevObjects, EgoState


class BevPerceptionNode(Node):
    def __init__(self):
        super().__init__("bev_perception_node")
        self.publisher = self.create_publisher(BevObjects, "/autodrivelab/bev/objects", 10)
        self.subscription = self.create_subscription(EgoState, "/autodrivelab/ego_state", self.on_ego, 10)
        self.tick = 0
        self.get_logger().info("BEV perception placeholder started.")

    def on_ego(self, ego: EgoState):
        msg = BevObjects()
        msg.header.stamp = ego.header.stamp
        msg.header.frame_id = "base_link"
        msg.lanes = ["left_lane", "ego_lane", "right_lane"]

        lead = BevObject()
        lead.track_id = "mock_lead_vehicle"
        lead.object_class = "vehicle"
        lead.x_m = 18.0 - 6.0 * math.sin(self.tick / 35.0)
        lead.y_m = 0.3
        lead.vx_mps = ego.speed_mps - 2.5
        lead.vy_mps = 0.0
        lead.yaw_rad = 0.0
        lead.confidence = 0.92

        blind_spot = BevObject()
        blind_spot.track_id = "mock_left_blind_spot"
        blind_spot.object_class = "vehicle"
        blind_spot.x_m = -5.0
        blind_spot.y_m = 3.2
        blind_spot.vx_mps = ego.speed_mps + 1.0
        blind_spot.vy_mps = 0.0
        blind_spot.yaw_rad = 0.0
        blind_spot.confidence = 0.86

        msg.objects = [lead, blind_spot]
        self.publisher.publish(msg)
        self.tick += 1


def main():
    rclpy.init()
    node = BevPerceptionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
