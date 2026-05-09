import math
from enum import IntEnum

import numpy as np


class WarningLevel(IntEnum):
    LEVEL_1_SAFE = 1
    LEVEL_2_ATTENTION = 2
    LEVEL_3_WARNING = 3
    LEVEL_4_EMERGENCY = 4


class VehicleState:
    def __init__(
        self,
        x,
        y,
        speed,
        heading,
        acceleration=0.0,
        yaw_rate=0.0,
        steering_angle=0.0,
        turn_signal=0,
    ):
        self.x = x
        self.y = y
        self.speed = speed
        self.heading = heading
        self.acceleration = acceleration
        self.yaw_rate = yaw_rate
        self.steering_angle = steering_angle
        self.turn_signal = turn_signal


class CTRV_EKF:
    """5D EKF for CTRV target smoothing: [x, y, v, yaw, yaw_rate]."""

    def __init__(self, x, y, v, yaw, dt=0.1):
        self.dt = dt
        self.X = np.matrix([[x], [y], [v], [yaw], [0.0]])
        self.P = np.matrix(np.eye(5)) * 10.0
        self.H = np.matrix(
            [
                [1, 0, 0, 0, 0],
                [0, 1, 0, 0, 0],
                [0, 0, 1, 0, 0],
                [0, 0, 0, 1, 0],
            ]
        )
        self.R = np.matrix(np.eye(4))
        self.R[0, 0] = 0.5
        self.R[1, 1] = 0.5
        self.R[2, 2] = 2.0
        self.R[3, 3] = 0.1
        self.Q = np.matrix(np.eye(5)) * 0.1
        self.Q[2, 2] = 1.0
        self.Q[4, 4] = 0.5

    @staticmethod
    def _normalize_angle(angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def update(self, z_measurement):
        px, py, v, yaw, yawd = (
            self.X[0, 0],
            self.X[1, 0],
            self.X[2, 0],
            self.X[3, 0],
            self.X[4, 0],
        )

        if abs(yawd) > 0.001:
            px_p = px + (v / yawd) * (math.sin(yaw + yawd * self.dt) - math.sin(yaw))
            py_p = py + (v / yawd) * (-math.cos(yaw + yawd * self.dt) + math.cos(yaw))
        else:
            px_p = px + v * self.dt * math.cos(yaw)
            py_p = py + v * self.dt * math.sin(yaw)

        yaw_p = yaw + yawd * self.dt
        x_pred = np.matrix([[px_p], [py_p], [v], [yaw_p], [yawd]])

        f_j = np.matrix(np.eye(5))
        if abs(yawd) > 0.001:
            f_j[0, 2] = (1.0 / yawd) * (math.sin(yaw + yawd * self.dt) - math.sin(yaw))
            f_j[0, 3] = (v / yawd) * (math.cos(yaw + yawd * self.dt) - math.cos(yaw))
            f_j[0, 4] = (v * self.dt * math.cos(yaw + yawd * self.dt)) / yawd - (
                v / yawd**2
            ) * (math.sin(yaw + yawd * self.dt) - math.sin(yaw))
            f_j[1, 2] = (1.0 / yawd) * (-math.cos(yaw + yawd * self.dt) + math.cos(yaw))
            f_j[1, 3] = (v / yawd) * (math.sin(yaw + yawd * self.dt) - math.sin(yaw))
            f_j[1, 4] = (v * self.dt * math.sin(yaw + yawd * self.dt)) / yawd - (
                v / yawd**2
            ) * (-math.cos(yaw + yawd * self.dt) + math.cos(yaw))
        else:
            f_j[0, 2] = math.cos(yaw) * self.dt
            f_j[0, 3] = -v * math.sin(yaw) * self.dt
            f_j[1, 2] = math.sin(yaw) * self.dt
            f_j[1, 3] = v * math.cos(yaw) * self.dt

        f_j[3, 4] = self.dt
        p_pred = f_j * self.P * f_j.T + self.Q

        z = np.matrix(z_measurement).T
        z_pred = self.H * x_pred
        residual = z - z_pred
        residual[3, 0] = self._normalize_angle(residual[3, 0])

        s = self.H * p_pred * self.H.T + self.R
        k = p_pred * self.H.T * np.linalg.inv(s)

        self.X = x_pred + k * residual
        self.X[3, 0] = self._normalize_angle(self.X[3, 0])
        self.P = (np.matrix(np.eye(5)) - k * self.H) * p_pred

        return self.X[0, 0], self.X[1, 0], self.X[2, 0], self.X[3, 0], self.X[4, 0]


class TrajectoryPredictor:
    def __init__(self, wheelbase=2.8, predict_time=3.0, dt=0.1):
        self.wheelbase = wheelbase
        self.predict_time = predict_time
        self.dt = dt

    def predict_ego_trajectory(self, ego_state):
        trajectory = []
        x, y, theta = 0.0, 0.0, 0.0
        v = ego_state.speed
        delta = ego_state.steering_angle / 15.0

        for _ in range(int(self.predict_time / self.dt)):
            x += v * math.cos(theta) * self.dt
            y += v * math.sin(theta) * self.dt
            theta += (v / self.wheelbase) * math.tan(delta) * self.dt
            trajectory.append((x, y))
        return trajectory

    def predict_target_trajectory(self, target_state):
        trajectory = []
        x, y = target_state.x, target_state.y
        v = target_state.speed
        theta = target_state.heading
        a = target_state.acceleration
        omega = target_state.yaw_rate

        for t_step in range(1, int(self.predict_time / self.dt) + 1):
            t = t_step * self.dt
            if abs(omega) > 0.01 and v > 0.1:
                next_x = x + (v / omega) * (math.sin(theta + omega * t) - math.sin(theta))
                next_y = y + (v / omega) * (-math.cos(theta + omega * t) + math.cos(theta))
            else:
                travel = v * t + 0.5 * a * t**2
                next_x = x + travel * math.cos(theta)
                next_y = y + travel * math.sin(theta)
            trajectory.append((next_x, next_y))
        return trajectory

    @staticmethod
    def check_trajectory_conflict(ego_traj, target_traj, threshold=2.0):
        for (ex, ey), (tx, ty) in zip(ego_traj, target_traj):
            if math.hypot(ex - tx, ey - ty) < threshold:
                return True
        return False


class TTCCalculator:
    @staticmethod
    def calculate(ego_state, target_state):
        rel_x, rel_y = target_state.x, target_state.y
        distance = math.hypot(rel_x, rel_y)

        v_ego_x = ego_state.speed * math.cos(ego_state.heading)
        v_ego_y = ego_state.speed * math.sin(ego_state.heading)
        v_target_x = target_state.speed * math.cos(target_state.heading)
        v_target_y = target_state.speed * math.sin(target_state.heading)

        rel_vx = v_ego_x - v_target_x
        rel_vy = v_ego_y - v_target_y

        if distance == 0:
            return 0.1
        v_approach = (rel_vx * rel_x + rel_vy * rel_y) / distance

        if v_approach <= 0:
            return float("inf")
        return distance / v_approach


class BSDLCADetector:
    def __init__(self):
        self.bsd_x_range = (-15.0, 2.0)
        self.bsd_y_range_left = (1.5, 4.5)
        self.bsd_y_range_right = (-4.5, -1.5)

    def is_in_blind_spot(self, target_state):
        x, y = target_state.x, target_state.y
        in_x = self.bsd_x_range[0] <= x <= self.bsd_x_range[1]
        in_y_left = self.bsd_y_range_left[0] <= y <= self.bsd_y_range_left[1]
        in_y_right = self.bsd_y_range_right[0] <= y <= self.bsd_y_range_right[1]
        return in_x and (in_y_left or in_y_right)

    @staticmethod
    def check_lca_intent(ego_state, target_state):
        if ego_state.turn_signal == 1 and target_state.y > 0:
            return True
        if ego_state.turn_signal == -1 and target_state.y < 0:
            return True
        return False


class ADASGlobalSystem:
    def __init__(self):
        self.predictor = TrajectoryPredictor()
        self.ttc_calc = TTCCalculator()
        self.bsd_lca = BSDLCADetector()

    def process_frame(self, ego_state, target_states):
        global_risk = WarningLevel.LEVEL_1_SAFE
        trigger_events = []
        ego_traj = self.predictor.predict_ego_trajectory(ego_state)

        for target in target_states:
            target_traj = self.predictor.predict_target_trajectory(target)
            ttc = self.ttc_calc.calculate(ego_state, target)
            has_conflict = self.predictor.check_trajectory_conflict(ego_traj, target_traj)
            in_bsd = self.bsd_lca.is_in_blind_spot(target)
            lca_intent = self.bsd_lca.check_lca_intent(ego_state, target)

            current_target_risk = WarningLevel.LEVEL_1_SAFE

            if in_bsd:
                current_target_risk = max(current_target_risk, WarningLevel.LEVEL_2_ATTENTION)
                trigger_events.append("BSD_ACTIVE")

            if has_conflict and 3.0 <= ttc <= 5.0:
                current_target_risk = max(current_target_risk, WarningLevel.LEVEL_3_WARNING)
                trigger_events.append("FCW_POTENTIAL")

            if lca_intent and has_conflict and ttc < 5.0:
                current_target_risk = max(current_target_risk, WarningLevel.LEVEL_4_EMERGENCY)
                trigger_events.append("LCA_INTERVENTION")

            if has_conflict and ttc < 3.0:
                current_target_risk = max(current_target_risk, WarningLevel.LEVEL_4_EMERGENCY)
                trigger_events.append("FCW_EMERGENCY")

            global_risk = max(global_risk, current_target_risk)

        return {
            "global_risk_level": int(global_risk),
            "active_events": set(trigger_events),
        }
