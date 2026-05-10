# AutoDriveLab RViz2 3D Visualization

This package converts `autodrivelab_msgs/msg/BevObjects` into `visualization_msgs/msg/MarkerArray` for ROS2/RViz2 debugging and demonstration.

## Input

Default topic:

```bash
/autodrivelab/bev/objects
```

Message type:

```bash
autodrivelab_msgs/msg/BevObjects
```

## Output

Default topic:

```bash
/autodrivelab/rviz/objects
```

Message type:

```bash
visualization_msgs/msg/MarkerArray
```

## Run With The Existing Demo Topic

```bash
colcon build --symlink-install --packages-select autodrivelab_msgs autodrivelab_visualization
source install/setup.bash
ros2 launch autodrivelab_visualization rviz_3d_markers.launch.py use_rviz:=true
```

## Standalone Smoke Test

Terminal 1:

```bash
source install/setup.bash
ros2 run autodrivelab_visualization test_bev_objects_publisher
```

Terminal 2:

```bash
source install/setup.bash
ros2 launch autodrivelab_visualization rviz_3d_markers.launch.py input_topic:=/bev_objects use_rviz:=true
```

## Display Strategy

The first version uses stable RViz primitives instead of external mesh assets:

- Vehicle: `CUBE`
- Pedestrian: `CYLINDER`
- Cyclist: `CUBE`
- Barrier: `CUBE`
- Cone: `CYLINDER`
- Velocity: `ARROW`

`object_scale_factor` defaults to `0.75`. It only changes the display size of markers and never changes the real BEV coordinates.
