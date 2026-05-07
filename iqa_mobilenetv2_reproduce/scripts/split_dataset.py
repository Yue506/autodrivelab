import argparse
import random
import shutil
from pathlib import Path

from common import IMAGE_EXTENSIONS, load_config, project_path


TARGETS = {
    "normal": {"train": 5763, "val": 1235, "test": 1236},
    "soiling": {"train": 2800, "val": 600, "test": 600},
}


def list_images(path):
    return [p for p in Path(path).rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]


def split_counts(n, cls, ratios=None, use_report_counts=False):
    if use_report_counts:
        target = TARGETS[cls]
        total = sum(target.values())
        if n >= total:
            return target
        ratios = {split: target[split] / total for split in ["train", "val", "test"]}
    ratios = ratios or {"train": 0.70, "val": 0.15, "test": 0.15}
    train = int(round(n * ratios["train"]))
    val = int(round(n * ratios["val"]))
    test = n - train - val
    return {"train": train, "val": val, "test": test}


def copy_split(files, out_dir, cls, counts, symlink=False):
    cursor = 0
    for split in ["train", "val", "test"]:
        dst = Path(out_dir) / split / cls
        dst.mkdir(parents=True, exist_ok=True)
        for src in files[cursor:cursor + counts[split]]:
            target = dst / src.name
            if target.exists() or target.is_symlink():
                target.unlink()
            if symlink:
                target.symlink_to(src.resolve())
            else:
                shutil.copy2(src, target)
        cursor += counts[split]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--normal_dir", default=None)
    parser.add_argument("--soiling_dir", default=None)
    parser.add_argument("--out_dir", default="data/woodscape_iqa")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--clean", action="store_true", help="Remove the output split before recreating it.")
    parser.add_argument("--symlink", action="store_true", help="Create symlinks instead of copying images.")
    parser.add_argument("--use_report_counts", action="store_true", help="Use the report's fixed 5763/1235/1236 and 2800/600/600 counts.")
    args = parser.parse_args()

    cfg = load_config(args.config) if args.config else None
    if cfg:
        args.normal_dir = args.normal_dir or project_path(cfg, cfg["data"]["raw_normal_dir"])
        args.soiling_dir = args.soiling_dir or project_path(cfg, cfg["data"]["raw_soiling_dir"])
        args.out_dir = project_path(cfg, args.out_dir)
        ratios = cfg.get("split", {}).get("ratios", None)
    else:
        ratios = None
    if not args.normal_dir or not args.soiling_dir:
        raise SystemExit("normal and soiling directories are required, either by --config or explicit arguments.")

    out_dir = Path(args.out_dir)
    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)

    rng = random.Random(args.seed)
    for cls, raw_dir in {"normal": args.normal_dir, "soiling": args.soiling_dir}.items():
        files = list_images(raw_dir)
        if not files:
            raise SystemExit(f"No images found for {cls}: {raw_dir}")
        rng.shuffle(files)
        counts = split_counts(len(files), cls, ratios=ratios, use_report_counts=args.use_report_counts)
        copy_split(files, out_dir, cls, counts, symlink=args.symlink)
        print(cls, counts)


if __name__ == "__main__":
    main()
