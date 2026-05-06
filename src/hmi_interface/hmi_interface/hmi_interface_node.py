import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import AlertCommand, CanFrame


class HmiInterfaceNode(Node):
    def __init__(self):
        super().__init__("hmi_interface_node")
        self.alert_sub = self.create_subscription(AlertCommand, "/autodrivelab/alert_cmd", self.on_alert, 10)
        self.can_sub = self.create_subscription(CanFrame, "/autodrivelab/can/tx", self.on_can, 10)
        self.last_can_id = None
        self.get_logger().info("HMI interface node started.")

    def on_can(self, frame: CanFrame):
        self.last_can_id = frame.can_id

    def on_alert(self, alert: AlertCommand):
        if alert.risk_level <= 1:
            return
        self.get_logger().warn(
            f"HMI alert risk={alert.risk_level} visual={alert.visual_alert} "
            f"audio={alert.audio_alert} record={alert.record_edge_case} msg={alert.message}"
        )


def main():
    rclpy.init()
    node = HmiInterfaceNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
