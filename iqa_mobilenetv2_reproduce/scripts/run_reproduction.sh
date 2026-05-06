#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python scripts/split_dataset.py --config configs/iqa_mobilenetv2.yaml --clean --symlink
python scripts/check_dataset.py --config configs/iqa_mobilenetv2.yaml
python scripts/train_iqa.py --config configs/iqa_mobilenetv2.yaml
python scripts/evaluate_iqa.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt
python scripts/infer_samples.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt --num_normal 15 --num_soiling 15
python scripts/export_model.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt
python scripts/write_experiment_summary.py --config configs/iqa_mobilenetv2.yaml
