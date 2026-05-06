import json
from pathlib import Path

import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import AlertCommand


class DataLoopNode(Node):
    def __init__(self):
        super().__init__("data_loop_node")
        self.declare_parameter("edge_case_dir", "data/edge_cases")
        self.output_dir = Path(str(self.get_parameter("edge_case_dir").value))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.subscription = self.create_subscription(AlertCommand, "/autodrivelab/alert_cmd", self.on_alert, 10)
        self.counter = 0
        self.get_logger().info(f"Data loop node writing manifests to {self.output_dir}")

    def on_alert(self, alert: AlertCommand):
        if not alert.record_edge_case:
            return
        self.counter += 1
        manifest = {
            "index": self.counter,
            "risk_level": int(alert.risk_level),
            "message": alert.message,
            "stamp": {"sec": alert.header.stamp.sec, "nanosec": alert.header.stamp.nanosec},
            "status": "metadata_only_placeholder",
        }
        path = self.output_dir / f"edge_case_{self.counter:05d}.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.get_logger().info(f"Recorded edge-case manifest: {path}")


def main():
    rclpy.init()
    node = DataLoopNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
