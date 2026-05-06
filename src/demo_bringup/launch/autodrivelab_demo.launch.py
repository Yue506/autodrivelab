from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package="signal_gateway", executable="mock_gateway_node", name="mock_gateway"),
        Node(package="bev_perception", executable="bev_perception_node", name="bev_perception"),
        Node(package="dms_monitor", executable="dms_monitor_node", name="dms_monitor"),
        Node(package="iqa_monitor", executable="iqa_monitor_node", name="iqa_monitor"),
        Node(package="motion_prediction", executable="motion_prediction_node", name="motion_prediction"),
        Node(package="arbiter_can", executable="arbiter_can_node", name="arbiter_can"),
        Node(package="data_loop", executable="data_loop_node", name="data_loop"),
        Node(package="hmi_interface", executable="hmi_interface_node", name="hmi_interface"),
    ])
