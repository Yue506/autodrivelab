# 自动驾驶座舱感知域 (DMS Module) - 快速启动指南

本项目是一个基于 Python 的轻量级自动驾驶座舱监控系统（Driver Monitoring System）。系统通过融合 YOLOv8 目标检测与 MediaPipe 3D 面部网格技术，实时分析驾驶员的疲劳（闭眼、打哈欠）与分心（玩手机、抽烟）状态，并输出工业级标准预警信号。

---

## 🛠️ 1. 环境配置 (Environment Setup)

本项目基于 Python 开发，推荐使用 **Python 3.8 或以上版本**。

### 1.1 安装依赖库
建议在 Anaconda 虚拟环境或原生 Python 环境中运行。请打开终端（CMD/PowerShell/Terminal），进入项目根目录，运行以下命令一键安装所有依赖：
```bash
pip install -r requirements.txt