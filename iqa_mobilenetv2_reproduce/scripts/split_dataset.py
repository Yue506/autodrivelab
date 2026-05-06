import argparse
import random
import shutil
from pathlib import Path

from common import IMAGE_EXTENSIONS


TARGETS = {
    "normal": {"train": 5763, "val": 1235, "test": 1236},
    "soiling": {"train": 2800, "val": 600, "test": 600},
}


def list_images(path):
    return [p for p in Path(path).rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]


def split_counts(n, cls):
    target = TARGETS[cls]
    total = sum(target.values())
    if n >= total:
        return target
    train = int(round(n * target["train"] / total))
    val = int(round(n * target["val"] / total))
    test = n - train - val
    return {"train": train, "val": val, "test": test}


def copy_split(files, out_dir, cls, counts):
    cursor = 0
    for split in ["train", "val", "test"]:
        dst = Path(out_dir) / split / cls
        dst.mkdir(parents=True, exist_ok=True)
        for src in files[cursor:cursor + counts[split]]:
            shutil.copy2(src, dst / src.name)
        cursor += counts[split]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal_dir", required=True)
    parser.add_argument("--soiling_dir", required=True)
    parser.add_argument("--out_dir", default="data/woodscape_iqa")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    for cls, raw_dir in {"normal": args.normal_dir, "soiling": args.soiling_dir}.items():
        files = list_images(raw_dir)
        rng.shuffle(files)
        counts = split_counts(len(files), cls)
        copy_split(files, args.out_dir, cls, counts)
        print(cls, counts)


if __name__ == "__main__":
    main()
