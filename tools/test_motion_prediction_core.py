#!/usr/bin/env python3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "motion_prediction"))

from motion_prediction.ttc_algorithm_core import ADASGlobalSystem, VehicleState  # noqa: E402


def assert_event(name, result):
    if name not in result["active_events"]:
        raise AssertionError(f"expected {name}, got {result}")


def main():
    adas = ADASGlobalSystem()

    emergency = adas.process_frame(
        VehicleState(x=0.0, y=0.0, speed=10.0, heading=0.0),
        [VehicleState(x=20.0, y=0.0, speed=0.0, heading=0.0)],
    )
    assert emergency["global_risk_level"] == 4
    assert_event("FCW_EMERGENCY", emergency)

    potential = adas.process_frame(
        VehicleState(x=0.0, y=0.0, speed=10.0, heading=0.0),
        [VehicleState(x=30.0, y=0.0, speed=0.0, heading=0.0)],
    )
    assert potential["global_risk_level"] == 3
    assert_event("FCW_POTENTIAL", potential)

    bsd = adas.process_frame(
        VehicleState(x=0.0, y=0.0, speed=10.0, heading=0.0),
        [VehicleState(x=-5.0, y=3.0, speed=10.0, heading=0.0)],
    )
    assert bsd["global_risk_level"] == 2
    assert_event("BSD_ACTIVE", bsd)

    lca = adas.process_frame(
        VehicleState(x=0.0, y=0.0, speed=10.0, heading=0.0, turn_signal=1),
        [VehicleState(x=20.0, y=0.5, speed=0.0, heading=0.0)],
    )
    assert lca["global_risk_level"] == 4
    assert_event("LCA_INTERVENTION", lca)

    print("motion_prediction_core checks passed")


if __name__ == "__main__":
    main()
