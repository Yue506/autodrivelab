# Roadmap

## Phase 1: ROS2 Demo Skeleton
- Build shared message contracts.
- Launch all modules with mock data.
- Verify end-to-end topics: gateway -> perception/DMS/IQA -> prediction -> arbiter -> HMI/data loop.

## Phase 2: nuScenes Replay
- Implement nuScenes scene loader in `signal_gateway`.
- Publish camera metadata, ego-state and synthetic cabin frames.
- Add deterministic demo scenes for thesis experiments.

## Phase 3: Algorithms
- Integrate BEV perception prototype.
- Port DMS prototype into `dms_monitor` with platform-independent audio handling.
- Add IQA metrics for blur, exposure, occlusion and camera-drop detection.

## Phase 4: Arbitration and CAN
- Formalize risk-level mapping.
- Add CAN-frame encode/decode abstraction.
- Connect HMI visual/audio commands and edge-case triggers.

## Phase 5: Evaluation
- Define scenario-level metrics.
- Generate logs, plots and replayable edge-case manifests.
