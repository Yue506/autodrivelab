import json
import os
import random
from pathlib import Path

import numpy as np
import torch
import yaml
from torchvision import transforms
from torchvision.models import MobileNet_V2_Weights, mobilenet_v2


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    base = Path(path).resolve().parents[1]
    cfg["_base_dir"] = str(base)
    return cfg


def project_path(cfg, value):
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(cfg["_base_dir"]) / path


def ensure_output_dirs(cfg):
    for value in cfg["output"].values():
        project_path(cfg, value).mkdir(parents=True, exist_ok=True)


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = False


def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def build_model(cfg):
    weights = MobileNet_V2_Weights.DEFAULT if cfg["model"].get("pretrained", True) else None
    model = mobilenet_v2(weights=weights)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, cfg["model"]["num_classes"])
    return model


def build_transforms(cfg, split):
    image_size = cfg["train"]["image_size"]
    weights = MobileNet_V2_Weights.DEFAULT
    mean = weights.transforms().mean
    std = weights.transforms().std
    if split == "train":
        ops = []
        aug = cfg.get("augmentation", {}).get("train", {})
        if aug.get("random_resized_crop", True):
            ops.append(transforms.RandomResizedCrop(image_size, scale=(0.75, 1.0)))
        else:
            ops.extend([transforms.Resize(image_size), transforms.CenterCrop(image_size)])
        if aug.get("horizontal_flip", True):
            ops.append(transforms.RandomHorizontalFlip())
        if aug.get("color_jitter", True):
            ops.append(transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.15, hue=0.02))
        rotation = aug.get("rotation", 0)
        if rotation:
            ops.append(transforms.RandomRotation(rotation))
        ops.extend([transforms.ToTensor(), transforms.Normalize(mean=mean, std=std)])
        return transforms.Compose(ops)
    val_aug = cfg.get("augmentation", {}).get("val_test", {})
    resize = val_aug.get("resize", 256)
    crop = val_aug.get("center_crop", image_size)
    return transforms.Compose([
        transforms.Resize(resize),
        transforms.CenterCrop(crop),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])


def save_json(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def image_files(root):
    root = Path(root)
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
