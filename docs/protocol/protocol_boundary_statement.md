# 协议边界说明

本项目当前阶段以 nuScenes 回放、感知状态生成、多源仲裁和 HMI/FSD-style 可视化为核心目标。

当前通信主链路采用 ROS2 Topic，主要用于模块间数据流转。

项目中提供 `CanFrame` 抽象与 `FusionRiskStatus` 到 `CanFrame` 的编码，仅作为 Demo 级协议适配层，用于展示融合风险结果可被进一步映射到车端通信接口。

当前不实现真实车载底层通信协议栈，包括但不限于：

- 真实 CAN 驱动；
- DBC 文件解析；
- UDS；
- DoIP；
- SOME-IP；
- Serial/UART；
- TCP/UDP Socket 网关；
- 车端重连与 heartbeat 状态机。

上述内容作为后续工程化扩展方向。
