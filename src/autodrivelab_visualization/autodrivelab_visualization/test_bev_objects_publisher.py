import math

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import BevObject, BevObjects


class TestBevObjectsPublisher(Node):
    def __init__(self):
        super().__init__("test_bev_objects_publisher")
        self.publisher = self.create_publisher(BevObjects, "/bev_objects", 10)
        self.timer = self.create_timer(0.2, self.on_timer)
        self.t = 0.0
        self.get_logger().info("Publishing sample BevObjects on /bev_objects.")

    def on_timer(self):
        msg = BevObjects()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"

        lead = BevObject()
        lead.track_id = "car_001"
        lead.object_class = "vehicle"
        lead.x_m = 8.0 + math.sin(self.t) * 0.8
        lead.y_m = 1.5
        lead.vx_mps = -0.6
        lead.vy_mps = 0.0
        lead.yaw_rad = 0.0
        lead.confidence = 0.95

        ped = BevObject()
        ped.track_id = "ped_001"
        ped.object_class = "pedestrian"
        ped.x_m = 5.0
        ped.y_m = -2.5
        ped.vx_mps = 0.0
        ped.vy_mps = 0.2
        ped.yaw_rad = math.pi / 2.0
        ped.confidence = 0.90

        cyclist = BevObject()
        cyclist.track_id = "cyc_001"
        cyclist.object_class = "cyclist"
        cyclist.x_m = 12.0
        cyclist.y_m = -1.0
        cyclist.vx_mps = 1.0
        cyclist.vy_mps = 0.0
        cyclist.yaw_rad = 0.0
        cyclist.confidence = 0.80

        barrier = BevObject()
        barrier.track_id = "barrier_001"
        barrier.object_class = "barrier"
        barrier.x_m = 3.0
        barrier.y_m = 2.6
        barrier.vx_mps = 0.0
        barrier.vy_mps = 0.0
        barrier.yaw_rad = 0.0
        barrier.confidence = 0.75

        msg.objects = [lead, ped, cyclist, barrier]
        msg.lanes = ["left_lane", "ego_lane", "right_lane"]
        self.publisher.publish(msg)
        self.t += 0.2


def main(args=None):
    rclpy.init(args=args)
    node = TestBevObjectsPublisher()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
