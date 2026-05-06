# DMS 座舱感知域 (DMS Module) - 代码目录结构与说明

本项目采用了高内聚、低耦合的三段式架构，将配置、算法核心与可视化完全分离，符合工业级自动驾驶感知模块的开发规范。

## 📂 根目录树状图
```text
DMS_Project/
├── config.yaml             # 全局配置文件 (参数、阈值、路径)
├── core_perception.py      # 核心感知算法域 (YOLOv8 + MediaPipe)
├── visualizer.py           # 可视化与 UI 渲染模块 (Dashboard 渲染)
├── main.py                 # 系统主入口引擎 (生命周期管理)
├── yolov8n.pt              # YOLOv8 目标检测权重模型
├── requirements.txt        # Python 环境依赖清单
└── logs/                   # 日志与数据输出目录
    └── dms_report.csv      # 实时生成的驾驶员状态时序报表