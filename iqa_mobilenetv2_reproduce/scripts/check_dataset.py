import argparse
from pathlib import Path

import pandas as pd
from PIL import Image
from tqdm import tqdm

from common import ensure_output_dirs, image_files, load_config, project_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/iqa_mobilenetv2.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    ensure_output_dirs(cfg)

    rows = []
    bad_images = []
    for split in ["train", "val", "test"]:
        for cls in cfg["data"]["class_names"]:
            class_dir = project_path(cfg, cfg["data"][f"{split}_dir"]) / cls
            files = image_files(class_dir)
            ok = 0
            for path in tqdm(files, desc=f"{split}/{cls}"):
                try:
                    with Image.open(path) as img:
                        img.verify()
                    ok += 1
                except Exception as exc:
                    bad_images.append({"split": split, "class": cls, "path": str(path), "error": str(exc)})
            rows.append({"split": split, "class": cls, "count": len(files), "valid_images": ok})

    summary = pd.DataFrame(rows)
    out_dir = project_path(cfg, cfg["output"]["metrics"])
    out_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_dir / "dataset_summary.csv", index=False)
    if bad_images:
        pd.DataFrame(bad_images).to_csv(out_dir / "bad_images.csv", index=False)
    print(summary.to_string(index=False))
    if bad_images:
        raise SystemExit(f"Found {len(bad_images)} unreadable images. See {out_dir / 'bad_images.csv'}")


if __name__ == "__main__":
    main()
