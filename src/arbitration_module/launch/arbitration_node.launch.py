from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config_path = PathJoinSubstitution([FindPackageShare("arbitration_module"), "config", "arbitration_config.yaml"])
    return LaunchDescription([
        Node(
            package="arbitration_module",
            executable="arbitration_node",
            name="arbitration_node",
            output="screen",
            parameters=[{"config_path": config_path}],
        )
    ])
