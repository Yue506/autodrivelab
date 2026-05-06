# ADAS 五合一综合预警与仲裁系统 (Graduation Project)

## 1. 项目简介
本项目是高级驾驶辅助系统 (ADAS) 的“核心决策大脑”。模块接收来自感知层（或 nuScenes 真实数据集）的目标数据以及底盘 CAN 总线的自车运动学数据。
通过融合**卡尔曼滤波 (KF)**、**阿克曼转向几何**以及 **CTRV/CA 混合轨迹预测模型**，系统能够在复杂的动态环境中精准计算 TTC (碰撞时间)，并执行 5 合 1（BSD、LCA、FCW 等）的全局风险仲裁，最终输出标准化的高优先级的预警指令。



## 2. 文件目录架构
ADAS_Project/
├── data/                       # 依赖数据目录
│   └── nuscenes/               # 请确保包含 v1.0-mini 和 can_bus 扩展包
├── src/                        # 源代码目录
│   ├── adas_pipeline.py        # [核心] 纯算法层：卡尔曼滤波、轨迹预测与仲裁逻辑
│   ├── visualize_adas.py       # [表现层] 结合 OpenCV 的实车视频流实时测试与 HUD 渲染
│   └── play_video.py           # [工具] 数据集纯视频回放查看器
└── README.md                   # 本说明文档

## 3. 核心输入与输出定义 (Interfaces)
本模块作为纯粹的决策中心，通过高度标准化的字典/Protobuf 格式与上下游模块进行交互。

3.1 模块输入 (Input)
调度程序在调用 adas.process_frame(ego_state, target_states) 时，需传入以下参数：

ego_state (自车状态): 真实环境下通过 CAN 总线解析获取。
speed: 纵向真实车速 (m/s)
steering_angle: 方向盘真实转角 (rad)
turn_signal: 转向灯状态 (1为左，-1为右，0为无)

target_states (目标车列表): 经过坐标系转换和卡尔曼滤波平滑后的相对数据。
x, y: 以自车为原点的相对坐标 (m)
speed, heading: 目标的绝对速度与相对航向角
acceleration, yaw_rate: 推导出的纵向加速度与横摆角速度

3.2 模块输出 (Output)
仲裁系统遍历所有目标后，输出当前帧的全局最高风险，可直接序列化发送给 UI 渲染层。
{
  "global_risk_level": 3, 
  "active_events": [
    "BSD_Active", 
    "FCW_Warning_Level_3"
  ]
}

## 4. 风险等级与事件判定逻辑 (Arbitration Logic)系统采用严格的物理时空重叠计算，有效过滤误报，并分为 4 个递增的优先级等级。
Level 1 & 2: 空间预警层 (静默与盲区)
Level 1 (SAFE - 安全): 默认状态，周围目标距离较远，无轨迹交汇趋势。
Level 2 (ATTENTION - 注意) -> 触发事件 [BSD_Active]:判定条件: 目标车辆的三维坐标落入自车侧后方（后15m至前2m，侧向1.5m至4.5m）的物理盲区多边形内。仅作后视镜亮灯提示，无声音警报。

Level 3: 空间+时间 双重预警层 (潜在碰撞)
Level 3 (WARNING - 警告) -> 触发事件 [FCW_Warning_Level_3]:判定条件: 基于阿克曼与 CTRV 模型预测自车与目标车未来 3-5 秒的行驶轨迹，若发生空间轨迹重叠，并且当前高频计算的碰撞时间 3.0s <= TTC <= 5.0s。提醒驾驶员准备减速。

Level 4: 紧急极限干预层 (致命风险)本等级具有最高仲裁权，UI 层接收到该指令应立即触发红色闪烁及蜂鸣器，并对接 AEB (自动紧急制动) 模块。
触发事件 A [FCW_Emergency_Level_4] (追尾/正面碰撞):判定条件: 存在轨迹重叠，且 TTC < 3.0s。
触发事件 B [LCA_Emergency_Intervention] (变道紧急干预):判定条件: 自车正在打转向灯试图变道，目标车在对应侧，预测发生轨迹冲突，且 TTC < 5.0s (主动变道危险阈值更严苛)。

##  5. 遇到的难题与解决方式 
难题 1：传感器微分噪声导致 TTC 误报频繁。
解决方式： 引入了一维轻量级卡尔曼滤波器对原始坐标和速度进行平滑，稳健地推导出了高阶运动学参数（加速度/角速度），大幅提升了 CTRV 模型的预测精度。

难题 2：转弯场景下，单纯依靠距离判定会导致前方假目标碰撞报警。
解决方式： 放弃 CV 匀速直线模型，全面接入真实底盘 CAN 总线的 steeranglefeedback (方向盘转角) 数据，结合阿克曼几何预测自车真实转弯弧线，成功过滤了误报。

##  6. 运行与环境依赖
安装依赖：pip install numpy pyquaternion nuscenes-devkit opencv-python
数据准备：确保 data/nuscenes/ 下包含完整的 v1.0-mini 和 can_bus 文件夹。
修改数据安装的正确位置 将这行代码路径改为自己安装的路径DATAROOT = r'E:\vscode_projects\ADAS\data\nuscenes'
执行测试：在终端运行 python src/visualize_adas.py。

如何更换测试录像 (如从 0061 切换到 0757)
系统内置了 nuScenes v1.0-mini 数据集进行仿真。若需测试不同路况（如拥堵、路口、雨天），只需修改代码中的一处变量。
找到SCENE_NAME = 'scene-0061'  # <--- 将 'scene-0061' 改为 'scene-0757'


