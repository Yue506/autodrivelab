# DMS Test Demo

This demo runs the DMS event-mapping pipeline on local labeled cabin videos and exports visualization videos plus frame-level JSONL records.

## Input

Place test videos under:

```text
data/DMS_test_data/
```

Expected demo files:

- `test_normal.MOV`
- `test_eyeclosed.MOV`
- `test_yawn.MOV`
- `test_smoke.MOV`
- `test_calling.MOV`
- `test_all.MOV`

The data directory is intentionally ignored by git.

## Run

```bash
python3 tools/run_dms_test_demo.py \
  --input-dir data/DMS_test_data \
  --output-dir demo_outputs/dms_test_demo \
  --sample-stride 3
```

If OpenCV cannot decode the source `.MOV` files on a Linux server, the tool automatically falls back to `ffmpeg` transcoding and then continues the same DMS visualization flow.

## Output

```text
demo_outputs/dms_test_demo/
├── summary.jsonl
├── README.md
└── <video_name>/
    ├── dms_status.jsonl
    └── dms_visualization.mp4
```

Risk levels follow the existing DMS event mapping:

| Scenario | Event | Level |
|---|---|---:|
| normal | `DRIVER_NORMAL` | 0 |
| eyeclosed | `DRIVER_EYES_CLOSED` | 3 |
| yawn | `DRIVER_YAWNING` | 2 |
| smoke | `DRIVER_SMOKING` | 2 |
| calling | `DRIVER_CALLING` | 3 |
| all | staged normal / eyeclosed / yawn / smoke / calling | 0-3 |
