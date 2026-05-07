# Server IQA Reproduction Status

## Server

- Host: `connect.westc.seetacloud.com`
- SSH port: `31957`
- Repository path: `/root/autodl-tmp/autodrivelab`
- Branch: `iqa-mobilenetv2-repro`
- Commit: `30552f3 Add IQA MobileNetV2 reproduction pipeline`
- GPU: NVIDIA GeForce RTX 4090 D, CUDA available in base conda environment

## Completed

- Cloned `https://github.com/Yue506/autodrivelab.git` into `/root/autodl-tmp/autodrivelab`.
- Created branch `iqa-mobilenetv2-repro`.
- Added MobileNetV2 IQA reproduction project under `iqa_mobilenetv2_reproduce/`.
- Verified Python scripts compile on the server.
- Installed missing base-environment dependencies: `pandas`, `scikit-learn`, `opencv-python`, `onnx`.
- Verified base environment has CUDA-enabled PyTorch:
  - `torch 2.5.1+cu124`
  - `torchvision 0.20.1+cu124`
  - CUDA device: `NVIDIA GeForce RTX 4090 D`
- Ran dataset check script and generated `outputs/iqa_mobilenetv2/metrics/dataset_summary.csv`.

## Current Blocker

The WoodScape IQA images are not present on the server. The generated dataset summary reports zero images for:

- `train/normal`
- `train/soiling`
- `val/normal`
- `val/soiling`
- `test/normal`
- `test/soiling`

Training, evaluation, model export, and the 98% binary accuracy target require the actual WoodScape soiling dataset in ImageFolder format under:

```text
iqa_mobilenetv2_reproduce/data/woodscape_iqa/
├── train/
│   ├── normal/
│   └── soiling/
├── val/
│   ├── normal/
│   └── soiling/
└── test/
    ├── normal/
    └── soiling/
```

## Resume Commands

After placing the dataset, run:

```bash
cd /root/autodl-tmp/autodrivelab/iqa_mobilenetv2_reproduce
/root/miniconda3/bin/python scripts/check_dataset.py --config configs/iqa_mobilenetv2.yaml
/root/miniconda3/bin/python scripts/train_iqa.py --config configs/iqa_mobilenetv2.yaml
/root/miniconda3/bin/python scripts/evaluate_iqa.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt
/root/miniconda3/bin/python scripts/infer_samples.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt --num_normal 15 --num_soiling 15
/root/miniconda3/bin/python scripts/export_model.py --config configs/iqa_mobilenetv2.yaml --checkpoint outputs/iqa_mobilenetv2/checkpoints/best.pt
```

Then update `docs/experiment_summary.md` with the values from `outputs/iqa_mobilenetv2/metrics/test_metrics.json`.
