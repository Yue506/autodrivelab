# ROS2 Topic Demo

This demo upgrades the offline JSONL nuScenes MVP into a ROS2 topic flow.

## Flow

- `/nuscenes/frame`: lightweight frame metadata and camera image paths.
- `/nuscenes/gt_objects`: nuScenes GT boxes in ego/BEV coordinates.
- `/adas/objects`: GT-derived pseudo perception objects.
- `/adas/status`: distance-threshold ADAS/TTC risk state.
- `/dms/status`: scripted DMS state because nuScenes has no cabin video.
- `/iqa/status`: scripted or custom IQA test result adapter.
- `/fusion/risk_status`: arbitration output from ADAS, DMS, and IQA.

IQA 模块使用自建测试数据进行独立 test，不使用 nuScenes 图像。ROS2 Demo 中 `/iqa/status` 由 scripted timeline 或自建测试集 IQA 结果 adapter 发布。

## Run

```bash
source /opt/ros/humble/setup.bash
colcon build --packages-select autodrivelab_msgs arbitration_module demo_pipeline
source install/setup.bash
ros2 launch demo_pipeline demo_ros2.launch.py \
  cache_dir:=demo_outputs/scene_000/demo_cache \
  scene_dir:=demo_outputs/scene_000 \
  fps:=10 \
  total_frames:=39 \
  iqa_mode:=scripted
```

For IQA test-result mode:

```bash
ros2 launch demo_pipeline demo_ros2.launch.py \
  cache_dir:=demo_outputs/scene_000/demo_cache \
  scene_dir:=demo_outputs/scene_000 \
  fps:=10 \
  total_frames:=39 \
  iqa_mode:=offline_test_result \
  iqa_result:=demo_outputs/scene_000/iqa_status_from_test.jsonl
```

Output video: `demo_outputs/scene_000/demo_ros2.mp4`.
