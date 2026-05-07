import argparse
import shutil

import torch

from common import build_model, ensure_output_dirs, get_device, load_config, project_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/iqa_mobilenetv2.yaml")
    parser.add_argument("--checkpoint", required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)
    ensure_output_dirs(cfg)
    device = get_device()
    model = build_model(cfg).to(device)
    ckpt_path = project_path(cfg, args.checkpoint)
    ckpt = torch.load(ckpt_path, map_location=device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    out_dir = project_path(cfg, cfg["output"]["checkpoints"])
    shutil.copy2(ckpt_path, out_dir / "iqa_mobilenetv2_best.pt")
    example = torch.randn(1, 3, cfg["train"]["image_size"], cfg["train"]["image_size"], device=device)
    traced = torch.jit.trace(model, example)
    traced.save(str(out_dir / "iqa_mobilenetv2_torchscript.pt"))
    torch.onnx.export(
        model,
        example,
        out_dir / "iqa_mobilenetv2.onnx",
        input_names=["image"],
        output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )
    print(f"Exported models to {out_dir}")


if __name__ == "__main__":
    main()
