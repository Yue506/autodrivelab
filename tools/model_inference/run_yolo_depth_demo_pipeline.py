#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from demo.offline_mvp import read_jsonl, run_arbitration, write_jsonl  # noqa: E402


COCO_TO_ADAS = {
    "person": "pedestrian",
    "bicycle": "bicycle",
    "car": "car",
    "motorcycle": "motorcycle",
    "bus": "bus",
    "truck": "truck",
}
CLASS_HEIGHT_M = {
    "pedestrian": 1.7,
    "bicycle": 1.4,
    "motorcycle": 1.4,
    "car": 1.55,
    "bus": 3.0,
    "truck": 3.0,
}
CLASS_SIZE = {
    "pedestrian": [0.7, 0.7, 1.7],
    "bicycle": [0.8, 1.8, 1.4],
    "motorcycle": [0.9, 2.1, 1.4],
    "car": [1.8, 4.4, 1.6],
    "bus": [2.6, 11.0, 3.2],
    "truck": [2.6, 8.0, 3.0],
}


@dataclass
class DepthRuntime:
    processor: object | None
    model: object | None
    model_name: str
    active: bool
    note: str


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def load_yolo(requested: str):
    from ultralytics import YOLO

    candidates = [requested, "yolo26s.pt", "yolo26n.pt", "yolo11s.pt", "yolov8s.pt"]
    errors: list[str] = []
    for name in dict.fromkeys(candidates):
        try:
            return YOLO(name), name, errors
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError("No YOLO model could be loaded:\n" + "\n".join(errors))


def load_depth(model_name: str, device: str, allow_fallback: bool) -> DepthRuntime:
    try:
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        processor = AutoImageProcessor.from_pretrained(model_name)
        model = AutoModelForDepthEstimation.from_pretrained(model_name).to(device)
        model.eval()
        return DepthRuntime(processor, model, model_name, True, "Depth Anything active")
    except Exception as exc:
        if not allow_fallback:
            raise
        return DepthRuntime(None, None, model_name, False, f"Depth Anything unavailable, bbox-depth fallback used: {exc}")


@torch.inference_mode()
def predict_depth(image_bgr: np.ndarray, runtime: DepthRuntime, device: str) -> np.ndarray | None:
    if not runtime.active or runtime.processor is None or runtime.model is None:
        return None
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(image_rgb)
    inputs = runtime.processor(images=pil, return_tensors="pt").to(device)
    outputs = runtime.model(**inputs)
    depth = outputs.predicted_depth
    depth = torch.nn.functional.interpolate(
        depth.unsqueeze(1),
        size=image_bgr.shape[:2],
        mode="bicubic",
        align_corners=False,
    ).squeeze()
    arr = depth.detach().float().cpu().numpy()
    p05, p95 = np.percentile(arr, [5, 95])
    if p95 <= p05:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - p05) / (p95 - p05), 0.0, 1.0).astype(np.float32)


def depth_signal(depth_map: np.ndarray | None, xyxy: list[float]) -> float | None:
    if depth_map is None:
        return None
    h, w = depth_map.shape[:2]
    x1, y1, x2, y2 = [int(round(v)) for v in xyxy]
    x1, x2 = sorted((clamp(x1, 0, w - 1), clamp(x2, 0, w - 1)))
    y1, y2 = sorted((clamp(y1, 0, h - 1), clamp(y2, 0, h - 1)))
    bw, bh = max(1, x2 - x1), max(1, y2 - y1)
    cx1 = int(x1 + 0.30 * bw)
    cx2 = int(x1 + 0.70 * bw)
    cy1 = int(y1 + 0.45 * bh)
    cy2 = int(y1 + 0.85 * bh)
    crop = depth_map[cy1:max(cy2, cy1 + 1), cx1:max(cx2, cx1 + 1)]
    if crop.size == 0:
        return None
    return float(np.median(crop))


def estimate_distance(class_name: str, xyxy: list[float], image_shape: tuple[int, int, int], depth_value: float | None) -> float:
    img_h, img_w = image_shape[:2]
    x1, y1, x2, y2 = xyxy
    box_h = max(4.0, y2 - y1)
    focal_px = 0.92 * img_w
    class_h = CLASS_HEIGHT_M.get(class_name, 1.6)
    bbox_m = focal_px * class_h / box_h
    if depth_value is None:
        return clamp(bbox_m, 2.0, 80.0)
    depth_m = 2.0 + (1.0 - clamp(depth_value, 0.0, 1.0)) * 58.0
    return clamp(0.70 * bbox_m + 0.30 * depth_m, 2.0, 80.0)


def lateral_offset(x_center: float, image_width: int, distance: float) -> float:
    half_fov = math.radians(35.0)
    angle = (x_center / max(image_width, 1) - 0.5) * 2.0 * half_fov
    return clamp(math.tan(angle) * distance, -25.0, 25.0)


def risk_from_ttc(ttc: float | None) -> tuple[int, str, str]:
    if ttc is None or not math.isfinite(ttc):
        return 0, "NO_FRONT_RISK", "模型未检测到满足 TTC 阈值的前向风险"
    if ttc < 3.0:
        return 4, "FCW_EMERGENCY", "TTC 小于 3 秒，触发前向紧急碰撞风险"
    if ttc <= 5.0:
        return 3, "FCW_POTENTIAL", "TTC 在 3 到 5 秒内，触发前向潜在碰撞风险"
    return 0, "NO_FRONT_RISK", "模型前向目标 TTC 未达到告警阈值"


def track_key(class_name: str, lateral_m: float) -> str:
    lateral_bin = round(lateral_m / 2.0) * 2
    return f"{class_name}:{lateral_bin:+.0f}m"


def estimate_ttc_for_objects(frame: dict, objects: list[dict], prev_distance_by_track: dict[str, tuple[int, float]]) -> None:
    for obj in objects:
        if not obj.get("is_front_candidate"):
            obj["relative_speed"] = 0.0
            obj["ttc"] = None
            obj["risk_level"] = 0
            obj["is_front_risk"] = False
            continue
        key = obj["track_key"]
        prev = prev_distance_by_track.get(key)
        relative_speed = 0.0
        ttc = None
        if prev:
            dt = max((int(frame["timestamp"]) - prev[0]) / 1e6, 1e-3)
            relative_speed = (prev[1] - float(obj["distance"])) / dt
            if relative_speed > 0.1:
                ttc = float(obj["distance"]) / relative_speed
        prev_distance_by_track[key] = (int(frame["timestamp"]), float(obj["distance"]))
        level, _, _ = risk_from_ttc(ttc)
        obj["relative_speed"] = float(relative_speed)
        obj["ttc"] = ttc
        obj["risk_level"] = int(level)
        obj["is_front_risk"] = level > 0


def status_from_objects(frame: dict, objects: list[dict]) -> dict:
    front = [o for o in objects if o["is_front_risk"]]
    target = max(front, key=lambda row: (row["risk_level"], -(row["ttc"] or float("inf"))), default=None)
    if target is None:
        _, event_type, description = risk_from_ttc(None)
        return {
            "frame_index": frame["frame_index"],
            "timestamp": frame["timestamp"],
            "adas_level": 0,
            "event_type": event_type,
            "event_description": description,
            "target_object_id": None,
            "front_object_distance": None,
            "relative_speed": 0.0,
            "ttc": None,
            "confidence": 0.0,
            "valid": True,
        }
    level, event_type, description = risk_from_ttc(target.get("ttc"))
    return {
        "frame_index": frame["frame_index"],
        "timestamp": frame["timestamp"],
        "adas_level": level,
        "event_type": event_type,
        "event_description": description,
        "target_object_id": target["object_id"],
        "front_object_distance": float(target["distance"]),
        "relative_speed": float(target["relative_speed"]),
        "ttc": float(target["ttc"]) if target.get("ttc") is not None else None,
        "confidence": float(target["confidence"]),
        "valid": True,
    }


def run_detector(args: argparse.Namespace) -> dict:
    scene_dir = Path(args.scene_dir)
    cache_dir = scene_dir / "demo_cache"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = read_jsonl(cache_dir / "frames.jsonl")
    device = "cuda:0" if torch.cuda.is_available() and not args.cpu else "cpu"
    yolo, yolo_name, yolo_errors = load_yolo(args.yolo_model)
    depth = load_depth(args.depth_model, device, args.allow_depth_fallback)

    object_rows: list[dict] = []
    status_rows: list[dict] = []
    prediction_rows: list[dict] = []
    detections_total = 0
    prev_distance_by_track: dict[str, tuple[int, float]] = {}
    for frame in frames:
        image_path = cache_dir / frame["camera_images"].get(args.camera, "")
        image = cv2.imread(str(image_path))
        if image is None:
            object_rows.append({"frame_index": frame["frame_index"], "timestamp": frame["timestamp"], "objects": []})
            status_rows.append(status_from_objects(frame, []))
            continue
        depth_map = predict_depth(image, depth, device)
        result = yolo.predict(image, conf=args.conf, imgsz=args.imgsz, device=0 if device.startswith("cuda") else "cpu", verbose=False)[0]
        objects: list[dict] = []
        names = result.names
        boxes = result.boxes
        for det_idx, box in enumerate(boxes):
            cls_name = names[int(box.cls.item())]
            if cls_name not in COCO_TO_ADAS:
                continue
            xyxy = [float(v) for v in box.xyxy[0].tolist()]
            class_name = COCO_TO_ADAS[cls_name]
            cx = 0.5 * (xyxy[0] + xyxy[2])
            dval = depth_signal(depth_map, xyxy)
            distance = estimate_distance(class_name, xyxy, image.shape, dval)
            y = lateral_offset(cx, image.shape[1], distance)
            is_front_candidate = abs(y) <= 3.8
            obj = {
                "object_id": f"pred_{frame['frame_index']:04d}_{det_idx:02d}",
                "class_name": class_name,
                "x": float(distance),
                "y": float(y),
                "z": CLASS_HEIGHT_M.get(class_name, 1.6) / 2.0,
                "distance": float(math.hypot(distance, y)),
                "is_front_candidate": bool(is_front_candidate),
                "is_front_risk": False,
                "risk_level": 0,
                "size": CLASS_SIZE.get(class_name, [1.0, 1.0, 1.0]),
                "confidence": float(box.conf.item()),
                "bbox_xyxy": xyxy,
                "depth_signal": dval,
                "source_camera": args.camera,
                "track_key": track_key(class_name, y),
                "relative_speed": 0.0,
                "ttc": None,
            }
            objects.append(obj)
        estimate_ttc_for_objects(frame, objects, prev_distance_by_track)
        detections_total += len(objects)
        objects.sort(key=lambda row: row["distance"])
        object_rows.append({"frame_index": frame["frame_index"], "timestamp": frame["timestamp"], "objects": objects})
        status_rows.append(status_from_objects(frame, objects))
        prediction_rows.append(
            {
                "frame_index": frame["frame_index"],
                "timestamp": frame["timestamp"],
                "image": str(image_path),
                "detections": objects,
            }
        )

    write_jsonl(out_dir / "yolo_depth_predictions.jsonl", prediction_rows)
    write_jsonl(out_dir / "pred_adas_objects.jsonl", object_rows)
    write_jsonl(out_dir / "pred_adas_status.jsonl", status_rows)
    return {
        "device": device,
        "yolo_model": yolo_name,
        "yolo_errors": yolo_errors,
        "depth_model": depth.model_name,
        "depth_active": depth.active,
        "depth_note": depth.note,
        "frames": len(frames),
        "detections": detections_total,
        "max_adas_level": max((row["adas_level"] for row in status_rows), default=0),
    }


def write_report(out_dir: Path, stats: dict, fusion_path: Path, video_path: Path) -> None:
    fusion = read_jsonl(fusion_path)
    report = f"""# YOLO + Depth Anything Model Demo

## Flow

`YOLO object detection -> Depth Anything monocular depth -> pred_adas_objects.jsonl -> pred_adas_status.jsonl -> fusion -> final_demo_model.mp4`

## Runtime

- Device: `{stats['device']}`
- YOLO model loaded: `{stats['yolo_model']}`
- Depth model requested: `{stats['depth_model']}`
- Depth status: `{stats['depth_note']}`
- Frames: {stats['frames']}
- Model detections: {stats['detections']}
- Max ADAS level: {stats['max_adas_level']}
- Max fusion level: {max((row['unified_risk_level'] for row in fusion), default=0)}

## Outputs

- `yolo_depth_predictions.jsonl`
- `pred_adas_objects.jsonl`
- `pred_adas_status.jsonl`
- `{fusion_path.name}`
- `{video_path.name}`

## Notes

Distances are model-estimated monocular distances calibrated for the offline demo display. The JSONL files are generated from model inference outputs and are intended to replace the ADAS/TTC demo input stream.
"""
    if stats["yolo_errors"]:
        report += "\n## YOLO Fallback Attempts\n\n" + "\n".join(f"- `{err}`" for err in stats["yolo_errors"][:4]) + "\n"
    (out_dir / "model_inference_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-dir", default="demo_outputs/scene_000")
    parser.add_argument("--out-dir", default="model_inference_outputs")
    parser.add_argument("--camera", default="CAM_FRONT")
    parser.add_argument("--yolo-model", default="yolo26s.pt")
    parser.add_argument("--depth-model", default="depth-anything/Depth-Anything-V2-Small-hf")
    parser.add_argument("--conf", type=float, default=0.20)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--fps", type=int, default=5)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--allow-depth-fallback", action="store_true", default=True)
    args = parser.parse_args()

    scene_dir = Path(args.scene_dir)
    out_dir = Path(args.out_dir)
    stats = run_detector(args)
    iqa = scene_dir / "iqa_status_from_test.jsonl"
    if not iqa.exists():
        iqa = scene_dir / "iqa_status.jsonl"
    fusion_path = out_dir / "fusion_status_model.jsonl"
    run_arbitration(
        argparse.Namespace(
            adas=out_dir / "pred_adas_status.jsonl",
            dms=scene_dir / "dms_status.jsonl",
            iqa=iqa,
            out=fusion_path,
        )
    )
    video_path = out_dir / "final_demo_model.mp4"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "render_final_demo.py"),
            "--scene-dir",
            str(scene_dir),
            "--adas-objects",
            str(out_dir / "pred_adas_objects.jsonl"),
            "--adas-status",
            str(out_dir / "pred_adas_status.jsonl"),
            "--iqa-status",
            str(iqa),
            "--fusion-status",
            str(fusion_path),
            "--source-label",
            f"{stats['yolo_model']} + Depth Anything model estimates",
            "--fps",
            str(args.fps),
            "--out",
            str(video_path),
        ],
        check=True,
    )
    write_report(out_dir, stats, fusion_path, video_path)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"Report: {out_dir / 'model_inference_report.md'}")


if __name__ == "__main__":
    main()
