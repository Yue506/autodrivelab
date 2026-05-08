#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "dms_module"))

from dms_module.core_perception import PerceptionResult
from dms_module.event_mapper import map_dms_event


SCENARIOS = {
    "normal": ("DRIVER_NORMAL", 0),
    "eyeclosed": ("DRIVER_EYES_CLOSED", 3),
    "yawn": ("DRIVER_YAWNING", 2),
    "smoke": ("DRIVER_SMOKING", 2),
    "calling": ("DRIVER_CALLING", 3),
}


def infer_scenario(path: Path) -> str:
    name = path.stem.lower()
    for key in SCENARIOS:
        if key in name:
            return key
    if "all" in name:
        return "all"
    return "normal"


def scenario_for_frame(base: str, frame_index: int, total_frames: int) -> str:
    if base != "all":
        return base
    ratio = frame_index / max(total_frames - 1, 1)
    if ratio < 0.18:
        return "normal"
    if ratio < 0.36:
        return "eyeclosed"
    if ratio < 0.54:
        return "yawn"
    if ratio < 0.72:
        return "smoke"
    return "calling"


def perception_from_scenario(scenario: str) -> PerceptionResult:
    result = PerceptionResult(valid=True)
    if scenario == "eyeclosed":
        result.eyes_closed = True
        result.eye_closure_ratio = 0.86
        result.fatigue_confidence = 0.94
    elif scenario == "yawn":
        result.yawning = True
        result.mouth_open_ratio = 0.82
        result.yawning_confidence = 0.91
    elif scenario == "smoke":
        result.smoking = True
        result.smoking_confidence = 0.90
    elif scenario == "calling":
        result.phone_calling = True
        result.phone_confidence = 0.93
    return result


def color_for_level(level: int) -> tuple[int, int, int]:
    return {
        0: (64, 190, 90),
        1: (70, 210, 210),
        2: (0, 165, 255),
        3: (0, 80, 255),
    }.get(int(level), (0, 0, 255))


def put_text(frame, text: str, xy: tuple[int, int], scale=0.7, color=(245, 248, 252), thickness=2):
    cv2.putText(frame, text, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def draw_overlay(frame, video_name: str, scenario: str, event, frame_index: int, total_frames: int):
    h, w = frame.shape[:2]
    level = int(event.danger_level)
    color = color_for_level(level)
    cv2.rectangle(frame, (0, 0), (w, 116), (12, 18, 28), -1)
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), color, 8 if level >= 2 else 3)
    put_text(frame, "AutoDriveLab DMS Test Demo", (24, 36), 0.85, (245, 248, 252), 2)
    put_text(frame, f"{video_name} | frame {frame_index + 1:04d}/{total_frames:04d}", (24, 72), 0.58, (185, 200, 220), 1)
    put_text(frame, f"L{level} {event.event_type}", (24, 106), 0.78, color, 2)

    panel_w = min(520, w - 48)
    x0, y0 = 24, max(136, h - 168)
    cv2.rectangle(frame, (x0, y0), (x0 + panel_w, y0 + 132), (18, 24, 34), -1)
    cv2.rectangle(frame, (x0, y0), (x0 + panel_w, y0 + 132), color, 2)
    lines = [
        f"Scenario: {scenario}",
        f"Fatigue L{event.fatigue_level} | Distraction L{event.distraction_level} | Violation L{event.violation_level}",
        f"Confidence: {event.confidence:.2f} | Valid: {event.valid}",
    ]
    for idx, line in enumerate(lines):
        put_text(frame, line, (x0 + 18, y0 + 34 + idx * 36), 0.56, (235, 240, 246), 1)
    return frame


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def open_video_or_transcode(video_path: Path, out_dir: Path):
    cap = cv2.VideoCapture(str(video_path))
    if cap.isOpened():
        ok, _ = cap.read()
        cap.release()
        if ok:
            return cv2.VideoCapture(str(video_path)), video_path

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(f"Could not decode {video_path}; ffmpeg is not installed for fallback transcoding")

    converted_dir = out_dir / "_converted_inputs"
    converted_dir.mkdir(parents=True, exist_ok=True)
    converted = converted_dir / f"{video_path.stem}.mp4"
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(converted),
    ]
    subprocess.run(cmd, check=True)
    cap = cv2.VideoCapture(str(converted))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open transcoded video: {converted}")
    ok, _ = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Could not read transcoded video: {converted}")
    return cv2.VideoCapture(str(converted)), converted


def process_video(video_path: Path, out_dir: Path, sample_stride: int, max_frames: int | None) -> dict:
    cap, readable_path = open_video_or_transcode(video_path, out_dir)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    scenario_base = infer_scenario(video_path)

    scene_dir = out_dir / video_path.stem
    scene_dir.mkdir(parents=True, exist_ok=True)
    out_video = scene_dir / "dms_visualization.mp4"
    out_jsonl = scene_dir / "dms_status.jsonl"

    writer = cv2.VideoWriter(str(out_video), cv2.VideoWriter_fourcc(*"mp4v"), max(1.0, fps / max(1, sample_stride)), (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {out_video}")

    rows = []
    event_counts: Counter[str] = Counter()
    level_counts: Counter[int] = Counter()
    frame_index = 0
    written = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % sample_stride != 0:
            frame_index += 1
            continue
        if max_frames is not None and written >= max_frames:
            break

        scenario = scenario_for_frame(scenario_base, frame_index, total_frames or frame_index + 1)
        perception = perception_from_scenario(scenario)
        event = map_dms_event(perception)
        row = {
            "video": video_path.name,
            "frame_index": frame_index,
            "scenario": scenario,
            "event": asdict(event),
            "perception": asdict(perception),
        }
        rows.append(row)
        event_counts[event.event_type] += 1
        level_counts[int(event.danger_level)] += 1
        writer.write(draw_overlay(frame, video_path.name, scenario, event, frame_index, total_frames or frame_index + 1))
        written += 1
        frame_index += 1

    cap.release()
    writer.release()
    write_jsonl(out_jsonl, rows)

    return {
        "video": video_path.name,
        "scenario": scenario_base,
        "input_frames": total_frames,
        "processed_frames": written,
        "fps": fps,
        "decoded_input": readable_path.as_posix(),
        "max_level": max(level_counts.keys()) if level_counts else 0,
        "event_counts": dict(event_counts),
        "level_counts": {str(k): v for k, v in sorted(level_counts.items())},
        "status_jsonl": out_jsonl.as_posix(),
        "visualization": out_video.as_posix(),
    }


def write_summary(out_dir: Path, summaries: list[dict]) -> None:
    lines = [
        "# DMS Test Demo Report",
        "",
        "This report is generated from the local DMS test videos. The demo uses the existing `PerceptionResult -> DmsEvent` mapping and the filename-level test labels to produce reproducible visualization videos for defense/demo review.",
        "",
        "| Video | Scenario | Processed frames | Max level | Dominant events | Visualization |",
        "|---|---|---:|---:|---|---|",
    ]
    for item in summaries:
        events = ", ".join(f"{k}:{v}" for k, v in item["event_counts"].items())
        rel_video = Path(item["visualization"]).relative_to(out_dir)
        lines.append(
            f"| `{item['video']}` | `{item['scenario']}` | {item['processed_frames']} | {item['max_level']} | {events} | [{rel_video.as_posix()}]({rel_video.as_posix()}) |"
        )
    lines.append("")
    lines.append("Generated outputs:")
    lines.append("")
    lines.append("- `dms_status.jsonl`: frame-level DMS event records.")
    lines.append("- `dms_visualization.mp4`: source video with DMS risk overlay.")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="data/DMS_test_data")
    parser.add_argument("--output-dir", default="demo_outputs/dms_test_demo")
    parser.add_argument("--sample-stride", type=int, default=3)
    parser.add_argument("--max-frames", type=int)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    videos = sorted([*input_dir.glob("*.MOV"), *input_dir.glob("*.mp4"), *input_dir.glob("*.mov")])
    if not videos:
        raise FileNotFoundError(f"No videos found in {input_dir}")

    summaries = [process_video(path, out_dir, max(1, args.sample_stride), args.max_frames) for path in videos]
    write_jsonl(out_dir / "summary.jsonl", summaries)
    write_summary(out_dir, summaries)
    print(f"DMS demo videos: {len(summaries)}")
    print(f"Output: {out_dir}")
    for item in summaries:
        print(f"- {item['video']}: max L{item['max_level']} -> {item['visualization']}")


if __name__ == "__main__":
    main()
