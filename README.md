# AutoDriveLab

AutoDriveLab 是一个面向毕业设计展示的智能驾驶多源感知与风险融合系统。项目以 ROS2 为通信主干，围绕车外环境感知、驾驶员状态监测、摄像头质量评估、TTC 风险预测、中央仲裁决策和 HMI 可视化，构建从数据输入、算法推理、风险融合到最终告警展示的完整闭环。

本项目的展示重点不是单一模型指标，而是智能驾驶辅助系统的工程化集成能力：在统一消息协议下，将车外目标、相对距离、驾驶员状态、摄像头污染状态等异构输入转化为可解释的风险等级，并通过 Demo 视频、ROS2 节点和中间结果文件进行复现。

## Graduation Demo Goal

毕业设计展示围绕三个问题展开：

1. 智能驾驶系统如何同时接入车外感知、座舱监测和传感器质量信息。
2. 多源风险如何通过统一协议进入中央仲裁模块，形成稳定、可解释的告警结果。
3. 离线数据、模型推理、ROS2 联调和最终可视化如何形成一条可复现的工程链路。

当前版本已经支持三段 nuScenes 场景的慢速标准展示输出，并保留 JSONL 中间结果，方便答辩时逐帧解释每一次风险变化。

## System Architecture

![AutoDriveLab system framework](docs/framework.jpg)

系统按五层组织：底层传感器输入、数据网关与时空同步、核心算法计算、决策与数据闭环、执行与展示层。ROS2 消息和 Demo 级协议桥接贯穿各模块，使感知、预测、IQA、DMS 和 HMI 可以独立开发、统一联调。

## Demo Videos

标准展示视频统一采用 5 FPS 输出，相当于早期 10 FPS 版本的 1/2 速度，更适合答辩演示和逐帧讲解。

| Scene | Demo focus | Video |
|---|---|---|
| `scene-0061` | 城市场景目标跟踪、BEV 避障、TTC 风险提示 | [scene-0061 final_demo.mp4](docs/assets/demo_videos/scene-0061_final_demo.mp4) |
| `scene-0103` | 多目标交互、远近目标风险分层、HMI 状态联动 | [scene-0103 final_demo.mp4](docs/assets/demo_videos/scene-0103_final_demo.mp4) |
| `scene-0553` | 复杂静态障碍物过滤、BEV 合并显示、低速风险展示 | [scene-0553 final_demo.mp4](docs/assets/demo_videos/scene-0553_final_demo.mp4) |

本地生成的完整输出保存在 `demo_outputs/three_scene_slow/`，GitHub 主页展示视频保存在 `docs/assets/demo_videos/`。

## Technical Modules For Defense

| Module | Main packages / tools | Graduation-demo role |
|---|---|---|
| Scene Replay & Data Gateway | `tools/export_nuscenes_demo_cache.py`, `signal_gateway` | 输出对齐后的多相机帧、时间戳、ego state 和场景索引，为后续算法提供统一输入 |
| Object & Distance Perception | `tools/model_inference/`, `demo_pipeline` | 接入目标检测与深度估计结果，形成车外目标、距离和前向风险对象输入 |
| ADAS / TTC Risk Reasoning | `motion_prediction`, `tools/generate_adas_from_gt.py` | 根据目标位置、相对速度和 TTC 计算风险等级，支撑前碰撞预警逻辑 |
| DMS Driver Monitoring | `dms_monitor`, `dms_module` | 表达疲劳、分心、闭眼等驾驶员状态，让系统具备座舱风险输入 |
| IQA Camera Quality Assessment | `iqa_monitor`, `iqa_mobilenetv2_reproduce` | 对 normal / soiling 摄像头质量进行二分类评估，影响感知可信度和融合结果 |
| Central Arbitration & Fusion | `arbitration_module`, `hmi_interface` | 融合 ADAS、DMS、IQA 三类风险，输出统一风险等级、主事件和展示层提示 |
| ROS2 Message & Protocol Bridge | `autodrivelab_msgs`, `arbiter_can`, `demo_bringup` | 定义消息合同、Demo 级 CAN 映射和一键 launch，证明系统具备联调与扩展基础 |
| BEV / HMI Final Rendering | `bev_perception`, `tools/render_final_demo.py` | 将多源状态渲染为六视图、BEV、风险面板和时间线，形成最终答辩展示视频 |

## Reproducible Pipeline

```text
nuScenes scene replay
  -> object / distance perception
  -> pred_adas_objects.jsonl + pred_adas_status.jsonl
  -> DMS status + IQA status
  -> central arbitration / fusion
  -> ROS2 messages + protocol bridge
  -> final_demo.mp4
```

这条链路保留两类输出：一类是面向工程调试的 JSONL / ROS2 消息，另一类是面向答辩展示的最终视频。这样既能展示系统效果，也能解释每个风险等级背后的数据来源和决策依据。

## Repository Layout

```text
autodrivelab/
├── docs/                         # architecture docs, protocol docs and demo assets
│   └── assets/demo_videos/        # GitHub homepage demo videos
├── src/                          # ROS2 workspace packages
│   ├── autodrivelab_msgs/         # shared .msg contracts
│   ├── signal_gateway/            # scene replay and input gateway
│   ├── bev_perception/            # BEV object abstraction
│   ├── dms_monitor/               # driver state monitor
│   ├── iqa_monitor/               # camera quality monitor
│   ├── motion_prediction/         # TTC and risk metrics
│   ├── arbiter_can/               # protocol bridge and CAN abstraction
│   ├── arbitration_module/        # central fusion and decision logic
│   ├── hmi_interface/             # alert / display command sink
│   └── demo_bringup/              # ROS2 launch entrypoints
├── tools/                         # dataset export, inference, rendering and reports
├── iqa_mobilenetv2_reproduce/     # IQA training / evaluation reproduction
├── demo_outputs/                  # local generated videos and JSONL outputs, ignored by git
├── data/                          # local datasets, ignored by git
└── models/                        # local model weights, ignored by git
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

生成三段标准展示视频时，默认输出目录为 `demo_outputs/three_scene_slow/`，主页引用的视频资产位于 `docs/assets/demo_videos/`。

## Data And Models

nuScenes 数据默认放在 `data/nuscenes/`，IQA 数据默认放在 `data/IQA_data/`，模型权重默认放在 `models/`。这些目录包含大文件或本地环境产物，默认不提交到 GitHub。

## Documentation

- [Architecture](docs/bishe_project_architecture.md)
- [ROS2 Demo Notes](README_ros2_demo.md)
- [IQA Integration](README_iqa_integration.md)
- [Protocol Boundary](docs/protocol/protocol_boundary_statement.md)
- [CAN Frame Mapping](docs/protocol/can_frame_mapping.md)
