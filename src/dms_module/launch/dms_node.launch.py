from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config_path = PathJoinSubstitution([FindPackageShare("dms_module"), "config", "dms_config.yaml"])
    return LaunchDescription([
        Node(
            package="dms_module",
            executable="dms_node",
            name="dms_node",
            output="screen",
            parameters=[{"config_path": config_path}],
        )
    ])
