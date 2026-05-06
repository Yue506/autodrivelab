# IQA MobileNetV2 Reproduction

This repository reproduces the Image Quality Assessment module used in the OmniVision-BEV project.

## Task

Binary classification of vehicle fisheye camera images:

- normal / clear
- soiling / soiled

## Dataset

WoodScape fisheye dataset in ImageFolder format under `data/woodscape_iqa`.

Expected split:

| Split | Normal | Soiling |
|---|---:|---:|
| train | 5763 | 2800 |
| val | 1235 | 600 |
| test | 1236 | 600 |

## Model

MobileNetV2 initialized with official Torchvision ImageNet pretrained weights and fine-tuned for 2-class soiling detection.

## Quick Start

```bash
conda create -n iqa_mobilenetv2 python=3.10 -y
conda activate iqa_mobilenetv2
pip install -r requirements.txt
python scripts/check_dataset.py --config configs/iqa_mobilenetv2.yaml
python scripts/train_iqa.py --config configs/iqa_mobilenetv2.yaml
python scripts/evaluate_iqa.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt
python scripts/infer_samples.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt
python scripts/export_model.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt
```

## Results

Run the experiment to populate `outputs/iqa_mobilenetv2/metrics/test_metrics.json` and `docs/experiment_summary.md`.

## References

- WoodScape: https://woodscape.valeo.com
- WoodScape GitHub: https://github.com/valeoai/woodscape
- Torchvision MobileNetV2: https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.mobilenet_v2.html
