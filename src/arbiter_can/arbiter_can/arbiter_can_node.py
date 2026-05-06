import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import AlertCommand, CameraQuality, CanFrame, DriverState, RiskMetrics


class ArbiterCanNode(Node):
    def __init__(self):
        super().__init__("arbiter_can_node")
        self.driver = None
        self.camera_quality = None
        self.alert_pub = self.create_publisher(AlertCommand, "/autodrivelab/alert_cmd", 10)
        self.can_pub = self.create_publisher(CanFrame, "/autodrivelab/can/tx", 10)
        self.risk_sub = self.create_subscription(RiskMetrics, "/autodrivelab/risk_metrics", self.on_risk, 10)
        self.driver_sub = self.create_subscription(DriverState, "/autodrivelab/cabin/driver_state", self.on_driver, 10)
        self.iqa_sub = self.create_subscription(CameraQuality, "/autodrivelab/camera/front/quality", self.on_quality, 10)
        self.get_logger().info("Central arbiter/CAN node started.")

    def on_driver(self, msg: DriverState):
        self.driver = msg

    def on_quality(self, msg: CameraQuality):
        self.camera_quality = msg

    def on_risk(self, risk: RiskMetrics):
        driver_level = self.driver.danger_level if self.driver else 0
        quality_penalty = self.camera_quality is not None and not self.camera_quality.usable
        risk_level = max(int(risk.risk_level), int(driver_level))
        if quality_penalty:
            risk_level = max(risk_level, 2)

        alert = AlertCommand()
        alert.header = risk.header
        alert.risk_level = risk_level
        alert.visual_alert = risk_level >= 2
        alert.audio_alert = risk_level >= 3
        alert.record_edge_case = risk_level >= 3 or quality_penalty
        alert.message = self._build_message(risk, driver_level, quality_penalty)
        self.alert_pub.publish(alert)
        self.can_pub.publish(self._encode_can(alert))

    def _build_message(self, risk: RiskMetrics, driver_level: int, quality_penalty: bool) -> str:
        parts = list(risk.active_events)
        if driver_level >= 3:
            parts.append("DRIVER_ATTENTION_REQUIRED")
        if quality_penalty:
            parts.append("CAMERA_QUALITY_DEGRADED")
        return ",".join(parts) if parts else "NORMAL"

    def _encode_can(self, alert: AlertCommand) -> CanFrame:
        frame = CanFrame()
        frame.header = alert.header
        frame.can_id = 0x321
        frame.semantic_name = "ADAS_ALERT_COMMAND"
        frame.is_extended = False
        frame.data = [
            int(alert.risk_level) & 0xFF,
            int(alert.visual_alert),
            int(alert.audio_alert),
            int(alert.record_edge_case),
            0,
            0,
            0,
            0,
        ]
        return frame


def main():
    rclpy.init()
    node = ArbiterCanNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
