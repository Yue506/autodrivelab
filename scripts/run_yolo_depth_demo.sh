#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python tools/model_inference/run_yolo_depth_demo_pipeline.py \
  --scene-dir "${SCENE_DIR:-demo_outputs/scene_000}" \
  --out-dir "${OUT_DIR:-model_inference_outputs}" \
  --yolo-model "${YOLO_MODEL:-yolo26s.pt}" \
  --depth-model "${DEPTH_MODEL:-depth-anything/Depth-Anything-V2-Small-hf}" \
  --conf "${YOLO_CONF:-0.20}" \
  --imgsz "${YOLO_IMGSZ:-960}"
