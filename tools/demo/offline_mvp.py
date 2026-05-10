from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import yaml

try:
    from demo.bev_render import draw_bev_scene
except ModuleNotFoundError:
    from .bev_render import draw_bev_scene


CAMERAS = [
    "CAM_FRONT",
    "CAM_FRONT_LEFT",
    "CAM_FRONT_RIGHT",
    "CAM_BACK",
    "CAM_BACK_LEFT",
    "CAM_BACK_RIGHT",
]

RISK_CATEGORIES = {
    "vehicle.car": "car",
    "vehicle.truck": "truck",
    "vehicle.bus": "bus",
    "vehicle.motorcycle": "motorcycle",
    "vehicle.bicycle": "bicycle",
    "human.pedestrian.adult": "pedestrian",
    "human.pedestrian.child": "pedestrian",
    "human.pedestrian.construction_worker": "pedestrian",
    "human.pedestrian.police_officer": "pedestrian",
}


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def table_index(rows: list[dict]) -> dict[str, dict]:
    return {row["token"]: row for row in rows}


def normalize_dataroot(path: str | Path) -> Path:
    root = Path(path).expanduser()
    if root.exists():
        return root
    alt = Path(str(root).replace("nuscense", "nuscenes"))
    if alt.exists():
        return alt
    return root


def quat_conjugate(q: list[float]) -> list[float]:
    return [q[0], -q[1], -q[2], -q[3]]


def quat_multiply(a: list[float], b: list[float]) -> list[float]:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return [
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ]


def rotate_vector(q: list[float], v: list[float]) -> list[float]:
    rotated = quat_multiply(quat_multiply(q, [0.0, *v]), quat_conjugate(q))
    return rotated[1:]


def global_to_ego(global_xyz: list[float], ego_pose: dict) -> list[float]:
    delta = [float(global_xyz[i]) - float(ego_pose["translation"][i]) for i in range(3)]
    return rotate_vector(quat_conjugate(ego_pose["rotation"]), delta)


def load_nuscenes_tables(dataroot: Path, version: str) -> dict[str, object]:
    version_dir = dataroot / version
    names = [
        "scene",
        "sample",
        "sample_data",
        "sample_annotation",
        "instance",
        "category",
        "ego_pose",
        "calibrated_sensor",
        "sensor",
    ]
    tables = {name: read_json(version_dir / f"{name}.json") for name in names}
    for name in names:
        tables[f"{name}_by_token"] = table_index(tables[name])
    sample_data_by_sample_channel: dict[tuple[str, str], dict] = {}
    for row in tables["sample_data"]:
        calibrated = tables["calibrated_sensor_by_token"][row["calibrated_sensor_token"]]
        sensor = tables["sensor_by_token"][calibrated["sensor_token"]]
        channel = sensor["channel"]
        if channel in CAMERAS and row.get("is_key_frame", False):
            sample_data_by_sample_channel[(row["sample_token"], channel)] = row
    annotations_by_sample: dict[str, list[dict]] = {}
    for row in tables["sample_annotation"]:
        annotations_by_sample.setdefault(row["sample_token"], []).append(row)
    tables["sample_data_by_sample_channel"] = sample_data_by_sample_channel
    tables["annotations_by_sample"] = annotations_by_sample
    return tables


def annotation_category_name(tables: dict[str, object], ann: dict) -> str:
    instance = tables["instance_by_token"].get(ann.get("instance_token", ""), {})
    category = tables["category_by_token"].get(instance.get("category_token", ""), {})
    return category.get("name", "unknown")


def iter_scene_samples(scene: dict, sample_by_token: dict[str, dict], max_frames: int | None):
    token = scene["first_sample_token"]
    count = 0
    while token and (max_frames is None or count < max_frames):
        sample = sample_by_token[token]
        yield sample
        count += 1
        token = sample.get("next", "")


def sample_camera_data(sample: dict, sample_data_by_sample_channel: dict[tuple[str, str], dict]) -> dict[str, dict]:
    return {
        camera: sample_data_by_sample_channel[(sample["token"], camera)]
        for camera in CAMERAS
        if (sample["token"], camera) in sample_data_by_sample_channel
    }


def scene_min_front_distance(tables: dict[str, object], scene: dict, max_frames: int) -> float:
    best = float("inf")
    for sample in iter_scene_samples(scene, tables["sample_by_token"], max_frames):
        cam_data = sample_camera_data(sample, tables["sample_data_by_sample_channel"])
        if "CAM_FRONT" not in cam_data:
            continue
        ego_pose = tables["ego_pose_by_token"][cam_data["CAM_FRONT"]["ego_pose_token"]]
        for ann in tables["annotations_by_sample"].get(sample["token"], []):
            if annotation_category_name(tables, ann) not in RISK_CATEGORIES:
                continue
            x, y, _ = global_to_ego(ann["translation"], ego_pose)
            if x > 0.0 and abs(y) < 3.5:
                best = min(best, math.hypot(x, y))
    return best


def select_scene(tables: dict[str, object], scene_index: int | None, scene_name: str | None, max_frames: int, auto_select: bool):
    scenes = tables["scene"]
    if scene_name:
        for idx, scene in enumerate(scenes):
            if scene["name"] == scene_name:
                return idx, scene
        raise ValueError(f"Scene name not found: {scene_name}")
    if auto_select:
        scored = [(scene_min_front_distance(tables, scene, max_frames), idx, scene) for idx, scene in enumerate(scenes)]
        scored.sort(key=lambda item: item[0])
        return scored[0][1], scored[0][2]
    idx = int(scene_index or 0)
    return idx, scenes[idx]


def export_cache(args: argparse.Namespace) -> None:
    dataroot = normalize_dataroot(args.dataroot)
    tables = load_nuscenes_tables(dataroot, args.version)
    scene_index, scene = select_scene(
        tables,
        args.scene_index,
        args.scene_name,
        args.max_frames,
        args.auto_select_scene,
    )
    out = Path(args.out)
    if out.exists() and args.overwrite:
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    frames = []
    gt_rows = []
    copied = 0
    for frame_index, sample in enumerate(iter_scene_samples(scene, tables["sample_by_token"], args.max_frames)):
        cam_data = sample_camera_data(sample, tables["sample_data_by_sample_channel"])
        if "CAM_FRONT" not in cam_data:
            continue
        front_pose = tables["ego_pose_by_token"][cam_data["CAM_FRONT"]["ego_pose_token"]]
        camera_images = {}
        for camera in CAMERAS:
            if camera not in cam_data:
                continue
            src = dataroot / cam_data[camera]["filename"]
            rel = Path("images") / camera / f"{frame_index:06d}{src.suffix.lower()}"
            if args.copy_images:
                dst = out / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
                camera_images[camera] = rel.as_posix()
            else:
                camera_images[camera] = str(src)
        objects = []
        for ann in tables["annotations_by_sample"].get(sample["token"], []):
            ego_xyz = global_to_ego(ann["translation"], front_pose)
            objects.append(
                {
                    "instance_token": ann.get("instance_token", ""),
                    "sample_annotation_token": ann["token"],
                    "category_name": annotation_category_name(tables, ann),
                    "translation_global": ann["translation"],
                    "translation_ego": ego_xyz,
                    "size": ann.get("size", [0.0, 0.0, 0.0]),
                    "rotation": ann.get("rotation", [1.0, 0.0, 0.0, 0.0]),
                    "num_lidar_pts": ann.get("num_lidar_pts", 0),
                    "num_radar_pts": ann.get("num_radar_pts", 0),
                }
            )
        frames.append(
            {
                "frame_index": frame_index,
                "timestamp": sample["timestamp"],
                "sample_token": sample["token"],
                "scene_token": scene["token"],
                "camera_images": camera_images,
                "ego_pose": {
                    "translation": front_pose["translation"],
                    "rotation": front_pose["rotation"],
                },
            }
        )
        gt_rows.append({"frame_index": frame_index, "timestamp": sample["timestamp"], "objects": objects})

    write_jsonl(out / "frames.jsonl", frames)
    write_jsonl(out / "gt_objects.jsonl", gt_rows)
    write_json(
        out / "meta.json",
        {
            "dataroot": str(dataroot),
            "version": args.version,
            "scene_index": scene_index,
            "scene_name": scene["name"],
            "scene_token": scene["token"],
            "description": scene.get("description", ""),
            "frames": len(frames),
            "copy_images": bool(args.copy_images),
        },
    )
    print(f"Loaded scene: {scene['name']} ({scene_index})")
    print(f"Exported frames: {len(frames)}")
    print(f"Exported camera images: {copied if args.copy_images else 'referenced'}")
    print(f"Exported gt object records: {len(gt_rows)}")
    print(f"Output: {out}")


def category_to_class(category: str) -> str:
    return RISK_CATEGORIES.get(category, "unknown")


def adas_level_from_ttc(ttc: float | None) -> tuple[int, str, str]:
    if ttc is None or not math.isfinite(ttc):
        return 0, "ADAS_NORMAL", "前方无明显碰撞风险"
    if ttc < 3.0:
        return 4, "FCW_EMERGENCY", "TTC 小于 3 秒，触发前向紧急碰撞风险"
    if ttc <= 5.0:
        return 3, "FCW_POTENTIAL", "TTC 在 3 到 5 秒内，触发前向潜在碰撞风险"
    return 0, "ADAS_NORMAL", "前方目标 TTC 未达到告警阈值"


def compute_ttc(
    object_id: str,
    timestamp: int,
    distance: float,
    prev_distance_by_id: dict[str, tuple[int, float]],
) -> tuple[float | None, float]:
    prev = prev_distance_by_id.get(object_id)
    relative_speed = 0.0
    ttc = None
    if prev:
        dt = max((timestamp - prev[0]) / 1e6, 1e-3)
        relative_speed = (prev[1] - distance) / dt
        if relative_speed > 0.1:
            ttc = distance / relative_speed
    prev_distance_by_id[object_id] = (timestamp, distance)
    return ttc, relative_speed


def generate_adas(args: argparse.Namespace) -> None:
    cache = Path(args.cache)
    frames = read_jsonl(cache / "frames.jsonl")
    gt_rows = read_jsonl(cache / "gt_objects.jsonl")
    out_dir = Path(args.out_dir)
    status_rows = []
    object_rows = []
    prev_distance_by_id: dict[str, tuple[int, float]] = {}
    for frame, gt in zip(frames, gt_rows, strict=True):
        objects = []
        best = None
        for obj in gt["objects"]:
            class_name = category_to_class(obj["category_name"])
            x, y, z = [float(v) for v in obj["translation_ego"]]
            distance = math.hypot(x, y)
            is_front = class_name != "unknown" and x > 0.0 and abs(y) < args.front_y_abs_max
            object_id = obj["instance_token"] or obj["sample_annotation_token"]
            ttc, relative_speed = compute_ttc(object_id, frame["timestamp"], distance, prev_distance_by_id) if is_front else (None, 0.0)
            risk_level, _, _ = adas_level_from_ttc(ttc)
            row = {
                "object_id": object_id,
                "class_name": class_name,
                "x": x,
                "y": y,
                "z": z,
                "distance": distance,
                "is_front_risk": bool(is_front and risk_level > 0),
                "risk_level": risk_level if is_front else 0,
                "relative_speed": relative_speed if is_front else 0.0,
                "ttc": ttc if is_front else None,
                "size": obj["size"],
            }
            objects.append(row)
            if row["is_front_risk"] and (
                best is None
                or row["risk_level"] > best["risk_level"]
                or (row["risk_level"] == best["risk_level"] and (row["ttc"] or float("inf")) < (best["ttc"] or float("inf")))
            ):
                best = row
        level = 0
        event_type = "ADAS_NORMAL"
        description = "前方无明显碰撞风险"
        ttc = None
        relative_speed = 0.0
        if best is not None:
            ttc = best["ttc"]
            relative_speed = best["relative_speed"]
            level, event_type, description = adas_level_from_ttc(ttc)
        status_rows.append(
            {
                "frame_index": frame["frame_index"],
                "timestamp": frame["timestamp"],
                "adas_level": level,
                "event_type": event_type,
                "event_description": description,
                "target_object_id": best["object_id"] if best else None,
                "front_object_distance": best["distance"] if best else None,
                "relative_speed": relative_speed,
                "ttc": ttc,
                "confidence": 1.0,
                "valid": True,
            }
        )
        object_rows.append({"frame_index": frame["frame_index"], "timestamp": frame["timestamp"], "objects": objects})
    write_jsonl(out_dir / "adas_status.jsonl", status_rows)
    write_jsonl(out_dir / "adas_objects.jsonl", object_rows)
    print(f"ADAS status: {out_dir / 'adas_status.jsonl'}")
    print(f"ADAS objects: {out_dir / 'adas_objects.jsonl'}")
    print(f"Max ADAS level: {max(row['adas_level'] for row in status_rows) if status_rows else 0}")


def timeline_value(index: int, total: int, segments: list[dict]) -> dict:
    ratio = index / max(total, 1)
    for segment in segments:
        if float(segment["start_ratio"]) <= ratio < float(segment["end_ratio"]):
            return segment
    return segments[-1]


def generate_dms(args: argparse.Namespace) -> None:
    frames = read_jsonl(Path(args.frames))
    timeline = [
        {"start_ratio": 0.00, "end_ratio": 0.25, "danger_level": 0, "event_type": "DRIVER_NORMAL", "event_description": "驾驶员状态正常"},
        {"start_ratio": 0.25, "end_ratio": 0.45, "danger_level": 2, "event_type": "DRIVER_YAWNING", "event_description": "驾驶员打哈欠，存在疲劳风险"},
        {"start_ratio": 0.45, "end_ratio": 0.70, "danger_level": 3, "event_type": "DRIVER_EYES_CLOSED", "event_description": "驾驶员闭眼危险"},
        {"start_ratio": 0.70, "end_ratio": 1.00, "danger_level": 0, "event_type": "DRIVER_NORMAL", "event_description": "驾驶员状态恢复正常"},
    ]
    rows = []
    for idx, frame in enumerate(frames):
        seg = timeline_value(idx, len(frames), timeline)
        level = int(seg["danger_level"])
        rows.append(
            {
                "frame_index": frame["frame_index"],
                "timestamp": frame["timestamp"],
                "danger_level": level,
                "event_type": seg["event_type"],
                "event_description": seg["event_description"],
                "fatigue_level": level if level > 0 else 0,
                "distraction_level": 0,
                "violation_level": 0,
                "confidence": 1.0,
                "valid": True,
            }
        )
    write_jsonl(Path(args.out), rows)
    print(f"DMS status: {args.out}")


def default_camera_states(soiled_front: bool) -> dict[str, dict]:
    states = {}
    for camera in CAMERAS:
        soiled = bool(soiled_front and camera == "CAM_FRONT")
        states[camera] = {
            "quality_state": "soiling" if soiled else "normal",
            "soiling_score": 0.92 if soiled else 0.03,
            "is_soiled": soiled,
            "is_critical": camera in {"CAM_FRONT", "CAM_FRONT_LEFT", "CAM_FRONT_RIGHT"},
        }
    return states


def generate_iqa(args: argparse.Namespace) -> None:
    frames = read_jsonl(Path(args.frames))
    if args.iqa_source == "offline_model_result":
        if not args.model_result:
            raise ValueError("--model-result is required for offline_model_result")
        rows = read_jsonl(Path(args.model_result))
        write_jsonl(Path(args.out), rows)
        print(f"IQA status copied from model result: {args.out}")
        return
    rows = []
    for idx, frame in enumerate(frames):
        ratio = idx / max(len(frames), 1)
        states = default_camera_states(0.50 <= ratio < 0.75)
        soiled = [name for name, state in states.items() if state["is_soiled"]]
        critical = any(name in {"CAM_FRONT", "CAM_FRONT_LEFT", "CAM_FRONT_RIGHT"} for name in soiled)
        rows.append(
            {
                "frame_index": frame["frame_index"],
                "timestamp": frame["timestamp"],
                "iqa_level": 3 if critical else (1 if soiled else 0),
                "soiled_camera_count": len(soiled),
                "soiled_cameras": soiled,
                "critical_camera_soiled": critical,
                "camera_states": states,
                "confidence": 0.92 if soiled else 1.0,
                "valid": True,
            }
        )
    write_jsonl(Path(args.out), rows)
    print(f"IQA status: {args.out}")


class AttrDict(SimpleNamespace):
    def get(self, key, default=None):
        return getattr(self, key, default)


def to_attr(data):
    if isinstance(data, dict):
        return AttrDict(**{k: to_attr(v) for k, v in data.items()})
    if isinstance(data, list):
        return [to_attr(v) for v in data]
    return data


def iqa_to_attr(row: dict):
    cameras = []
    for name, state in row.get("camera_states", {}).items():
        camera = dict(state)
        camera["camera_name"] = name
        cameras.append(to_attr(camera))
    data = dict(row)
    data["cameras"] = cameras
    return to_attr(data)


def run_arbitration(args: argparse.Namespace) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "arbitration_module"))
    from arbitration_module.event_builder import build_fusion_events
    from arbitration_module.iqa_gate import apply_iqa_gate, compute_iqa_level
    from arbitration_module.risk_matrix import fuse_adas_dms
    from arbitration_module.time_sync_buffer import SourceStatusData

    adas_rows = read_jsonl(Path(args.adas))
    dms_rows = read_jsonl(Path(args.dms))
    iqa_rows = read_jsonl(Path(args.iqa))
    config = {
        "soiling_score_threshold": 0.5,
        "critical_cameras": ["CAM_FRONT", "CAM_FRONT_LEFT", "CAM_FRONT_RIGHT"],
        "level1_soiled_count": 1,
        "level2_soiled_count": 2,
        "level3_soiled_count": 3,
        "mark_degraded_from_level": 2,
        "min_level_when_iqa_level2": 2,
        "min_level_when_iqa_level3": 2,
    }
    rows = []
    for adas, dms, iqa in zip(adas_rows, dms_rows, iqa_rows, strict=True):
        adas_msg = to_attr(adas)
        dms_msg = to_attr(dms)
        iqa_msg = iqa_to_attr(iqa)
        status = SourceStatusData(
            adas_valid=bool(adas.get("valid", True)),
            dms_valid=bool(dms.get("valid", True)),
            iqa_valid=bool(iqa.get("valid", True)),
            perception_degraded=False,
            soiled_camera_count=int(iqa.get("soiled_camera_count", 0)),
            soiled_cameras=list(iqa.get("soiled_cameras", [])),
            critical_camera_soiled=bool(iqa.get("critical_camera_soiled", False)),
        )
        base = fuse_adas_dms(adas["adas_level"], dms["danger_level"], status.adas_valid, status.dms_valid)
        status.iqa_level = compute_iqa_level(iqa_msg, config) if status.iqa_valid else 0
        unified, status.perception_degraded = apply_iqa_gate(base, status.iqa_level, status.iqa_valid, config)
        primary_source, primary_event, primary_description, events, confidence = build_fusion_events(
            adas_msg, dms_msg, iqa_msg, unified, status
        )
        rows.append(
            {
                "frame_index": adas["frame_index"],
                "timestamp": adas["timestamp"],
                "unified_risk_level": int(unified),
                "primary_source": primary_source,
                "primary_event": primary_event,
                "primary_description": primary_description,
                "triggered_events": events,
                "source_status": {
                    "adas_valid": status.adas_valid,
                    "dms_valid": status.dms_valid,
                    "iqa_valid": status.iqa_valid,
                    "perception_degraded": status.perception_degraded,
                    "iqa_level": status.iqa_level,
                    "soiled_camera_count": status.soiled_camera_count,
                    "soiled_cameras": status.soiled_cameras,
                    "critical_camera_soiled": status.critical_camera_soiled,
                },
                "valid": bool(status.adas_valid or status.dms_valid or status.iqa_valid),
                "confidence": float(confidence),
            }
        )
    write_jsonl(Path(args.out), rows)
    print(f"Fusion status: {args.out}")
    print(f"Max fusion level: {max(row['unified_risk_level'] for row in rows) if rows else 0}")
    print(f"Perception degraded frames: {sum(bool(row['source_status']['perception_degraded']) for row in rows)}")


def risk_color(level: int) -> tuple[int, int, int]:
    return [(60, 180, 60), (60, 210, 210), (0, 190, 255), (0, 120, 255), (0, 0, 255)][max(0, min(4, level))]


def put_text(img, text: str, xy: tuple[int, int], scale=0.55, color=(255, 255, 255), thickness=1):
    cv2.putText(img, text, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def draw_bev(canvas, objects: list[dict], fusion_level: int):
    x0, y0, w, h = 30, 390, 760, 300
    draw_bev_scene(
        canvas,
        (x0, y0, w, h),
        objects,
        target_object_id=None,
        border_level=fusion_level,
        title="BEV FSD View",
    )


def draw_risk_panel(canvas, adas, dms, iqa, fusion):
    x0, y0, w, h = 820, 390, 430, 300
    level = int(fusion["unified_risk_level"])
    cv2.rectangle(canvas, (x0, y0), (x0 + w, y0 + h), (18, 22, 29), -1)
    cv2.rectangle(canvas, (x0, y0), (x0 + w, y0 + h), risk_color(level), 3)
    put_text(canvas, f"FUSION LEVEL {level}", (x0 + 18, y0 + 36), 0.9, risk_color(level), 2)
    lines = [
        f"Primary: {fusion['primary_event']}",
        f"ADAS L{adas['adas_level']}: {adas['event_type']}",
        f"DMS  L{dms['danger_level']}: {dms['event_type']}",
        f"IQA  L{iqa['iqa_level']}: {','.join(iqa.get('soiled_cameras', [])) or 'normal'}",
        f"Perception: {'DEGRADED' if fusion['source_status']['perception_degraded'] else 'OK'}",
    ]
    for i, line in enumerate(lines):
        put_text(canvas, line[:48], (x0 + 18, y0 + 78 + i * 34), 0.56, (235, 238, 242), 1)


def render_video(args: argparse.Namespace) -> None:
    cache = Path(args.cache)
    frames = read_jsonl(cache / "frames.jsonl")
    adas_objects = read_jsonl(Path(args.adas_objects))
    adas_rows = read_jsonl(Path(args.adas_status))
    dms_rows = read_jsonl(Path(args.dms_status))
    iqa_rows = read_jsonl(Path(args.iqa_status))
    fusion_rows = read_jsonl(Path(args.fusion_status))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), float(args.fps), (1280, 720))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {out}")
    for frame, objects, adas, dms, iqa, fusion in zip(frames, adas_objects, adas_rows, dms_rows, iqa_rows, fusion_rows, strict=True):
        canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
        front_path = cache / frame["camera_images"].get("CAM_FRONT", "")
        img = cv2.imread(str(front_path))
        if img is None:
            img = np.zeros((360, 760, 3), dtype=np.uint8)
        img = cv2.resize(img, (760, 360))
        canvas[20:380, 30:790] = img
        level = int(fusion["unified_risk_level"])
        cv2.rectangle(canvas, (30, 20), (790, 380), risk_color(level), 3)
        put_text(canvas, f"nuScenes {frame['frame_index']:03d} | {frame['timestamp']}", (48, 54), 0.62, (255, 255, 255), 2)
        if "CAM_FRONT" in iqa.get("soiled_cameras", []):
            put_text(canvas, "CAM_FRONT SOILING", (48, 352), 0.8, (0, 220, 255), 2)
        if adas.get("target_object_id"):
            dist = adas.get("front_object_distance")
            put_text(canvas, f"Front risk target: {dist:.1f}m", (48, 324), 0.65, risk_color(int(adas["adas_level"])), 2)
        draw_bev(canvas, objects["objects"], level)
        draw_risk_panel(canvas, adas, dms, iqa, fusion)
        put_text(
            canvas,
            f"Frame {frame['frame_index'] + 1:03d}/{len(frames):03d}   ADAS L{adas['adas_level']} | DMS L{dms['danger_level']} | IQA L{iqa['iqa_level']} | Fusion L{level}",
            (30, 708),
            0.58,
            (230, 235, 240),
            1,
        )
        writer.write(canvas)
    writer.release()
    print(f"Video: {out}")


def write_demo_readme(scene_dir: Path, cache_dir: Path, config_path: Path) -> None:
    meta = read_json(cache_dir / "meta.json")
    text = f"""# nuScenes Offline Demo MVP

## 数据来源

- nuScenes version: `{meta['version']}`
- dataroot: `{meta['dataroot']}`
- scene: `{meta['scene_name']}` (index `{meta['scene_index']}`)
- frames: `{meta['frames']}`

## 模块流程

`nuScenes mini -> GT ADAS/TTC pseudo perception -> scripted DMS -> scripted IQA -> offline arbitration -> demo.mp4`

## 重要说明

本 Demo 阶段使用 nuScenes GT boxes 生成 ADAS/TTC 伪感知结果，用于系统可视化与仲裁逻辑展示，不代表最终真实视觉检测模型性能。

nuScenes 不包含座舱驾驶员视频，因此 DMS 使用 scripted timeline。IQA 当前使用 scripted camera quality timeline，预留了 `offline_model_result` 输入用于后续接入真实 IQA 模型结果。

## 运行命令

```bash
python tools/run_demo_pipeline.py --config {config_path.as_posix()}
```

## 输出文件

- `demo_cache/frames.jsonl`
- `demo_cache/gt_objects.jsonl`
- `adas_status.jsonl`
- `adas_objects.jsonl`
- `dms_status.jsonl`
- `iqa_status.jsonl`
- `fusion_status.jsonl`
- `demo.mp4`

## 坐标约定

GT box 从 global 坐标转换到 ego 坐标后，`x > 0` 表示车辆前方，`y > 0` 表示左侧，距离使用 `sqrt(x^2 + y^2)`。

## 后续计划

1. 将 GT ADAS 替换为真实视觉检测或 BEV 感知输出。
2. 将 scripted IQA 替换为 IQA 模型对 nuScenes 图像或污染增强图像的离线推理结果。
3. 增加 ROS2 topic replay，与在线仲裁节点共用同一套事件语义。
4. 增强前视图 2D/3D box 投影和六视图展示。
"""
    (scene_dir / "README_demo.md").write_text(text, encoding="utf-8")


def run_pipeline(args: argparse.Namespace) -> None:
    config_path = Path(args.config)
    cfg = load_config(config_path)
    dataroot = normalize_dataroot(cfg["nuscenes"]["dataroot"])
    out_root = Path(cfg.get("output", {}).get("root", "demo_outputs"))
    scene_dir = out_root / cfg.get("output", {}).get("scene_dir", "scene_000")
    cache_dir = scene_dir / "demo_cache"
    scene_dir.mkdir(parents=True, exist_ok=True)

    export_args = argparse.Namespace(
        dataroot=dataroot,
        version=cfg["nuscenes"].get("version", "v1.0-mini"),
        scene_index=cfg["nuscenes"].get("scene_index"),
        scene_name=cfg["nuscenes"].get("scene_name"),
        max_frames=int(cfg["nuscenes"].get("max_frames", 80)),
        auto_select_scene=bool(cfg["nuscenes"].get("auto_select_scene", True)),
        out=cache_dir,
        copy_images=bool(cfg.get("demo", {}).get("copy_images", True)),
        overwrite=True,
    )
    if not args.skip_cache:
        export_cache(export_args)
    generate_adas(argparse.Namespace(cache=cache_dir, out_dir=scene_dir, front_y_abs_max=3.5))
    generate_dms(argparse.Namespace(frames=cache_dir / "frames.jsonl", out=scene_dir / "dms_status.jsonl"))
    generate_iqa(
        argparse.Namespace(
            frames=cache_dir / "frames.jsonl",
            out=scene_dir / "iqa_status.jsonl",
            iqa_source="scripted",
            model_result=None,
        )
    )
    run_arbitration(
        argparse.Namespace(
            adas=scene_dir / "adas_status.jsonl",
            dms=scene_dir / "dms_status.jsonl",
            iqa=scene_dir / "iqa_status.jsonl",
            out=scene_dir / "fusion_status.jsonl",
        )
    )
    render_video(
        argparse.Namespace(
            cache=cache_dir,
            adas_objects=scene_dir / "adas_objects.jsonl",
            adas_status=scene_dir / "adas_status.jsonl",
            dms_status=scene_dir / "dms_status.jsonl",
            iqa_status=scene_dir / "iqa_status.jsonl",
            fusion_status=scene_dir / "fusion_status.jsonl",
            out=scene_dir / "demo.mp4",
            fps=int(cfg.get("demo", {}).get("fps", 5)),
        )
    )
    write_demo_readme(scene_dir, cache_dir, config_path)
    print("Demo pipeline completed.")
    print(f"Scene: {read_json(cache_dir / 'meta.json')['scene_name']}")
    print(f"Frames: {len(read_jsonl(cache_dir / 'frames.jsonl'))}")
    print(f"ADAS status: {scene_dir / 'adas_status.jsonl'}")
    print(f"DMS status: {scene_dir / 'dms_status.jsonl'}")
    print(f"IQA status: {scene_dir / 'iqa_status.jsonl'}")
    print(f"Fusion status: {scene_dir / 'fusion_status.jsonl'}")
    print(f"Video: {scene_dir / 'demo.mp4'}")


def build_parser(command: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    if command == "export_cache":
        parser.add_argument("--dataroot", required=True)
        parser.add_argument("--version", default="v1.0-mini")
        parser.add_argument("--scene-index", type=int, default=0)
        parser.add_argument("--scene-name")
        parser.add_argument("--max-frames", type=int, default=80)
        parser.add_argument("--auto-select-scene", action="store_true")
        parser.add_argument("--out", required=True)
        parser.add_argument("--copy-images", action=argparse.BooleanOptionalAction, default=True)
        parser.add_argument("--overwrite", action=argparse.BooleanOptionalAction, default=True)
    elif command == "generate_adas":
        parser.add_argument("--cache", required=True)
        parser.add_argument("--out-dir", required=True)
        parser.add_argument("--front-y-abs-max", type=float, default=3.5)
    elif command == "generate_dms":
        parser.add_argument("--frames", required=True)
        parser.add_argument("--out", required=True)
    elif command == "generate_iqa":
        parser.add_argument("--frames", required=True)
        parser.add_argument("--out", required=True)
        parser.add_argument("--iqa-source", choices=["scripted", "offline_model_result"], default="scripted")
        parser.add_argument("--model-result")
    elif command == "run_arbitration":
        parser.add_argument("--adas", required=True)
        parser.add_argument("--dms", required=True)
        parser.add_argument("--iqa", required=True)
        parser.add_argument("--out", required=True)
    elif command == "render_video":
        parser.add_argument("--cache", required=True)
        parser.add_argument("--adas-objects", required=True)
        parser.add_argument("--adas-status", required=True)
        parser.add_argument("--dms-status", required=True)
        parser.add_argument("--iqa-status", required=True)
        parser.add_argument("--fusion-status", required=True)
        parser.add_argument("--out", required=True)
        parser.add_argument("--fps", type=int, default=5)
    elif command == "run_pipeline":
        parser.add_argument("--config", required=True)
        parser.add_argument("--skip-cache", action="store_true")
    return parser


def main(command: str) -> None:
    parser = build_parser(command)
    args = parser.parse_args()
    {
        "export_cache": export_cache,
        "generate_adas": generate_adas,
        "generate_dms": generate_dms,
        "generate_iqa": generate_iqa,
        "run_arbitration": run_arbitration,
        "render_video": render_video,
        "run_pipeline": run_pipeline,
    }[command](args)
