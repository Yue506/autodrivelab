import math

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import CameraQuality, EgoState


class MockGatewayNode(Node):
    def __init__(self):
        super().__init__("mock_gateway_node")
        self.declare_parameter("rate_hz", 10.0)
        self.ego_pub = self.create_publisher(EgoState, "/autodrivelab/ego_state", 10)
        self.camera_pub = self.create_publisher(CameraQuality, "/autodrivelab/camera/front/quality_seed", 10)
        self.tick = 0
        rate_hz = float(self.get_parameter("rate_hz").value)
        self.create_timer(1.0 / max(rate_hz, 1.0), self.publish_mock_inputs)
        self.get_logger().info("Mock signal gateway started.")

    def publish_mock_inputs(self):
        now = self.get_clock().now().to_msg()
        phase = self.tick / 20.0

        ego = EgoState()
        ego.header.stamp = now
        ego.header.frame_id = "base_link"
        ego.speed_mps = 8.0 + 2.0 * math.sin(phase)
        ego.yaw_rate_radps = 0.03 * math.sin(phase / 2.0)
        ego.acceleration_mps2 = 0.2 * math.cos(phase)
        ego.steering_angle_rad = 0.04 * math.sin(phase / 3.0)
        ego.turn_signal = 1 if self.tick % 160 > 120 else 0
        self.ego_pub.publish(ego)

        quality_seed = CameraQuality()
        quality_seed.header.stamp = now
        quality_seed.header.frame_id = "camera_front"
        quality_seed.camera_name = "front"
        quality_seed.blur_score = 180.0
        quality_seed.brightness = 120.0
        quality_seed.occlusion_score = 0.0
        quality_seed.usable = True
        quality_seed.reason = "mock_seed"
        self.camera_pub.publish(quality_seed)
        self.tick += 1


def main():
    rclpy.init()
    node = MockGatewayNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
