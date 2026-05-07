import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import torch
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report,
                             confusion_matrix, precision_recall_fscore_support, roc_auc_score)
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
from tqdm import tqdm

from common import build_model, build_transforms, ensure_output_dirs, get_device, load_config, project_path, save_json


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, targets_all, probs_all, preds_all, paths_all = 0.0, [], [], [], []
    offset = 0
    with torch.no_grad():
        for images, targets in tqdm(loader):
            images, targets = images.to(device), targets.to(device)
            logits = model(images)
            loss = criterion(logits, targets)
            probs = torch.softmax(logits, dim=1)[:, 1]
            preds = logits.argmax(dim=1)
            total_loss += loss.item() * images.size(0)
            targets_all.extend(targets.cpu().numpy().tolist())
            probs_all.extend(probs.cpu().numpy().tolist())
            preds_all.extend(preds.cpu().numpy().tolist())
            batch_size = images.size(0)
            paths_all.extend(path for path, _ in loader.dataset.samples[offset:offset + batch_size])
            offset += batch_size
    precision, recall, f1, _ = precision_recall_fscore_support(targets_all, preds_all, average="binary", zero_division=0)
    auc = roc_auc_score(targets_all, probs_all)
    return {
        "test_loss": total_loss / max(len(targets_all), 1),
        "accuracy": accuracy_score(targets_all, preds_all),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc,
    }, targets_all, preds_all, probs_all, paths_all


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/iqa_mobilenetv2.yaml")
    parser.add_argument("--checkpoint", required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)
    ensure_output_dirs(cfg)
    device = get_device()
    dataset = ImageFolder(project_path(cfg, cfg["data"]["test_dir"]), transform=build_transforms(cfg, "test"))
    loader = DataLoader(dataset, batch_size=cfg["train"]["batch_size"], shuffle=False,
                        num_workers=cfg["train"]["num_workers"], pin_memory=True)
    model = build_model(cfg).to(device)
    ckpt = torch.load(project_path(cfg, args.checkpoint), map_location=device)
    model.load_state_dict(ckpt["model_state"])
    criterion = torch.nn.CrossEntropyLoss()
    metrics, y_true, y_pred, y_prob, paths = evaluate(model, loader, criterion, device)

    metrics_dir = project_path(cfg, cfg["output"]["metrics"])
    figures_dir = project_path(cfg, cfg["output"]["figures"])
    save_json(metrics_dir / "test_metrics.json", metrics)
    with open(metrics_dir / "test_predictions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "true_label", "pred_label", "soiling_probability"])
        writer.writeheader()
        for path, true_idx, pred_idx, prob in zip(paths, y_true, y_pred, y_prob):
            writer.writerow({
                "path": str(path),
                "true_label": dataset.classes[true_idx],
                "pred_label": dataset.classes[pred_idx],
                "soiling_probability": prob,
            })
    report = classification_report(y_true, y_pred, target_names=dataset.classes, digits=4)
    (metrics_dir / "classification_report.txt").write_text(report, encoding="utf-8")
    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(cm, display_labels=dataset.classes)
    fig, ax = plt.subplots(figsize=(5, 5))
    disp.plot(ax=ax, cmap="Blues", values_format="d", colorbar=False)
    fig.tight_layout()
    fig.savefig(figures_dir / "confusion_matrix.png", dpi=220)
    fig.savefig(figures_dir / "confusion_matrix.pdf")
    plt.close(fig)
    print(metrics)
    print(report)


if __name__ == "__main__":
    main()
