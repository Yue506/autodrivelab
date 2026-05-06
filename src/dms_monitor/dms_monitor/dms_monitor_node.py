import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import DriverState, EgoState


class DmsMonitorNode(Node):
    def __init__(self):
        super().__init__("dms_monitor_node")
        self.publisher = self.create_publisher(DriverState, "/autodrivelab/cabin/driver_state", 10)
        self.subscription = self.create_subscription(EgoState, "/autodrivelab/ego_state", self.on_tick, 10)
        self.tick = 0
        self.get_logger().info("DMS monitor placeholder started.")

    def on_tick(self, ego: EgoState):
        msg = DriverState()
        msg.header.stamp = ego.header.stamp
        msg.header.frame_id = "cabin_camera"
        distracted = self.tick % 180 > 135
        msg.danger_level = 3 if distracted else 0
        msg.event_type = "PHONE_CALLING" if distracted else "NORMAL"
        msg.fatigue_score = 0.1
        msg.distraction_score = 0.9 if distracted else 0.1
        msg.eyes_closed = False
        msg.phone_calling = distracted
        msg.smoking = False
        msg.yawning = False
        self.publisher.publish(msg)
        self.tick += 1


def main():
    rclpy.init()
    node = DmsMonitorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
