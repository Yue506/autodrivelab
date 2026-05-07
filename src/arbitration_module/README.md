# Arbitration Module

ROS2 fusion node for ADAS/TTC, DMS, and IQA risk arbitration.

## Topics

| Direction | Topic | Type |
|---|---|---|
| Subscribe | `/adas/status` | `autodrivelab_msgs/msg/AdasStatus` |
| Subscribe | `/dms/status` | `autodrivelab_msgs/msg/DmsStatus` |
| Subscribe | `/iqa/status` | `autodrivelab_msgs/msg/IqaStatus` |
| Publish | `/fusion/risk_status` | `autodrivelab_msgs/msg/FusionRiskStatus` |

## Run

```bash
colcon build --packages-select autodrivelab_msgs dms_module arbitration_module
source install/setup.bash
ros2 launch arbitration_module arbitration_node.launch.py
ros2 topic echo /fusion/risk_status
```

## Tests

```bash
python -m unittest discover src/arbitration_module/test
```

Risk matrix implementation: `arbitration_module/risk_matrix.py`.
IQA gate implementation: `arbitration_module/iqa_gate.py`.
Time synchronization buffer: `arbitration_module/time_sync_buffer.py`.
