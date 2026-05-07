import argparse
import random

import matplotlib.pyplot as plt
import torch
from PIL import Image

from common import build_model, build_transforms, ensure_output_dirs, get_device, image_files, load_config, project_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/iqa_mobilenetv2.yaml")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--num_normal", type=int, default=15)
    parser.add_argument("--num_soiling", type=int, default=15)
    args = parser.parse_args()
    cfg = load_config(args.config)
    ensure_output_dirs(cfg)
    rng = random.Random(cfg["seed"])
    device = get_device()
    transform = build_transforms(cfg, "test")
    model = build_model(cfg).to(device)
    ckpt = torch.load(project_path(cfg, args.checkpoint), map_location=device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    samples = []
    for cls, n in [("normal", args.num_normal), ("soiling", args.num_soiling)]:
        files = image_files(project_path(cfg, cfg["data"]["test_dir"]) / cls)
        chosen = rng.sample(files, min(n, len(files)))
        samples.extend((path, cls) for path in chosen)
    class_names = cfg["data"]["class_names"]
    fig, axes = plt.subplots(5, 6, figsize=(15, 11))
    for ax in axes.flat:
        ax.axis("off")
    with torch.no_grad():
        for ax, (path, true_label) in zip(axes.flat, samples):
            image = Image.open(path).convert("RGB")
            tensor = transform(image).unsqueeze(0).to(device)
            prob = torch.softmax(model(tensor), dim=1)[0]
            pred_idx = int(prob.argmax().item())
            pred = class_names[pred_idx]
            conf = float(prob[pred_idx].item())
            ax.imshow(image)
            ax.set_title(f"T:{true_label} P:{pred} {conf:.3f}", fontsize=9)
            ax.axis("off")
    fig.tight_layout()
    figures_dir = project_path(cfg, cfg["output"]["figures"])
    fig.savefig(figures_dir / "qualitative_iqa_samples.png", dpi=220)
    fig.savefig(figures_dir / "qualitative_iqa_samples.pdf")
    plt.close(fig)


if __name__ == "__main__":
    main()
