from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    output_topic = LaunchConfiguration("output_topic")
    object_scale_factor = LaunchConfiguration("object_scale_factor")

    demo_launch = PathJoinSubstitution([
        FindPackageShare("demo_bringup"),
        "launch",
        "autodrivelab_demo.launch.py",
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            "output_topic",
            default_value="/autodrivelab/rviz/objects",
            description="Output topic for RViz2 MarkerArray.",
        ),
        DeclareLaunchArgument(
            "object_scale_factor",
            default_value="0.75",
            description="Display-only scale factor for RViz markers.",
        ),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(demo_launch)),
        Node(
            package="autodrivelab_visualization",
            executable="bev_marker_node",
            name="bev_marker_node",
            output="screen",
            parameters=[{
                "input_topic": "/autodrivelab/bev/objects",
                "output_topic": output_topic,
                "default_frame_id": "base_link",
                "object_scale_factor": object_scale_factor,
                "show_velocity_arrow": True,
            }],
        ),
    ])
