import argparse
import csv
import json
from pathlib import Path

from common import load_config, project_path


def read_dataset_summary(path):
    rows = []
    if not path.exists():
        return rows
    with open(path, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows


def format_metric(value):
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/iqa_mobilenetv2.yaml")
    parser.add_argument("--output", default="docs/experiment_summary.md")
    args = parser.parse_args()

    cfg = load_config(args.config)
    metrics_dir = project_path(cfg, cfg["output"]["metrics"])
    summary_csv = metrics_dir / "dataset_summary.csv"
    metrics_json = metrics_dir / "test_metrics.json"
    train_log = project_path(cfg, cfg["output"]["logs"]) / "train_log.csv"

    dataset_rows = read_dataset_summary(summary_csv)
    metrics = {}
    if metrics_json.exists():
        metrics = json.loads(metrics_json.read_text(encoding="utf-8"))
    final_epoch = None
    best_val = None
    if train_log.exists():
        with open(train_log, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            final_epoch = rows[-1]["epoch"]
            best_val = max(float(row["val_f1"]) for row in rows)

    dataset_table = "\n".join(
        f"| {row['split']} | {row['class']} | {row['count']} | {row['valid_images']} |"
        for row in dataset_rows
    )
    if not dataset_table:
        dataset_table = "| n/a | n/a | n/a | n/a |"

    metric_rows = "\n".join(
        f"| {name} | {format_metric(metrics.get(key, 'n/a'))} |"
        for name, key in [
            ("Test Loss", "test_loss"),
            ("Accuracy", "accuracy"),
            ("Precision", "precision"),
            ("Recall", "recall"),
            ("F1 Score", "f1"),
            ("AUC", "auc"),
        ]
    )

    content = f"""# IQA MobileNetV2 Experiment Summary

## Dataset

- Dataset: WoodScape fisheye soiling dataset
- Task: binary classification
- Classes: normal, soiling
- Split strategy: stratified 70% train / 15% validation / 15% test with seed `{cfg['seed']}`

| Split | Class | Count | Valid Images |
|---|---|---:|---:|
{dataset_table}

## Model

- Backbone: MobileNetV2
- Pretrained weights: official ImageNet pretrained weights from Torchvision
- Classifier: 2-class linear classification head

## Training Setup

- Image size: {cfg['train']['image_size']} x {cfg['train']['image_size']}
- Optimizer: AdamW
- Scheduler: Cosine learning rate scheduler
- Epochs configured: {cfg['train']['epochs']}
- Epochs completed: {final_epoch or 'n/a'}
- Batch size: {cfg['train']['batch_size']}
- Best validation F1: {format_metric(best_val) if best_val is not None else 'n/a'}

## Test Results

| Metric | Value |
|---|---:|
{metric_rows}

## Output Figures

- Training curves: `outputs/iqa_mobilenetv2/figures/training_curves.png`
- Confusion matrix: `outputs/iqa_mobilenetv2/figures/confusion_matrix.png`
- Qualitative inference samples: `outputs/iqa_mobilenetv2/figures/qualitative_iqa_samples.png`

## Artifacts

- Best checkpoint: `outputs/iqa_mobilenetv2/checkpoints/best.pt`
- Last checkpoint: `outputs/iqa_mobilenetv2/checkpoints/last.pt`
- TorchScript: `outputs/iqa_mobilenetv2/checkpoints/iqa_mobilenetv2_torchscript.pt`
- ONNX: `outputs/iqa_mobilenetv2/checkpoints/iqa_mobilenetv2.onnx`
- Test predictions: `outputs/iqa_mobilenetv2/metrics/test_predictions.csv`

## Notes

The reproduced result may differ from the report because of dataset version, split strategy, preprocessing, augmentation, random seed, and hardware environment.
"""
    output = project_path(cfg, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
