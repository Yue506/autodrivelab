import rclpy
from rclpy.node import Node

from autodrivelab_msgs.msg import DmsStatus, NuscenesFrame

from .common import default_dms_timeline, timeline_segment


class DmsScriptedNode(Node):
    def __init__(self):
        super().__init__("dms_scripted_node")
        self.declare_parameter("total_frames", 80)
        self.status_pub = self.create_publisher(DmsStatus, "/dms/status", 10)
        self.create_subscription(NuscenesFrame, "/nuscenes/frame", self.on_frame, 10)
        self.timeline = default_dms_timeline()

    def on_frame(self, frame: NuscenesFrame):
        seg = timeline_segment(frame.frame_index, int(self.get_parameter("total_frames").value), self.timeline)
        level = int(seg["danger_level"])
        msg = DmsStatus(
            stamp=frame.stamp,
            frame_id="dms_camera",
            frame_index=frame.frame_index,
            danger_level=level,
            event_type=seg["event_type"],
            event_description=seg["event_description"],
            fatigue_level=level if level > 0 else 0,
            confidence=1.0,
            fatigue_confidence=1.0 if level > 0 else 0.0,
            valid=True,
        )
        msg.is_fatigue = level > 0
        msg.is_yawning = seg["event_type"] == "DRIVER_YAWNING"
        self.status_pub.publish(msg)


def main():
    rclpy.init()
    node = DmsScriptedNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
