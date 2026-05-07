# Demo CAN Frame Mapping

## 协议定位

本协议为 Demo 级融合风险输出编码协议，用于将 `FusionRiskStatus` 映射为抽象 `CanFrame`，供 HMI 和系统展示使用。

当前不直接对接真实车端 CAN 驱动，不包含 DBC、UDS、DoIP、SOME-IP、Serial 或 UDP 实现。

## CAN 帧定义

- CAN ID: `0x321`
- DLC: `8`
- `semantic_name`: `FUSION_RISK_STATUS`
- `is_extended`: `false`

| Byte | 字段 | 说明 |
|---:|---|---|
| 0 | `unified_risk_level` | 统一风险等级，范围 0-4 |
| 1 | `source_valid_flags` | bit0 ADAS, bit1 DMS, bit2 IQA, bit3 perception degraded |
| 2 | `primary_event_code` | 主事件编码，未知事件为 255 |
| 3 | `iqa_level` | IQA 风险等级 |
| 4 | `soiled_camera_count` | 污染摄像头数量 |
| 5 | `risk_source_code` | 主风险来源编码 |
| 6 | `rolling_counter` | 循环计数 |
| 7 | `checksum` | Demo 级简单校验 |

## 事件编码

| Event | Code |
|---|---:|
| `SAFE` | 0 |
| `FCW_WARNING` | 1 |
| `FCW_EMERGENCY` | 2 |
| `AEB_TRIGGER` | 3 |
| `BSD_ACTIVE` | 4 |
| `DRIVER_YAWNING` | 10 |
| `DRIVER_EYES_CLOSED` | 11 |
| `DRIVER_CALLING` | 12 |
| `DRIVER_SMOKING` | 13 |
| `CAMERA_SOILING` | 20 |
| `PERCEPTION_DEGRADED` | 21 |
| `SENSOR_INVALID` | 30 |
| unknown | 255 |

## 风险来源编码

| Source | Code |
|---|---:|
| `FUSION` | 0 |
| `ADAS` | 1 |
| `DMS` | 2 |
| `IQA` | 3 |
| unknown | 255 |

## Checksum

当前使用 Demo 级简单 checksum:

```text
checksum = sum(data[0:7]) & 0xFF
```

该 checksum 只用于 Demo 输出一致性检查，不是真实车规 CAN 通信校验。

## 扩展说明

真实车端接入时，可进一步增加：

1. DBC 信号定义；
2. SocketCAN 或车端 CAN driver；
3. UDS/DoIP 诊断协议；
4. 心跳与重连状态机；
5. 通信故障注入测试。

当前毕设 Demo 阶段不实现这些内容。
