from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    input_topic = LaunchConfiguration("input_topic")
    output_topic = LaunchConfiguration("output_topic")
    frame_id = LaunchConfiguration("frame_id")
    object_scale_factor = LaunchConfiguration("object_scale_factor")
    show_velocity_arrow = LaunchConfiguration("show_velocity_arrow")
    use_rviz = LaunchConfiguration("use_rviz")
    rviz_config = PathJoinSubstitution([
        FindPackageShare("autodrivelab_visualization"),
        "rviz",
        "autodrivelab_3d_markers.rviz",
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            "input_topic",
            default_value="/autodrivelab/bev/objects",
            description="Input topic of autodrivelab_msgs/msg/BevObjects.",
        ),
        DeclareLaunchArgument(
            "output_topic",
            default_value="/autodrivelab/rviz/objects",
            description="Output topic of visualization_msgs/msg/MarkerArray.",
        ),
        DeclareLaunchArgument(
            "frame_id",
            default_value="base_link",
            description="Fallback RViz frame_id when input header.frame_id is empty.",
        ),
        DeclareLaunchArgument(
            "object_scale_factor",
            default_value="0.75",
            description="Scale factor used only for display geometry size.",
        ),
        DeclareLaunchArgument(
            "show_velocity_arrow",
            default_value="true",
            description="Whether to draw velocity arrows.",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="false",
            description="Launch RViz2 with the package config.",
        ),
        Node(
            package="autodrivelab_visualization",
            executable="bev_marker_node",
            name="bev_marker_node",
            output="screen",
            parameters=[{
                "input_topic": input_topic,
                "output_topic": output_topic,
                "default_frame_id": frame_id,
                "object_scale_factor": object_scale_factor,
                "show_velocity_arrow": show_velocity_arrow,
            }],
        ),
        ExecuteProcess(
            cmd=["rviz2", "-d", rviz_config],
            condition=IfCondition(use_rviz),
            output="screen",
        ),
    ])
