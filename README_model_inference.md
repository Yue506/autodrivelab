# YOLO + Depth Anything Demo Pipeline

This pipeline replaces the demo ADAS/TTC input stream with model-estimated detections and monocular depth:

```text
YOLO + Depth Anything -> pred_adas_objects.jsonl -> pred_adas_status.jsonl -> fusion -> final_demo_model.mp4
```

## Run

```bash
source /root/autodl-tmp/yolo_depth_env/bin/activate
bash scripts/run_yolo_depth_demo.sh
```

Optional overrides:

```bash
YOLO_MODEL=yolo26s.pt YOLO_CONF=0.20 YOLO_IMGSZ=960 bash scripts/run_yolo_depth_demo.sh
```

The script first tries the requested YOLO weight, then falls back through `yolo26s.pt`, `yolo26n.pt`, `yolo11s.pt`, and `yolov8s.pt` if the installed Ultralytics package cannot load a newer weight.

## Outputs

Runtime artifacts are written under `model_inference_outputs/`:

- `yolo_depth_predictions.jsonl`
- `pred_adas_objects.jsonl`
- `pred_adas_status.jsonl`
- `fusion_status_model.jsonl`
- `final_demo_model.mp4`
- `model_inference_report.md`

The model-estimated distance is a monocular estimate calibrated for offline demo visualization. High FCW risk is gated by estimated closing speed and TTC across frames; a close target without an approaching relative-speed trend remains non-emergency in the ADAS status output.
