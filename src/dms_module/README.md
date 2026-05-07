# DMS Module

ROS2 driver monitoring node for structured DMS status publishing.

## Topics

| Direction | Topic | Type |
|---|---|---|
| Subscribe | `/camera/dms/image_raw` | `sensor_msgs/msg/Image` |
| Publish | `/dms/status` | `autodrivelab_msgs/msg/DmsStatus` |
| Publish | `/dms/vis_image` | `sensor_msgs/msg/Image` |

## Run

```bash
colcon build --packages-select autodrivelab_msgs dms_module
source install/setup.bash
ros2 launch dms_module dms_node.launch.py
ros2 topic echo /dms/status
```

## Tests

```bash
python -m unittest discover src/dms_module/test
```

The node keeps MediaPipe and YOLO integration behind `core_perception.py`,
`face_analyzer.py`, and `object_detector.py`. Missing optional detectors do not
crash the ROS node; the result is marked invalid for bad frames and normal for
valid frames with no active detections.
