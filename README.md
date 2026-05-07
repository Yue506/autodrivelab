# AutoDriveLab

AutoDriveLab 是一个面向毕业设计与 Demo 展示的智能驾驶多源感知融合系统。项目以 ROS2 为主干，围绕 nuScenes 离线回放、车外目标感知、深度/距离估计、TTC 风险计算、DMS 驾驶员状态、IQA 摄像头质量评估、仲裁决策与 HMI 可视化，形成可复现、可演示、可继续替换真实模型的端到端链路。

当前版本重点收敛在稳定可跑的离线 Demo：输入侧支持 nuScenes mini 场景回放与模型推理结果接入，算法侧支持 ADAS 风险、DMS、IQA、多源仲裁和协议映射，输出侧生成 JSONL 中间结果、ROS2 消息链路和最终展示视频。

## Demo Videos

标准展示视频统一采用 5 FPS 输出，相当于早期 10 FPS 版本的 1/2 速度，更适合答辩和逐帧讲解。

| Scene | Demo focus | Video |
|---|---|---|
| `scene-0061` | 城市场景目标跟踪、BEV 避障、TTC 风险提示 | [final_demo.mp4](docs/assets/demo_videos/scene-0061_final_demo.mp4) |
| `scene-0103` | 多目标交互、远近目标风险分层、HMI 状态联动 | [final_demo.mp4](docs/assets/demo_videos/scene-0103_final_demo.mp4) |
| `scene-0553` | 复杂静态障碍物过滤、BEV 合并显示、低速风险展示 | [final_demo.mp4](docs/assets/demo_videos/scene-0553_final_demo.mp4) |

本地生成的完整输出保存在 `demo_outputs/three_scene_slow/`，GitHub 主页展示视频保存在 `docs/assets/demo_videos/`。

## Technical Modules

| Module | Main packages / tools | Responsibility |
|---|---|---|
| Offline Scene Replay | `tools/export_nuscenes_demo_cache.py`, `signal_gateway` | 读取 nuScenes mini 场景，导出按时间戳对齐的图像、ego state 和回放索引 |
| Model Perception Pipeline | `tools/model_inference/`, `demo_pipeline` | 接入 YOLO 目标检测与 Depth Anything 深度估计，生成 `pred_adas_objects.jsonl` 与 `pred_adas_status.jsonl` |
| ADAS / TTC Risk | `motion_prediction`, `tools/generate_adas_from_gt.py` | 根据目标距离、相对速度和 ego state 计算 TTC、碰撞等级和风险标签 |
| BEV Rendering & Fusion | `bev_perception`, `tools/render_final_demo.py` | 统一 BEV 坐标、目标合并、静态障碍物降噪、ego 周边留白和最终画面渲染 |
| DMS Driver State | `dms_monitor`, `dms_module` | 输出疲劳、分心、闭眼等驾驶员状态，并接入仲裁链路 |
| IQA Camera Quality | `iqa_monitor`, `iqa_mobilenetv2_reproduce` | 基于 MobileNetV2 的 normal / soiling 二分类质量检测，支持真实测试结果接入 |
| Arbitration & HMI | `arbitration_module`, `hmi_interface` | 融合 ADAS、DMS、IQA 状态，生成统一告警、风险事件和展示层提示 |
| ROS2 & Protocol Bridge | `autodrivelab_msgs`, `arbiter_can`, `demo_bringup` | 定义 ROS2 消息合同、Demo 级 CAN 映射和一键联调 launch 入口 |

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

## Data And Models

nuScenes 数据默认放在 `data/nuscenes/`，IQA 数据默认放在 `data/IQA_data/`，模型权重默认放在 `models/`。这些目录包含大文件或本地环境产物，默认不提交到 GitHub。

## Documentation

- [Architecture](docs/bishe_project_architecture.md)
- [ROS2 Demo Notes](README_ros2_demo.md)
- [IQA Integration](README_iqa_integration.md)
- [Protocol Boundary](docs/protocol/protocol_boundary_statement.md)
- [CAN Frame Mapping](docs/protocol/can_frame_mapping.md)
