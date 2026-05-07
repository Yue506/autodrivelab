from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


DEFAULT_OBJECT_SIZE = {
    "car": {"length": 4.5, "width": 1.8},
    "truck": {"length": 7.0, "width": 2.5},
    "bus": {"length": 10.0, "width": 2.8},
    "trailer": {"length": 8.0, "width": 2.5},
    "construction_vehicle": {"length": 6.0, "width": 2.5},
    "pedestrian": {"length": 0.6, "width": 0.6},
    "bicycle": {"length": 1.8, "width": 0.7},
    "motorcycle": {"length": 2.0, "width": 0.8},
    "traffic_cone": {"length": 0.4, "width": 0.4},
    "barrier": {"length": 2.0, "width": 0.5},
    "unknown": {"length": 1.0, "width": 1.0},
}


@dataclass(frozen=True)
class BevRenderConfig:
    x_min: float = -10.0
    x_max: float = 50.0
    y_min: float = -25.0
    y_max: float = 25.0
    ego_length_m: float = 4.6
    ego_width_m: float = 1.9
    ego_min_length_px: int = 24
    ego_min_width_px: int = 12
    object_min_size_px: int = 6
    risk_highlight_margin_m: float = 0.4
    far_object_distance_m: float = 35.0
    draw_distance_line: bool = True
    draw_distance_text: bool = True
    draw_risk_highlight_box: bool = True
    merge_same_class_overlaps: bool = True
    merge_overlap_margin_m: float = 0.35
    static_roadside_y_abs_m: float = 3.5


def get_object_physical_size(obj: dict[str, Any]) -> tuple[float, float]:
    width = obj.get("width")
    length = obj.get("length")
    size = obj.get("size")
    if (width is None or length is None) and isinstance(size, (list, tuple)) and len(size) >= 2:
        width = size[0] if width is None else width
        length = size[1] if length is None else length
    defaults = DEFAULT_OBJECT_SIZE.get(str(obj.get("class_name", "unknown")), DEFAULT_OBJECT_SIZE["unknown"])
    try:
        width_m = float(width) if width is not None else float(defaults["width"])
        length_m = float(length) if length is not None else float(defaults["length"])
    except (TypeError, ValueError):
        width_m = float(defaults["width"])
        length_m = float(defaults["length"])
    return max(width_m, 0.1), max(length_m, 0.1)


def compute_bev_scale(bev_w: int, bev_h: int, cfg: BevRenderConfig) -> float:
    return min(bev_w / (cfg.y_max - cfg.y_min), bev_h / (cfg.x_max - cfg.x_min))


def bev_to_pixel(x_m: float, y_m: float, scale: float, origin_px: tuple[int, int]) -> tuple[int, int]:
    ox, oy = origin_px
    return int(round(ox - y_m * scale)), int(round(oy - x_m * scale))


def risk_color(level: int) -> tuple[int, int, int]:
    return [(72, 190, 90), (80, 220, 220), (0, 188, 255), (0, 112, 255), (0, 0, 235)][max(0, min(4, level))]


def put_text(img, value, xy, scale=0.48, color=(235, 238, 242), thickness=1):
    cv2.putText(img, str(value), xy, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def rect_from_center(center: tuple[int, int], width_px: float, length_px: float) -> tuple[int, int, int, int]:
    cx, cy = center
    half_w = max(1, int(round(width_px / 2.0)))
    half_l = max(1, int(round(length_px / 2.0)))
    return cx - half_w, cy - half_l, cx + half_w, cy + half_l


def draw_box(canvas, center, width_px, length_px, color, thickness=1, fill=None):
    x1, y1, x2, y2 = rect_from_center(center, width_px, length_px)
    if fill is not None:
        cv2.rectangle(canvas, (x1, y1), (x2, y2), fill, -1)
    cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)


def draw_distance_annotation(canvas, origin_px, center_px, distance_m: float, color):
    cv2.line(canvas, origin_px, center_px, color, 1, cv2.LINE_AA)
    mx = int((origin_px[0] + center_px[0]) / 2)
    my = int((origin_px[1] + center_px[1]) / 2)
    put_text(canvas, f"{distance_m:.1f}m", (mx + 6, my - 6), 0.42, color, 1)


def is_static_class(class_name: str) -> bool:
    return class_name in {"barrier", "traffic_cone", "construction_vehicle", "unknown"}


def is_roadside_static(obj: dict[str, Any], cfg: BevRenderConfig) -> bool:
    try:
        y_m = abs(float(obj.get("y", 0.0)))
    except (TypeError, ValueError):
        y_m = 0.0
    return is_static_class(str(obj.get("class_name", "unknown"))) and y_m > cfg.static_roadside_y_abs_m


def object_extent_m(obj: dict[str, Any]) -> tuple[float, float, float, float]:
    x_m = float(obj.get("x", 0.0))
    y_m = float(obj.get("y", 0.0))
    width_m, length_m = get_object_physical_size(obj)
    return (
        x_m - length_m / 2.0,
        x_m + length_m / 2.0,
        y_m - width_m / 2.0,
        y_m + width_m / 2.0,
    )


def extents_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float], margin: float) -> bool:
    ax1, ax2, ay1, ay2 = a
    bx1, bx2, by1, by2 = b
    return ax1 <= bx2 + margin and bx1 <= ax2 + margin and ay1 <= by2 + margin and by1 <= ay2 + margin


def merge_object_group(group: list[dict[str, Any]], target_object_id: str | None) -> dict[str, Any]:
    extents = [object_extent_m(obj) for obj in group]
    x1 = min(item[0] for item in extents)
    x2 = max(item[1] for item in extents)
    y1 = min(item[2] for item in extents)
    y2 = max(item[3] for item in extents)
    representative = min(group, key=lambda obj: float(obj.get("distance", math.hypot(float(obj.get("x", 0.0)), float(obj.get("y", 0.0))) or 0.0)))
    merged = dict(representative)
    merged["x"] = (x1 + x2) / 2.0
    merged["y"] = (y1 + y2) / 2.0
    merged["distance"] = min(float(obj.get("distance", math.hypot(float(obj.get("x", 0.0)), float(obj.get("y", 0.0))) or 0.0)) for obj in group)
    merged["size"] = [max(y2 - y1, 0.1), max(x2 - x1, 0.1), 1.0]
    merged["object_id"] = ",".join(str(obj.get("object_id", "")) for obj in group if obj.get("object_id"))
    if target_object_id and any(obj.get("object_id") == target_object_id for obj in group):
        merged["object_id"] = target_object_id
    merged["is_front_risk"] = any(bool(obj.get("is_front_risk")) for obj in group)
    merged["risk_level"] = max(int(obj.get("risk_level", 0) or 0) for obj in group)
    merged["merged_count"] = len(group)
    return merged


def merge_same_class_overlaps(objects: list[dict[str, Any]], target_object_id: str | None, cfg: BevRenderConfig) -> list[dict[str, Any]]:
    if not cfg.merge_same_class_overlaps:
        return objects
    remaining = list(objects)
    merged: list[dict[str, Any]] = []
    while remaining:
        seed = remaining.pop(0)
        group = [seed]
        changed = True
        while changed:
            changed = False
            group_extent = object_extent_m(merge_object_group(group, target_object_id))
            next_remaining = []
            for obj in remaining:
                same_class = str(obj.get("class_name", "unknown")) == str(seed.get("class_name", "unknown"))
                if same_class and extents_overlap(group_extent, object_extent_m(obj), cfg.merge_overlap_margin_m):
                    group.append(obj)
                    changed = True
                else:
                    next_remaining.append(obj)
            remaining = next_remaining
        merged.append(merge_object_group(group, target_object_id) if len(group) > 1 else seed)
    return merged


def draw_bev_scene(
    canvas: np.ndarray,
    rect: tuple[int, int, int, int],
    objects: list[dict[str, Any]],
    *,
    target_object_id: str | None = None,
    border_level: int = 0,
    title: str = "BEV FSD-style View",
    cfg: BevRenderConfig = BevRenderConfig(),
) -> None:
    x0, y0, w, h = rect
    cv2.rectangle(canvas, (x0, y0), (x0 + w, y0 + h), (19, 24, 31), -1)
    cv2.rectangle(canvas, (x0, y0), (x0 + w, y0 + h), risk_color(border_level), 2)
    put_text(canvas, title, (x0 + 16, y0 + 32), 0.62, (235, 238, 242), 2)
    put_text(canvas, "Equal px/m scale, physical-size boxes", (x0 + 16, y0 + 54), 0.42, (145, 158, 176), 1)

    pad_x, top_pad, bottom_pad = 25, 64, 22
    draw_x0, draw_y0 = x0 + pad_x, y0 + top_pad
    draw_w, draw_h = max(1, w - 2 * pad_x), max(1, h - top_pad - bottom_pad)
    scale = compute_bev_scale(draw_w, draw_h, cfg)
    origin_px = (int(draw_x0 + draw_w / 2), int(draw_y0 + draw_h * 0.85))

    for meter in [0, 10, 20, 30, 40, 50]:
        _, yy = bev_to_pixel(meter, 0, scale, origin_px)
        if draw_y0 <= yy <= draw_y0 + draw_h:
            cv2.line(canvas, (draw_x0, yy), (draw_x0 + draw_w, yy), (50, 58, 68), 1)
            if meter > 0:
                put_text(canvas, f"{meter}m", (draw_x0 + 8, yy - 5), 0.36, (140, 150, 160), 1)
    for lane_y in [-3.5, 0, 3.5]:
        px, _ = bev_to_pixel(0, lane_y, scale, origin_px)
        cv2.line(canvas, (px, draw_y0), (px, draw_y0 + draw_h), (66, 72, 82), 1, cv2.LINE_AA)

    ego_l = max(cfg.ego_length_m * scale, cfg.ego_min_length_px)
    ego_w = max(cfg.ego_width_m * scale, cfg.ego_min_width_px)
    draw_box(canvas, origin_px, ego_w, ego_l, (230, 232, 235), 2, (205, 208, 212))
    put_text(canvas, "EGO", (origin_px[0] - 15, origin_px[1] + int(ego_l / 2) + 18), 0.38, (230, 232, 235), 1)

    display_objects = merge_same_class_overlaps(objects, target_object_id, cfg)
    for obj in display_objects:
        try:
            x_m, y_m = float(obj.get("x", 0.0)), float(obj.get("y", 0.0))
        except (TypeError, ValueError):
            continue
        if x_m < cfg.x_min or x_m > cfg.x_max or y_m < cfg.y_min or y_m > cfg.y_max:
            continue
        center = bev_to_pixel(x_m, y_m, scale, origin_px)
        level = int(obj.get("risk_level", 0) or 0)
        roadside_static = is_roadside_static(obj, cfg)
        is_primary_target = bool(target_object_id) and obj.get("object_id") == target_object_id
        is_target = is_primary_target or (bool(obj.get("is_front_risk")) and not roadside_static)
        width_m, length_m = get_object_physical_size(obj)
        distance_m = float(obj.get("distance", math.hypot(x_m, y_m)) or math.hypot(x_m, y_m))
        color = risk_color(level) if is_target or (level > 0 and not roadside_static) else (92, 118, 145)

        if distance_m > cfg.far_object_distance_m and not is_target:
            cv2.circle(canvas, center, max(3, cfg.object_min_size_px // 2), color, 1, cv2.LINE_AA)
            continue

        obj_w_px = max(width_m * scale, cfg.object_min_size_px)
        obj_l_px = max(length_m * scale, cfg.object_min_size_px)
        draw_box(canvas, center, obj_w_px, obj_l_px, color, 2 if is_target else 1)
        if obj.get("merged_count", 1) > 1 and not is_target:
            put_text(canvas, f"x{obj['merged_count']}", (center[0] + 6, center[1] + 12), 0.34, color, 1)

        if is_target:
            if cfg.draw_risk_highlight_box:
                margin_px = cfg.risk_highlight_margin_m * scale
                draw_box(canvas, center, obj_w_px + 2 * margin_px, obj_l_px + 2 * margin_px, color, 2)
            if cfg.draw_distance_line:
                draw_distance_annotation(canvas, origin_px, center, distance_m, color)
            label = f"RISK {distance_m:.1f}m"
            put_text(canvas, label, (center[0] + 10, center[1] - 10), 0.42, color, 1)
