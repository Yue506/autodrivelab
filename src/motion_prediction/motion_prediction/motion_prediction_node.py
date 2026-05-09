import math

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from autodrivelab_msgs.msg import BevObjects, EgoState, RiskMetrics
from .ttc_algorithm_core import ADASGlobalSystem, CTRV_EKF, VehicleState


class MotionPredictionNode(Node):
    def __init__(self):
        super().__init__("motion_prediction_node")
        self.adas_system = ADASGlobalSystem()
        self.ekf_filters = {}
        self.last_speeds = {}
        self.dt = 0.1
        self.ego = None
        self.publisher = self.create_publisher(RiskMetrics, "/autodrivelab/risk_metrics", 10)
        self.ego_sub = self.create_subscription(EgoState, "/autodrivelab/ego_state", self.on_ego, 10)
        self.bev_sub = self.create_subscription(BevObjects, "/autodrivelab/bev/objects", self.on_bev, 10)
        self.get_logger().info("Advanced motion prediction node started with EKF + CTRV/CA risk reasoning.")

    def on_ego(self, ego: EgoState):
        self.ego = ego

    def on_bev(self, bev: BevObjects):
        if self.ego is None:
            return

        ego_state = VehicleState(
            x=0.0,
            y=0.0,
            speed=float(self.ego.speed_mps),
            heading=0.0,
            acceleration=float(getattr(self.ego, "acceleration_mps2", 0.0)),
            yaw_rate=float(getattr(self.ego, "yaw_rate_radps", 0.0)),
            steering_angle=float(getattr(self.ego, "steering_angle_rad", 0.0)),
            turn_signal=int(getattr(self.ego, "turn_signal", 0)),
        )

        target_states = []
        seen_target_ids = set()
        global_min_ttc = float("inf")

        for i, obj in enumerate(bev.objects):
            target_id = obj.track_id if getattr(obj, "track_id", "") else f"idx_{i}"
            seen_target_ids.add(target_id)

            raw_x = float(obj.x_m)
            raw_y = float(obj.y_m)
            vx = float(getattr(obj, "vx_mps", 0.0))
            vy = float(getattr(obj, "vy_mps", 0.0))

            raw_speed = math.hypot(vx, vy)
            if raw_speed > 0.1:
                raw_heading = math.atan2(vy, vx)
            else:
                raw_heading = float(getattr(obj, "yaw_rad", 0.0))

            if target_id not in self.ekf_filters:
                self.ekf_filters[target_id] = CTRV_EKF(raw_x, raw_y, raw_speed, raw_heading, self.dt)
                self.last_speeds[target_id] = raw_speed

            z_meas = [raw_x, raw_y, raw_speed, raw_heading]
            f_x, f_y, f_v, f_yaw, f_yaw_rate = self.ekf_filters[target_id].update(z_meas)

            acc = (f_v - self.last_speeds[target_id]) / self.dt
            self.last_speeds[target_id] = f_v

            target_states.append(
                VehicleState(
                    x=float(f_x),
                    y=float(f_y),
                    speed=float(f_v),
                    heading=float(f_yaw),
                    acceleration=float(acc),
                    yaw_rate=float(f_yaw_rate),
                )
            )

            closing_speed = max(ego_state.speed - f_v * math.cos(f_yaw), 0.0)
            ttc = math.hypot(f_x, f_y) / closing_speed if closing_speed > 0.1 else float("inf")
            global_min_ttc = min(global_min_ttc, ttc)

        stale_ids = set(self.ekf_filters.keys()) - seen_target_ids
        for stale_id in stale_ids:
            self.ekf_filters.pop(stale_id, None)
            self.last_speeds.pop(stale_id, None)

        result = self.adas_system.process_frame(ego_state, target_states)

        msg = RiskMetrics()
        msg.header.stamp = bev.header.stamp
        msg.header.frame_id = "base_link"
        msg.min_ttc_s = 999.0 if math.isinf(global_min_ttc) else float(global_min_ttc)
        msg.risk_level = int(result["global_risk_level"])
        msg.active_events = sorted(list(result["active_events"]))
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = MotionPredictionNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
