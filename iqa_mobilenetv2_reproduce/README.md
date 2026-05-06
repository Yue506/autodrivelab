# IQA MobileNetV2 Reproduction

This repository reproduces the Image Quality Assessment module used in the OmniVision-BEV project.

## Task

Binary classification of vehicle fisheye camera images:

- normal / clear
- soiling / soiled

## Dataset

WoodScape fisheye dataset in ImageFolder format under `data/woodscape_iqa`.

Reproduced split:

| Split | Normal | Soiling |
|---|---:|---:|
| train | 5764 | 3500 |
| val | 1235 | 750 |
| test | 1235 | 750 |

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
python scripts/write_experiment_summary.py --config configs/iqa_mobilenetv2.yaml
```

## Results

Best checkpoint: epoch 5, validation F1 `1.0000`.

| Metric | Value |
|---|---:|
| Test Loss | 0.0096 |
| Accuracy | 0.9985 |
| Precision | 0.9987 |
| Recall | 0.9973 |
| F1 Score | 0.9980 |
| AUC | 1.0000 |

Artifacts are saved under `outputs/iqa_mobilenetv2/`, and the concise report is in `docs/experiment_summary.md`.

## References

- WoodScape: https://woodscape.valeo.com
- WoodScape GitHub: https://github.com/valeoai/woodscape
- Torchvision MobileNetV2: https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.mobilenet_v2.html
