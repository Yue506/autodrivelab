# ROS2 Topic Demo

This demo upgrades the offline JSONL nuScenes MVP into a ROS2 topic flow.

## Flow

- `/nuscenes/frame`: lightweight frame metadata and camera image paths.
- `/nuscenes/gt_objects`: nuScenes GT boxes in ego/BEV coordinates.
- `/adas/objects`: GT-derived pseudo perception objects.
- `/adas/status`: distance-threshold ADAS/TTC risk state.
- `/autodrivelab/ego_state` + `/autodrivelab/bev/objects` -> `/autodrivelab/risk_metrics`: EKF-smoothed CTRV / CA motion prediction path for demo-level TTC, BSD, FCW, and lane-change risk events.
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
  fps:=5 \
  total_frames:=39 \
  iqa_mode:=scripted
```

For IQA test-result mode:

```bash
ros2 launch demo_pipeline demo_ros2.launch.py \
  cache_dir:=demo_outputs/scene_000/demo_cache \
  scene_dir:=demo_outputs/scene_000 \
  fps:=5 \
  total_frames:=39 \
  iqa_mode:=offline_test_result \
  iqa_result:=demo_outputs/scene_000/iqa_status_from_test.jsonl
```

Output video: `demo_outputs/scene_000/demo_ros2.mp4`.

## EKF + CTRV Motion Prediction

Tingfeng Wang optimised the `motion_prediction` module with EKF-smoothed target states and short-horizon CTRV / CA trajectory prediction. The node keeps the existing ROS2 interface unchanged:

```text
/autodrivelab/ego_state + /autodrivelab/bev/objects
  -> motion_prediction
  -> /autodrivelab/risk_metrics
```

`/autodrivelab/risk_metrics` publishes `min_ttc_s`, `risk_level`, and `active_events`. Current event names include `BSD_ACTIVE`, `FCW_POTENTIAL`, `FCW_EMERGENCY`, and `LCA_INTERVENTION`. This is a graduation-demo risk reasoning module for downstream arbitration and HMI visualization, not production AEB or real vehicle control.

Quick core check:

```bash
python3 tools/test_motion_prediction_core.py
```

Build check:

```bash
colcon build --symlink-install --packages-select autodrivelab_msgs motion_prediction
```

## Demo 级系统输出桥接

当前系统保留 `/adas|dms|iqa|fusion/*` 作为 Demo 主数据流。为对接 `/autodrivelab/*` 系统命名空间，新增可选 bridge 节点：

```text
/fusion/risk_status
    -> fusion_to_autodrivelab_bridge_node
    -> /autodrivelab/fusion/risk_status
    -> /autodrivelab/can/tx
```

该 bridge 为旁路增强，不影响原 Demo 主链路。默认不开启：

```bash
ros2 launch demo_pipeline demo_ros2.launch.py enable_bridge:=false
```

开启 bridge：

```bash
ros2 launch demo_pipeline demo_ros2.launch.py enable_bridge:=true
```

开启后可检查：

```bash
ros2 topic echo /autodrivelab/fusion/risk_status
ros2 topic echo /autodrivelab/can/tx
```

`/autodrivelab/can/tx` 使用 Demo 级 `FusionRiskStatus -> CanFrame` 编码，协议说明见 `docs/protocol/can_frame_mapping.md`。协议边界说明见 `docs/protocol/protocol_boundary_statement.md`。
