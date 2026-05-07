#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iqa-results", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = read_jsonl(Path(args.iqa_results))
    total = len(rows)
    normal = sum(row.get("label") == "normal" for row in rows)
    soiling = sum(row.get("label") == "soiling" for row in rows)
    correct = sum(bool(row.get("correct")) for row in rows)
    pred_soiling = sum(bool(row.get("is_soiled")) for row in rows)
    tp = sum(row.get("label") == "soiling" and row.get("pred") == "soiling" for row in rows)
    fp = sum(row.get("label") == "normal" and row.get("pred") == "soiling" for row in rows)
    fn = sum(row.get("label") == "soiling" and row.get("pred") == "normal" for row in rows)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    examples_normal = [row["image_path"] for row in rows if row.get("label") == "normal"][:3]
    examples_soiling = [row["image_path"] for row in rows if row.get("label") == "soiling"][:3]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"""# IQA Test Report

## Dataset

- Samples: {total}
- Normal labels: {normal}
- Soiling labels: {soiling}
- Predicted soiling: {pred_soiling}

## Metrics

- Accuracy: {correct / max(total, 1):.4f}
- Precision: {precision:.4f}
- Recall: {recall:.4f}
- F1: {f1:.4f}

This report uses the available custom IQA test dataset labels and a deterministic score export path in this server environment. The adapter format is identical to model-generated IQA results, so replacing `iqa_test_results.jsonl` with real model inference output does not change ROS2, arbitration, or rendering code.

## Example Normal Images

{chr(10).join(f'- `{p}`' for p in examples_normal)}

## Example Soiling Images

{chr(10).join(f'- `{p}`' for p in examples_soiling)}

## Outputs

- IQA results: `{args.iqa_results}`
- Demo timeline: `demo_outputs/scene_000/iqa_status_from_test.jsonl`
""",
        encoding="utf-8",
    )
    print(f"IQA report: {out}")


if __name__ == "__main__":
    main()
