# IQA Test Result Integration

IQA 模块独立基于自建测试数据进行 normal/soiling 二分类测试；nuScenes 仅用于车外场景回放、GT ADAS 伪感知和 FSD-style 渲染。

## Data And Result Format

The unified test-result file is `iqa_test_results.jsonl`; each row contains:

- `image_path`
- `camera_name`
- `quality_state`
- `soiling_score`
- `normal_score`
- `label`
- `pred`
- `correct`

The demo timeline file is `demo_outputs/scene_000/iqa_status_from_test.jsonl`; each row is aligned to a nuScenes demo `frame_index` and can be published as `/iqa/status`.

## Commands

```bash
python tools/export_iqa_test_results.py \
  --data-root data/IQA_data \
  --out demo_outputs/iqa_test_results.jsonl

python tools/build_iqa_timeline_from_test.py \
  --frames demo_outputs/scene_000/demo_cache/frames.jsonl \
  --iqa-results demo_outputs/iqa_test_results.jsonl \
  --out demo_outputs/scene_000/iqa_status_from_test.jsonl \
  --strategy segment

python tools/write_iqa_test_report.py \
  --iqa-results demo_outputs/iqa_test_results.jsonl \
  --out demo_outputs/iqa_test_report.md
```

## ROS2

```bash
ros2 launch demo_pipeline demo_ros2.launch.py \
  iqa_mode:=offline_test_result \
  iqa_result:=demo_outputs/scene_000/iqa_status_from_test.jsonl
```

The arbitration node consumes the same `/iqa/status` fields for scripted and offline-test-result modes, so it does not need to know which IQA source generated the status.
