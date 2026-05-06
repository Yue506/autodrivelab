# AutoDriveLab

AutoDriveLab 是一个面向毕业设计的智能驾驶辅助系统 ROS2 框架。项目围绕 nuScenes 数据回放，打通车外 BEV 感知、座舱 DMS、摄像头质量检测 IQA、风险预测、中央仲裁/CAN 处理、HMI 提醒与数据闭环。

## Core Modules

| Module | ROS2 package | Responsibility |
|---|---|---|
| Signal Gateway | `signal_gateway` | nuScenes / mock sensor input, timestamp alignment, ego-state publishing |
| BEV Perception | `bev_perception` | surround-camera BEV targets, lanes and drivable-area abstraction |
| DMS Monitor | `dms_monitor` | cabin driver state, fatigue/distraction event publishing |
| IQA Monitor | `iqa_monitor` | camera blur, brightness, occlusion and quality state publishing |
| Motion Prediction | `motion_prediction` | TTC and risk metric calculation from ego-state + BEV objects |
| Arbiter CAN | `arbiter_can` | central arbitration, HMI command generation, CAN-frame abstraction |
| Data Loop | `data_loop` | shadow mode, edge-case metadata and replay sample manifest logging |
| HMI Interface | `hmi_interface` | visual/audio alert command sink for demo |
| Demo Bringup | `demo_bringup` | launch files and shared parameters |

## Repository Layout

```text
autodrivelab/
├── docs/                         # architecture docs and figures
├── src/                          # ROS2 workspace packages
│   ├── autodrivelab_msgs/         # shared .msg contracts
│   ├── signal_gateway/
│   ├── bev_perception/
│   ├── dms_monitor/
│   ├── iqa_monitor/
│   ├── motion_prediction/
│   ├── arbiter_can/
│   ├── data_loop/
│   ├── hmi_interface/
│   └── demo_bringup/
├── legacy/                       # original prototype code kept for reference
├── data/                         # local datasets, ignored by git
├── models/                       # local weights, ignored by git
└── tools/                        # developer utilities
```

## Quick Start

```bash
# From repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# In a ROS2 environment
colcon build --symlink-install
source install/setup.bash
ros2 launch demo_bringup autodrivelab_demo.launch.py
```

The current framework runs with mock messages first. Replace each placeholder node with the real model pipeline incrementally while keeping the message contracts stable.

## Data

nuScenes data should be placed locally under `data/nuscenes/`, but it is intentionally ignored by git. Keep model weights under `models/`; large files should not be committed to this public repository.

## Architecture

See [docs/bishe_project_architecture.md](docs/bishe_project_architecture.md).
