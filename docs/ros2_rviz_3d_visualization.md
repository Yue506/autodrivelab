# ROS2 RViz2 3D Visualization

AutoDriveLab now provides an optional RViz2 visualization layer for 3D-style debugging and presentation. The module subscribes to the internal `BevObjects` stream and publishes a `MarkerArray` that RViz2 can render as vehicles, pedestrians, cyclists and static obstacles.

This layer is independent from the perception, prediction, arbitration and offline video-rendering logic. It is intended as a display adapter, not as an algorithmic replacement.

## Message Flow

```text
/autodrivelab/bev/objects
  -> autodrivelab_visualization/bev_marker_node
  -> /autodrivelab/rviz/objects
  -> RViz2 MarkerArray display
```

## Topics

| Direction | Topic | Type |
| --- | --- | --- |
| Input | `/autodrivelab/bev/objects` | `autodrivelab_msgs/msg/BevObjects` |
| Output | `/autodrivelab/rviz/objects` | `visualization_msgs/msg/MarkerArray` |

The input topic can be changed with `input_topic:=...`. For standalone validation, the package also provides a sample publisher on `/bev_objects`.

## Supported Classes

| Class | RViz Marker | Notes |
| --- | --- | --- |
| vehicle, car, truck, bus | `CUBE` | Blue rectangular vehicle body |
| pedestrian, person | `CYLINDER` | Yellow vertical marker |
| cyclist, bicycle, motorcycle | `CUBE` | Green compact marker |
| barrier | `CUBE` | Gray low obstacle marker |
| cone, traffic_cone | `CYLINDER` | Orange static marker |
| unknown | `CUBE` | Neutral fallback marker |

Velocity arrows are shown for moving objects when `show_velocity_arrow:=true`.

## Run

```bash
colcon build --symlink-install --packages-select autodrivelab_msgs autodrivelab_visualization
source install/setup.bash
ros2 launch autodrivelab_visualization rviz_3d_markers.launch.py use_rviz:=true
```

For a standalone smoke test:

```bash
source install/setup.bash
ros2 run autodrivelab_visualization test_bev_objects_publisher
```

In another terminal:

```bash
source install/setup.bash
ros2 launch autodrivelab_visualization rviz_3d_markers.launch.py input_topic:=/bev_objects use_rviz:=true
```

## Marker Scaling

`object_scale_factor` defaults to `0.75` to reduce visual overlap in close-range 3D views. This parameter only scales marker geometry:

```bash
ros2 launch autodrivelab_visualization rviz_3d_markers.launch.py object_scale_factor:=0.65
```

The node does not change `x_m`, `y_m` or `yaw_rad`, so the visualization remains faithful to the BEV coordinate system.

## Future Mesh Extension

External mesh assets should remain optional. If mesh models are added later, keep primitive markers as the default path and enable meshes only through an explicit parameter so that RViz2 demos remain robust on clean machines.
