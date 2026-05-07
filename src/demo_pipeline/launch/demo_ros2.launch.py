from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    cache_dir = LaunchConfiguration("cache_dir")
    scene_dir = LaunchConfiguration("scene_dir")
    fps = LaunchConfiguration("fps")
    total_frames = LaunchConfiguration("total_frames")
    iqa_mode = LaunchConfiguration("iqa_mode")
    iqa_result = LaunchConfiguration("iqa_result")
    return LaunchDescription([
        DeclareLaunchArgument("cache_dir", default_value="demo_outputs/scene_000/demo_cache"),
        DeclareLaunchArgument("scene_dir", default_value="demo_outputs/scene_000"),
        DeclareLaunchArgument("fps", default_value="10"),
        DeclareLaunchArgument("total_frames", default_value="39"),
        DeclareLaunchArgument("iqa_mode", default_value="scripted"),
        DeclareLaunchArgument("iqa_result", default_value=""),
        Node(package="demo_pipeline", executable="nuscenes_replay_node", parameters=[{"cache_dir": cache_dir, "fps": fps, "loop": False}]),
        Node(package="demo_pipeline", executable="adas_gt_adapter_node"),
        Node(package="demo_pipeline", executable="dms_scripted_node", parameters=[{"total_frames": total_frames}]),
        Node(package="demo_pipeline", executable="iqa_adapter_node", parameters=[{"mode": iqa_mode, "iqa_result": iqa_result, "total_frames": total_frames}]),
        Node(package="arbitration_module", executable="arbitration_node"),
        Node(package="demo_pipeline", executable="render_recorder_node", parameters=[{"cache_dir": cache_dir, "scene_dir": scene_dir, "fps": fps, "expected_frames": total_frames, "out": [scene_dir, "/demo_ros2.mp4"]}]),
    ])
