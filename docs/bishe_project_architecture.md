# 毕设项目架构说明文档

> 根据 `framework_chart` 梳理。本项目架构围绕“多源感知数据采集、时空同步、核心计算、决策闭环、人机交互与云端数据沉淀”展开，形成从物理传感器到最终提醒与数据回传的完整系统流程。

---

## 1. 项目总体架构

本项目采用分层式系统架构，共分为五个主要层级：

1. **Layer 1：Physical Sensors，物理传感层**
2. **Layer 2：Data Gateway，数据网关层**
3. **Layer 3：Core Computation，核心计算层**
4. **Layer 4：Decision & Data Loop，决策与数据闭环层**
5. **Layer 5：Execution & Cloud Hub，执行与云端枢纽层**

整体流程可以概括为：

```text
多源传感器采集
    ↓
信号网关进行时间与空间同步
    ↓
BEV感知、舱内状态识别、运动预测等核心模块计算
    ↓
标准化消息总线进行模块间数据发布/订阅
    ↓
中央仲裁器与HMI策略模块完成风险判断和交互决策
    ↓
视觉/语音提醒执行，同时将困难样本上传云端用于后续优化
```

该架构的核心特点是：

- **多源输入**：同时接入车外环视摄像头、舱内摄像头、底盘CAN/IMU等信息；
- **时空对齐**：通过统一网关将不同来源、不同频率的数据对齐；
- **模块解耦**：感知、预测、决策、执行之间通过标准化消息总线通信；
- **闭环优化**：通过影子模式与数据记录器将边缘案例上传云端，为后续模型迭代提供数据基础；
- **安全优先**：中央仲裁器统一处理风险指标、驾驶员状态和环境信息，避免单模块直接触发高风险决策。人类终于想起来让系统别各说各话了，值得表扬。

---

## 2. Layer 1：Physical Sensors 物理传感层

### 2.1 组成模块

物理传感层负责采集车辆外部环境、车内人员状态和车辆自身运动状态，主要包括：

| 传感器模块 | 功能说明 | 输出数据 |
|---|---|---|
| 6× Surround Cameras | 六路环视摄像头，用于采集车辆周围道路、车道线、目标物等环境信息 | 多视角图像帧 |
| Cabin Camera | 舱内摄像头，用于识别驾驶员/乘员状态 | 舱内图像帧 |
| Chassis CAN / IMU | 底盘CAN与惯性测量单元，用于获取车辆速度、横摆角速度、姿态变化等 | 车辆运动状态数据 |

### 2.2 本层作用

该层是整个系统的数据入口，决定后续感知与决策的基础质量。车外摄像头提供环境理解能力，舱内摄像头提供驾驶员状态监测能力，CAN/IMU则提供车辆自身运动状态。

本层不直接进行复杂判断，而是将原始数据统一送入下一层的数据网关，由网关完成同步、标定和格式整理。

---

## 3. Layer 2：Data Gateway 数据网关层

### 3.1 核心模块

#### 1. Signal Gateway & Time-Space Synchronization Hub

该模块是整个系统的数据中枢，负责将来自不同传感器的数据统一接入，并完成时间同步与空间同步。

主要功能包括：

- 接收六路环视摄像头图像；
- 接收舱内摄像头图像；
- 接收底盘CAN与IMU数据；
- 对多源数据进行时间戳对齐；
- 将车外图像帧与车辆自运动信息进行空间对齐；
- 向下游模块分发对齐后的数据。

### 3.2 输出数据

数据网关层主要向下游输出三类数据：

```text
Aligned Frames & Ego-Motion
    → 发送至 BEV Perception 模块

Aligned Cabin Frames
    → 发送至 Cabin DMS/OMS 模块

Ego-State, Speed/Yaw
    → 发送至 Motion & Prediction 模块
```

### 3.3 设计意义

由于不同传感器的采样频率、延迟和坐标系并不一致，如果不进行统一同步，后续模块会出现“视觉看到的是过去，车辆状态却是现在”的问题。听起来像科幻片，其实只是工程系统常见的混乱现场。

因此，数据网关层的核心价值是保证所有后续计算都建立在同一时间与空间基准上。

---

## 4. Layer 3：Core Computation 核心计算层

核心计算层是系统的主要智能处理区域，负责环境感知、舱内状态识别、风险计算与运动预测。

该层包含三个主要模块：

1. **BEV Perception**
2. **Cabin DMS/OMS**
3. **Motion & Prediction**

---

### 4.1 BEV Perception：鸟瞰图环境感知模块

#### 输入

```text
Aligned Frames & Ego-Motion
```

该模块接收经过网关同步后的多路车外图像帧和车辆自运动信息。

#### 功能

BEV感知模块将多摄像头视角转换到统一的鸟瞰图空间，用于识别车辆周围的交通环境。

主要识别内容包括：

- 周围车辆；
- 行人；
- 非机动车；
- 道路边界；
- 车道线；
- 可行驶区域；
- 其他BEV空间目标。

#### 输出

```text
Pub: BEV Targets & Lanes
```

输出的BEV目标与车道线信息会通过标准化消息总线发布，供后续运动预测与中央仲裁模块使用。

---

### 4.2 Cabin DMS/OMS：舱内驾驶员/乘员状态监测模块

#### 输入

```text
Aligned Cabin Frames
```

该模块接收经过同步的舱内摄像头图像。

#### 功能

DMS/OMS模块用于分析驾驶员与乘员状态，其中：

- **DMS**：Driver Monitoring System，驾驶员监测系统；
- **OMS**：Occupant Monitoring System，乘员监测系统。

主要识别内容包括：

- 驾驶员视线方向；
- 注意力状态；
- 疲劳状态；
- 分心行为；
- 乘员位置与状态；
- 舱内异常行为。

#### 输出

```text
Pub: Driver State
```

驾驶员状态会被发布到标准化消息总线，并被中央仲裁器用于综合判断当前风险水平。

---

### 4.3 Motion & Prediction：运动与风险预测模块

#### 输入

```text
Ego-State，Speed/Yaw
Sub: BEV Targets
```

该模块同时接收车辆自身状态与BEV感知结果。

#### 功能

运动预测模块负责根据当前交通环境与车辆运动状态，推断未来短时间内可能发生的风险。

主要功能包括：

- 目标轨迹预测；
- 自车运动趋势估计；
- 交通参与者交互关系分析；
- TTC，Time To Collision，碰撞时间计算；
- 风险等级评估；
- 潜在碰撞或危险场景识别。

#### 输出

```text
Pub: TTC & Risk Metrics
```

该模块输出TTC与风险指标，供中央仲裁器进一步决策。

---

## 5. Standardized Message Bus 标准化消息总线

### 5.1 总线定位

标准化消息总线位于核心计算层与决策层之间，采用类似 Pub/Sub 的通信方式，通过 Protobuf 或 DDS 实现模块解耦。

其作用是让不同模块不需要直接互相调用，而是通过统一消息格式进行数据发布和订阅。

### 5.2 消息类型

系统中主要包含以下消息流：

| 消息方向 | 消息内容 | 发布方 | 订阅方 |
|---|---|---|---|
| Pub | BEV Targets & Lanes | BEV Perception | Motion & Prediction / Central Arbiter |
| Pub | Driver State | Cabin DMS/OMS | Central Arbiter |
| Pub | TTC & Risk Metrics | Motion & Prediction | Central Arbiter |
| Sub | Aggregated Environment & Cabin Data | Message Bus | Central Arbiter |

### 5.3 设计意义

该总线使系统具备良好的扩展性。例如未来替换BEV模型、升级DMS算法或新增传感器时，只需要保持消息协议一致，就不会把整个系统改成一锅工程粥。

---

## 6. Layer 4：Decision & Data Loop 决策与数据闭环层

该层是系统从“感知结果”转向“实际策略”的关键区域，包含两个核心模块：

1. **Central Arbiter & HMI Strategy**
2. **Shadow Mode & Data Logger**

---

### 6.1 Central Arbiter & HMI Strategy：中央仲裁与人机交互策略模块

#### 输入

```text
Sub: Aggregated Environment & Cabin Data
```

该模块订阅来自消息总线的环境信息、舱内状态和风险指标。

#### 功能

中央仲裁器负责综合判断当前风险，并决定是否触发提醒或记录事件。

主要判断依据包括：

- BEV目标与车道线信息；
- 驾驶员状态；
- TTC与风险指标；
- 自车速度、横摆角速度等运动状态；
- 历史缓存帧；
- 场景触发规则。

#### 输出

中央仲裁器主要产生三类输出：

```text
Visual Alert Cmd
    → 发送至 HMI Visual Engine

Audio Alert Cmd
    → 发送至 Acoustic & Voice Alerts

Event: Trigger Edge Case Record
    → 发送至 Shadow Mode & Data Logger
```

### 6.2 决策逻辑示例

中央仲裁器可以采用规则判断、风险评分或轻量策略模型进行综合判断。一个简化逻辑如下：

```text
如果：
    TTC 低于安全阈值
    且 BEV目标处于潜在碰撞区域
    且 驾驶员注意力不足
则：
    触发视觉提醒
    触发语音提醒
    记录该边缘案例
```

### 6.3 Shadow Mode & Data Logger：影子模式与数据记录模块

#### 输入

```text
Event: Trigger Edge Case Record
Bypass: Buffer History Frames
```

该模块接收中央仲裁器触发的边缘案例记录事件，同时可以从网关旁路获取历史缓存帧。

#### 功能

影子模式并不直接干预车辆行为，而是用于记录系统认为有价值的困难场景。

主要功能包括：

- 记录风险场景片段；
- 保存触发事件前后的历史帧；
- 保存感知结果、驾驶员状态、车辆状态和风险指标；
- 形成可回放的数据样本；
- 上传困难样本到云端数据中心。

#### 输出

```text
Upload: Hard Sample Clips
```

这些困难样本会被上传到云端，用于后续模型训练、算法验证和系统迭代。

---

## 7. Layer 5：Execution & Cloud Hub 执行与云端枢纽层

该层负责将决策结果转化为实际人机交互反馈，同时完成数据闭环沉淀。

主要包括三个模块：

1. **HMI Visual Engine**
2. **Acoustic & Voice Alerts**
3. **Cloud Data Center**

---

### 7.1 HMI Visual Engine：视觉提醒引擎

#### 输入

```text
Visual Alert Cmd
```

#### 功能

视觉提醒引擎负责将中央仲裁器的提醒指令转化为可视化界面提示。

可能的视觉提示包括：

- 仪表盘图标提醒；
- 中控屏风险提示；
- HUD抬头显示警示；
- 周围目标高亮；
- 车道偏离或碰撞风险提示。

### 7.2 Acoustic & Voice Alerts：声音与语音提醒模块

#### 输入

```text
Audio Alert Cmd
```

#### 功能

声音提醒模块用于在高风险场景下通过声音方式提醒驾驶员。

可能包括：

- 蜂鸣警报；
- 语音播报；
- 分级声音提示；
- 不同风险等级对应不同音效。

视觉和声音双通道提醒可以提高驾驶员感知概率，毕竟人类注意力经常像后台被强制杀掉的进程。

### 7.3 Cloud Data Center：云端数据中心

#### 输入

```text
Upload: Hard Sample Clips
```

#### 功能

云端数据中心用于接收边缘案例和困难样本，支撑后续算法优化。

主要功能包括：

- 存储困难场景视频片段；
- 存储多源同步数据；
- 支持离线分析；
- 支持模型再训练；
- 支持策略评估；
- 支持系统版本迭代。

---

## 8. 系统详细流程

### 8.1 数据采集阶段

系统首先通过车载传感器采集数据：

```text
6路环视摄像头 → 采集车外环境
舱内摄像头 → 采集驾驶员与乘员状态
CAN/IMU → 采集车辆速度、姿态、横摆角速度等状态
```

这些数据被统一送入信号网关。

---

### 8.2 数据同步阶段

信号网关对输入数据进行处理：

```text
多源数据接入
    ↓
时间戳统一
    ↓
空间坐标对齐
    ↓
缓存历史帧
    ↓
分发给下游计算模块
```

此阶段的重点是保证车外感知、舱内状态和车辆运动信息在同一时间窗口内可用。

---

### 8.3 核心感知阶段

核心计算层并行处理不同类型的数据：

```text
车外同步图像 + 自运动信息
    → BEV Perception
    → 输出 BEV Targets & Lanes

舱内同步图像
    → Cabin DMS/OMS
    → 输出 Driver State

BEV目标 + 自车状态
    → Motion & Prediction
    → 输出 TTC & Risk Metrics
```

通过这种并行结构，系统可以同时获得外部环境风险、驾驶员状态和未来运动趋势。

---

### 8.4 消息汇聚阶段

各核心模块将结果发布到标准化消息总线：

```text
BEV Perception 发布环境目标与车道线
Cabin DMS/OMS 发布驾驶员状态
Motion & Prediction 发布风险指标
```

中央仲裁器从消息总线订阅聚合后的环境与舱内数据。

---

### 8.5 决策仲裁阶段

中央仲裁器综合分析当前状态：

```text
环境目标
+ 车道线
+ 驾驶员状态
+ TTC风险指标
+ 自车运动状态
+ 历史缓存帧
= 综合风险判断
```

根据判断结果，系统会输出以下指令：

```text
低风险：不触发提醒，仅持续监测
中风险：触发视觉提醒
高风险：触发视觉提醒 + 声音提醒
边缘案例：触发数据记录
```

---

### 8.6 执行提醒阶段

如果中央仲裁器判断需要提醒驾驶员，则会向执行层发送指令：

```text
Visual Alert Cmd → HMI Visual Engine
Audio Alert Cmd → Acoustic & Voice Alerts
```

视觉和语音提醒共同构成系统的人机交互输出。

---

### 8.7 数据闭环阶段

当系统检测到边缘案例或高价值困难样本时，会触发数据记录：

```text
中央仲裁器触发事件
    ↓
Shadow Mode & Data Logger 调取历史缓存帧
    ↓
保存多源同步数据与风险结果
    ↓
生成 Hard Sample Clips
    ↓
上传至 Cloud Data Center
    ↓
用于后续模型优化与系统迭代
```

该闭环使系统不仅能完成实时提醒，还能不断积累困难场景数据，为后续改进提供依据。

---

## 9. 项目模块关系图，文字版

```text
Layer 1: Physical Sensors
├── 6× Surround Cameras
├── Cabin Camera
└── Chassis CAN / IMU
        ↓
Layer 2: Data Gateway
└── Signal Gateway & Time-Space Synchronization Hub
        ├── Aligned Frames & Ego-Motion → BEV Perception
        ├── Aligned Cabin Frames → Cabin DMS/OMS
        ├── Ego-State Speed/Yaw → Motion & Prediction
        └── Buffer History Frames → Shadow Mode & Data Logger
        ↓
Layer 3: Core Computation
├── BEV Perception
│   └── Pub: BEV Targets & Lanes
├── Cabin DMS/OMS
│   └── Pub: Driver State
└── Motion & Prediction
    └── Pub: TTC & Risk Metrics
        ↓
Standardized Message Bus
└── Pub/Sub via Protobuf / DDS
        ↓
Layer 4: Decision & Data Loop
├── Central Arbiter & HMI Strategy
│   ├── Visual Alert Cmd
│   ├── Audio Alert Cmd
│   └── Event: Trigger Edge Case Record
└── Shadow Mode & Data Logger
    └── Upload: Hard Sample Clips
        ↓
Layer 5: Execution & Cloud Hub
├── HMI Visual Engine
├── Acoustic & Voice Alerts
└── Cloud Data Center
```

---

## 10. 项目技术路线

本项目的技术路线可以按照以下步骤推进：

### Step 1：传感器数据采集

完成车外环视摄像头、舱内摄像头、CAN/IMU数据的采集设计，明确不同传感器的数据格式、频率和时间戳标准。

### Step 2：多源数据同步

构建信号网关模块，对多源数据进行统一接入、时间同步和空间对齐，为后续计算提供标准化输入。

### Step 3：环境与舱内状态识别

分别建立BEV感知模块和DMS/OMS模块，实现车外环境目标识别与舱内驾驶员状态识别。

### Step 4：运动预测与风险评估

结合BEV目标、自车速度和横摆角速度等信息，计算目标运动趋势、TTC指标和综合风险等级。

### Step 5：消息总线与模块解耦

采用标准化消息总线实现核心模块之间的数据发布与订阅，使系统具备良好的扩展性和维护性。

### Step 6：中央仲裁与HMI策略

设计中央仲裁逻辑，综合环境风险、驾驶员状态和运动预测结果，输出视觉提醒、声音提醒或数据记录事件。

### Step 7：执行反馈与数据闭环

通过HMI视觉引擎和语音提醒模块完成实时反馈，同时通过影子模式记录困难样本并上传云端，形成持续优化闭环。

---

## 11. 项目可实现的核心功能

| 功能类别 | 具体功能 | 对应模块 |
|---|---|---|
| 环境感知 | 识别车辆周围目标、车道线、可行驶区域 | BEV Perception |
| 舱内监测 | 识别驾驶员注意力、疲劳、分心状态 | Cabin DMS/OMS |
| 车辆状态估计 | 获取速度、横摆角速度、姿态变化 | Chassis CAN / IMU |
| 风险预测 | 计算TTC与风险等级 | Motion & Prediction |
| 决策仲裁 | 综合判断是否触发提醒 | Central Arbiter & HMI Strategy |
| 人机交互 | 视觉提醒、声音提醒、语音提示 | HMI Visual Engine / Acoustic Alerts |
| 数据闭环 | 记录困难样本并上传云端 | Shadow Mode & Data Logger / Cloud Data Center |

---

## 12. 毕设论文中可对应的章节安排

如果将该架构写入毕业设计论文，可对应安排如下：

```text
第1章 绪论
    介绍项目背景、研究意义、国内外现状与研究目标

第2章 系统需求分析
    分析驾驶安全、人机交互、多源感知和数据闭环需求

第3章 系统总体架构设计
    重点描述五层架构、模块划分和数据流关系

第4章 核心模块设计
    分别说明数据网关、BEV感知、DMS/OMS、运动预测和中央仲裁模块

第5章 系统流程与交互设计
    说明风险判断流程、视觉提醒流程、声音提醒流程和云端数据闭环流程

第6章 系统测试与结果分析
    设计典型场景测试，验证提醒逻辑、数据同步和边缘案例记录能力

第7章 总结与展望
    总结系统优势、不足和后续优化方向
```

---

## 13. 总结

本项目架构以多源感知为基础，以时空同步网关为数据中枢，以BEV环境感知、舱内状态识别和运动预测为核心计算能力，并通过标准化消息总线连接中央仲裁器，实现从感知、预测、决策到人机交互反馈的完整闭环。

同时，系统引入影子模式和数据记录机制，将边缘案例上传云端，支持后续模型迭代和系统优化。整体架构具备较强的模块化、扩展性和工程落地价值，适合作为智能驾驶辅助、人机交互安全提醒或车载风险预警系统的毕业设计项目框架。
