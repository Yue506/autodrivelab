#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from itertools import cycle
from pathlib import Path


CRITICAL = {"CAM_FRONT", "CAM_FRONT_LEFT", "CAM_FRONT_RIGHT"}


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def choose_pool(results: list[dict], state: str) -> list[dict]:
    pool = [row for row in results if row.get("quality_state") == state or row.get("pred") == state or row.get("label") == state]
    return pool or results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", required=True)
    parser.add_argument("--iqa-results", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--strategy", choices=["segment", "cycle"], default="segment")
    args = parser.parse_args()
    frames = read_jsonl(Path(args.frames))
    results = read_jsonl(Path(args.iqa_results))
    normal_iter = cycle(choose_pool(results, "normal"))
    soiling_iter = cycle(choose_pool(results, "soiling"))
    all_iter = cycle(results)
    rows = []
    for idx, frame in enumerate(frames):
        ratio = idx / max(len(frames), 1)
        want = "soiling" if (0.40 <= ratio < 0.70 and args.strategy == "segment") else "normal"
        sample = next(soiling_iter if want == "soiling" else normal_iter) if args.strategy == "segment" else next(all_iter)
        camera = sample.get("camera_name") or "CAM_FRONT"
        soiled = bool(sample.get("is_soiled", sample.get("quality_state") == "soiling"))
        score = float(sample.get("soiling_score", 0.92 if soiled else 0.03))
        critical = camera in CRITICAL and soiled
        rows.append(
            {
                "frame_index": frame["frame_index"],
                "timestamp": frame["timestamp"],
                "iqa_level": 3 if critical else (1 if soiled else 0),
                "soiled_camera_count": 1 if soiled else 0,
                "soiled_cameras": [camera] if soiled else [],
                "critical_camera_soiled": critical,
                "camera_states": {
                    camera: {
                        "quality_state": "soiling" if soiled else "normal",
                        "soiling_score": score,
                        "source_image": sample.get("image_path", ""),
                        "is_soiled": soiled,
                    }
                },
                "confidence": score if soiled else float(sample.get("normal_score", 1.0 - score)),
                "valid": True,
                "source": "custom_iqa_test_dataset",
                "source_image": sample.get("image_path", ""),
                "quality_state": "soiling" if soiled else "normal",
            }
        )
    write_jsonl(Path(args.out), rows)
    print(f"IQA timeline: {args.out}")
    print(f"Frames: {len(rows)}; soiling frames: {sum(row['iqa_level'] > 0 for row in rows)}")


if __name__ == "__main__":
    main()
