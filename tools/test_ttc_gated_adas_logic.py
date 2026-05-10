#!/usr/bin/env python3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from demo.offline_mvp import adas_level_from_ttc, compute_ttc  # noqa: E402


def main():
    prev = {}

    ttc, relative_speed = compute_ttc("front_car", 1_000_000, 4.0, prev)
    level, event, _ = adas_level_from_ttc(ttc)
    assert ttc is None
    assert relative_speed == 0.0
    assert level == 0
    assert event == "ADAS_NORMAL"

    ttc, relative_speed = compute_ttc("front_car", 2_000_000, 4.0, prev)
    level, event, _ = adas_level_from_ttc(ttc)
    assert ttc is None
    assert relative_speed == 0.0
    assert level == 0
    assert event == "ADAS_NORMAL"

    ttc, relative_speed = compute_ttc("front_car", 3_000_000, 3.0, prev)
    level, event, _ = adas_level_from_ttc(ttc)
    assert round(relative_speed, 3) == 1.0
    assert round(ttc, 3) == 3.0
    assert level == 3
    assert event == "FCW_POTENTIAL"

    ttc, relative_speed = compute_ttc("front_car", 4_000_000, 1.0, prev)
    level, event, _ = adas_level_from_ttc(ttc)
    assert round(relative_speed, 3) == 2.0
    assert round(ttc, 3) == 0.5
    assert level == 4
    assert event == "FCW_EMERGENCY"

    print("ttc-gated ADAS checks passed")


if __name__ == "__main__":
    main()
