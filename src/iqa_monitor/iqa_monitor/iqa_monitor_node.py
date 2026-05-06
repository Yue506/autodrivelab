import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import CameraQuality


class IqaMonitorNode(Node):
    def __init__(self):
        super().__init__("iqa_monitor_node")
        self.publisher = self.create_publisher(CameraQuality, "/autodrivelab/camera/front/quality", 10)
        self.subscription = self.create_subscription(CameraQuality, "/autodrivelab/camera/front/quality_seed", self.on_seed, 10)
        self.tick = 0
        self.get_logger().info("IQA monitor placeholder started.")

    def on_seed(self, seed: CameraQuality):
        msg = CameraQuality()
        msg.header = seed.header
        msg.camera_name = seed.camera_name
        degraded = self.tick % 240 > 210
        msg.blur_score = 35.0 if degraded else seed.blur_score
        msg.brightness = seed.brightness
        msg.occlusion_score = 0.65 if degraded else 0.02
        msg.usable = not degraded
        msg.reason = "blur_or_occlusion" if degraded else "ok"
        self.publisher.publish(msg)
        self.tick += 1


def main():
    rclpy.init()
    node = IqaMonitorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
