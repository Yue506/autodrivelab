import math

import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray

from autodrivelab_msgs.msg import BevObjects
from autodrivelab_visualization.asset_registry import get_marker_spec, normalize_class
from autodrivelab_visualization.marker_utils import (
    make_delete_all_marker,
    make_velocity_arrow,
    rgba_to_msg,
    yaw_to_quaternion,
)


class BevMarkerNode(Node):
    def __init__(self):
        super().__init__("bev_marker_node")

        self.declare_parameter("input_topic", "/autodrivelab/bev/objects")
        self.declare_parameter("output_topic", "/autodrivelab/rviz/objects")
        self.declare_parameter("default_frame_id", "base_link")
        self.declare_parameter("object_scale_factor", 0.75)
        self.declare_parameter("show_velocity_arrow", True)
        self.declare_parameter("max_marker_count", 256)
        self.declare_parameter("confidence_alpha", True)

        self.input_topic = self.get_parameter("input_topic").get_parameter_value().string_value
        self.output_topic = self.get_parameter("output_topic").get_parameter_value().string_value
        self.default_frame_id = self.get_parameter("default_frame_id").get_parameter_value().string_value
        self.object_scale_factor = self.get_parameter("object_scale_factor").get_parameter_value().double_value
        self.show_velocity_arrow = self.get_parameter("show_velocity_arrow").get_parameter_value().bool_value
        self.max_marker_count = self.get_parameter("max_marker_count").get_parameter_value().integer_value
        self.confidence_alpha = self.get_parameter("confidence_alpha").get_parameter_value().bool_value

        self.publisher = self.create_publisher(MarkerArray, self.output_topic, 10)
        self.subscription = self.create_subscription(BevObjects, self.input_topic, self.on_bev_objects, 10)
        self.get_logger().info(
            f"BEV Marker node started: {self.input_topic} -> {self.output_topic}, "
            f"scale={self.object_scale_factor:.2f}"
        )

    def on_bev_objects(self, msg: BevObjects):
        frame_id = msg.header.frame_id or self.default_frame_id
        marker_array = MarkerArray()
        clear_marker = make_delete_all_marker(frame_id)
        clear_marker.header.stamp = msg.header.stamp
        marker_array.markers.append(clear_marker)

        scale_factor = max(0.05, float(self.object_scale_factor))
        for index, obj in enumerate(msg.objects[: self.max_marker_count]):
            spec = get_marker_spec(obj.object_class)
            marker = Marker()
            marker.header.stamp = msg.header.stamp
            marker.header.frame_id = frame_id
            marker.ns = f"autodrivelab_{normalize_class(obj.object_class)}"
            marker.id = index
            marker.type = spec.marker_type
            marker.action = Marker.ADD

            marker.pose.position.x = float(obj.x_m)
            marker.pose.position.y = float(obj.y_m)
            marker.pose.position.z = max(0.05, spec.size_xyz[2] * scale_factor * 0.5)
            marker.pose.orientation = yaw_to_quaternion(float(obj.yaw_rad))

            marker.scale.x = max(0.05, spec.size_xyz[0] * scale_factor)
            marker.scale.y = max(0.05, spec.size_xyz[1] * scale_factor)
            marker.scale.z = max(0.05, spec.size_xyz[2] * scale_factor)

            alpha_scale = max(0.2, min(1.0, float(obj.confidence))) if self.confidence_alpha else 1.0
            marker.color = rgba_to_msg(spec.color_rgba, alpha_scale)
            marker_array.markers.append(marker)

            speed = math.hypot(float(obj.vx_mps), float(obj.vy_mps))
            if self.show_velocity_arrow and speed > 0.10:
                arrow = make_velocity_arrow(frame_id, self.max_marker_count + index, obj, marker.color)
                arrow.header.stamp = msg.header.stamp
                marker_array.markers.append(arrow)

        self.publisher.publish(marker_array)


def main(args=None):
    rclpy.init(args=args)
    node = BevMarkerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
