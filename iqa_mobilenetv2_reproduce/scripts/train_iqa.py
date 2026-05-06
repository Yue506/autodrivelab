import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from torchvision.datasets import ImageFolder
from tqdm import tqdm

from common import build_model, build_transforms, ensure_output_dirs, get_device, load_config, project_path, set_seed


def run_epoch(model, loader, criterion, device, optimizer=None, scaler=None):
    training = optimizer is not None
    model.train(training)
    total_loss, total_correct, total = 0.0, 0, 0
    all_targets, all_probs, all_preds = [], [], []
    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for images, targets in tqdm(loader, leave=False):
            images, targets = images.to(device), targets.to(device)
            if training:
                optimizer.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=scaler is not None):
                logits = model(images)
                loss = criterion(logits, targets)
            if training:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            probs = torch.softmax(logits, dim=1)[:, 1]
            preds = logits.argmax(dim=1)
            total_loss += loss.item() * images.size(0)
            total_correct += (preds == targets).sum().item()
            total += images.size(0)
            all_targets.extend(targets.detach().cpu().numpy().tolist())
            all_probs.extend(probs.detach().cpu().numpy().tolist())
            all_preds.extend(preds.detach().cpu().numpy().tolist())
    precision, recall, f1, _ = precision_recall_fscore_support(
        all_targets, all_preds, average="binary", zero_division=0
    )
    try:
        auc = roc_auc_score(all_targets, all_probs)
    except ValueError:
        auc = float("nan")
    return {
        "loss": total_loss / max(total, 1),
        "accuracy": total_correct / max(total, 1),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "auc": auc,
    }


def save_curves(rows, out_path):
    epochs = [r["epoch"] for r in rows]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    axes[0, 0].plot(epochs, [r["train_loss"] for r in rows], label="train")
    axes[0, 0].plot(epochs, [r["val_loss"] for r in rows], label="val")
    axes[0, 0].set_title("Loss")
    axes[0, 0].legend()
    axes[0, 1].plot(epochs, [r["train_accuracy"] for r in rows], label="train")
    axes[0, 1].plot(epochs, [r["val_accuracy"] for r in rows], label="val")
    axes[0, 1].set_title("Accuracy")
    axes[0, 1].legend()
    axes[1, 0].plot(epochs, [r["val_precision"] for r in rows], label="precision")
    axes[1, 0].plot(epochs, [r["val_recall"] for r in rows], label="recall")
    axes[1, 0].plot(epochs, [r["val_f1"] for r in rows], label="f1")
    axes[1, 0].set_title("Validation PRF")
    axes[1, 0].legend()
    axes[1, 1].plot(epochs, [r["val_auc"] for r in rows], label="auc")
    axes[1, 1].set_title("Validation AUC")
    axes[1, 1].legend()
    fig.tight_layout()
    fig.savefig(out_path.with_suffix(".png"), dpi=200)
    fig.savefig(out_path.with_suffix(".pdf"))
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/iqa_mobilenetv2.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    ensure_output_dirs(cfg)
    set_seed(cfg["seed"])
    device = get_device()
    print(f"Using device: {device}")

    train_ds = ImageFolder(project_path(cfg, cfg["data"]["train_dir"]), transform=build_transforms(cfg, "train"))
    val_ds = ImageFolder(project_path(cfg, cfg["data"]["val_dir"]), transform=build_transforms(cfg, "val"))
    print("Class mapping:", train_ds.class_to_idx)
    train_loader = DataLoader(train_ds, batch_size=cfg["train"]["batch_size"], shuffle=True,
                              num_workers=cfg["train"]["num_workers"], pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=cfg["train"]["batch_size"], shuffle=False,
                            num_workers=cfg["train"]["num_workers"], pin_memory=True)
    model = build_model(cfg).to(device)
    criterion = torch.nn.CrossEntropyLoss(label_smoothing=cfg["train"].get("label_smoothing", 0.0))
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["train"]["learning_rate"],
                                  weight_decay=cfg["train"]["weight_decay"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg["train"]["epochs"])
    scaler = torch.cuda.amp.GradScaler(enabled=(device.type == "cuda" and cfg["train"].get("amp", True)))
    writer = SummaryWriter(project_path(cfg, cfg["output"]["logs"]) / "tensorboard")

    ckpt_dir = project_path(cfg, cfg["output"]["checkpoints"])
    log_path = project_path(cfg, cfg["output"]["logs"]) / "train_log.csv"
    rows, best_score, stale = [], -1.0, 0
    metric_for_best = cfg["train"].get("metric_for_best", "f1")
    fields = ["epoch", "lr", "train_loss", "train_accuracy", "val_loss", "val_accuracy",
              "val_precision", "val_recall", "val_f1", "val_auc"]
    for epoch in range(1, cfg["train"]["epochs"] + 1):
        train_metrics = run_epoch(model, train_loader, criterion, device, optimizer, scaler)
        val_metrics = run_epoch(model, val_loader, criterion, device)
        scheduler.step()
        row = {
            "epoch": epoch,
            "lr": scheduler.get_last_lr()[0],
            "train_loss": train_metrics["loss"],
            "train_accuracy": train_metrics["accuracy"],
            "val_loss": val_metrics["loss"],
            "val_accuracy": val_metrics["accuracy"],
            "val_precision": val_metrics["precision"],
            "val_recall": val_metrics["recall"],
            "val_f1": val_metrics["f1"],
            "val_auc": val_metrics["auc"],
        }
        rows.append(row)
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer_csv = csv.DictWriter(f, fieldnames=fields)
            writer_csv.writeheader()
            writer_csv.writerows(rows)
        for key, value in row.items():
            if key not in {"epoch", "lr"}:
                writer.add_scalar(key, value, epoch)
        state = {"epoch": epoch, "model_state": model.state_dict(), "optimizer_state": optimizer.state_dict(),
                 "scheduler_state": scheduler.state_dict(), "config": cfg, "class_to_idx": train_ds.class_to_idx,
                 "metrics": row}
        torch.save(state, ckpt_dir / "last.pt")
        score = row[f"val_{metric_for_best}"]
        if score > best_score:
            best_score, stale = score, 0
            torch.save(state, ckpt_dir / "best.pt")
        else:
            stale += 1
        save_curves(rows, project_path(cfg, cfg["output"]["figures"]) / "training_curves")
        print(f"epoch={epoch} val_acc={row['val_accuracy']:.4f} val_f1={row['val_f1']:.4f} best={best_score:.4f}")
        if stale >= cfg["train"].get("early_stopping_patience", 30):
            print("Early stopping triggered.")
            break
    writer.close()


if __name__ == "__main__":
    main()
