# -*- coding: utf-8 -*-
import math
import numpy as np
from enum import IntEnum

# ==========================================
# 1. 基础数据结构与枚举定义
# ==========================================

class WarningLevel(IntEnum):
    LEVEL_1_SAFE = 1
    LEVEL_2_ATTENTION = 2
    LEVEL_3_WARNING = 3
    LEVEL_4_EMERGENCY = 4

class VehicleState:
    def __init__(self, x, y, speed, heading, acceleration=0.0, yaw_rate=0.0, steering_angle=0.0, turn_signal=0):
        self.x = x
        self.y = y
        self.speed = speed
        self.heading = heading
        self.acceleration = acceleration 
        self.yaw_rate = yaw_rate        
        self.steering_angle = steering_angle 
        self.turn_signal = turn_signal  

# ==========================================
# 2. 状态估计与滤波模块 (保留用于模拟)
# ==========================================

class Simple1DKalman:
    def __init__(self, initial_value, dt=0.5, is_angle=False):
        self.dt = dt
        self.is_angle = is_angle 
        self.X = np.array([[initial_value], [0.0]]) 
        self.P = np.array([[1.0, 0.0], [0.0, 1.0]])
        self.F = np.array([[1.0, self.dt], [0.0, 1.0]])
        self.H = np.array([[1.0, 0.0]])
        self.R = np.array([[0.5]])    
        self.Q = np.array([[0.01, 0.0], [0.0, 0.1]]) 

    def update(self, measurement):
        X_pred = np.dot(self.F, self.X)
        P_pred = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        
        S = np.dot(np.dot(self.H, P_pred), self.H.T) + self.R
        K = np.dot(np.dot(P_pred, self.H.T), np.linalg.inv(S))
        y = measurement - np.dot(self.H, X_pred)
        
        if self.is_angle and abs(y) > math.pi:
            y = (y + math.pi) % (2 * math.pi) - math.pi
            
        self.X = X_pred + np.dot(K, y)
        self.P = P_pred - np.dot(np.dot(K, self.H), P_pred)
        
        return self.X[0, 0], self.X[1, 0] 

# ==========================================
# 3. 核心算法模块 (你的完整算法逻辑)
# ==========================================

class TrajectoryPredictor:
    def __init__(self, wheelbase=2.8, predict_time=3.0, dt=0.5):
        self.wheelbase = wheelbase
        self.predict_time = predict_time
        self.dt = dt

    def predict_ego_trajectory(self, ego_state):
        trajectory = []
        x, y, theta = 0.0, 0.0, 0.0
        v = ego_state.speed
        delta = ego_state.steering_angle / 15.0 

        for t in range(int(self.predict_time / self.dt)):
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

        YAW_RATE_THRESHOLD = 0.05 

        for t_step in range(1, int(self.predict_time / self.dt) + 1):
            t = t_step * self.dt
            if abs(omega) > YAW_RATE_THRESHOLD and v > 0.1:
                next_x = x + (v / omega) * (math.sin(theta + omega * t) - math.sin(theta))
                next_y = y + (v / omega) * (-math.cos(theta + omega * t) + math.cos(theta))
            else:
                next_x = x + (v * t + 0.5 * a * t**2) * math.cos(theta)
                next_y = y + (v * t + 0.5 * a * t**2) * math.sin(theta)
            trajectory.append((next_x, next_y))
        return trajectory

    def check_trajectory_conflict(self, ego_traj, target_traj, threshold=2.0):
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
        
        if distance == 0: return 0.1
        v_approach = (rel_vx * rel_x + rel_vy * rel_y) / distance

        if v_approach <= 0:
            return float('inf')
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

    def check_lca_intent(self, ego_state, target_state):
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
                trigger_events.append("BSD_Active")

            if has_conflict and 3.0 <= ttc <= 5.0:
                current_target_risk = max(current_target_risk, WarningLevel.LEVEL_3_WARNING)
                trigger_events.append("FCW_Warning_Level_3")

            if lca_intent and has_conflict and ttc < 5.0:
                current_target_risk = max(current_target_risk, WarningLevel.LEVEL_4_EMERGENCY)
                trigger_events.append("LCA_Emergency_Intervention")

            if has_conflict and ttc < 3.0:
                current_target_risk = max(current_target_risk, WarningLevel.LEVEL_4_EMERGENCY)
                trigger_events.append("FCW_Emergency_Level_4")

            global_risk = max(global_risk, current_target_risk)

        return {"global_risk_level": global_risk.value, "active_events": list(set(trigger_events))}

# ==========================================
# 4. 模拟测试 (不需要数据集)
# ==========================================
if __name__ == "__main__":
    print("--- 正在运行 ADAS 核心算法模拟测试 ---")
    
    adas_system = ADASGlobalSystem()
    
    # 模拟场景：自车 20m/s (72km/h)，打左转向灯，准备变道
    ego = VehicleState(
        x=0, y=0, 
        speed=20.0, 
        heading=0.0, 
        steering_angle=0.1, 
        turn_signal=1
    )
    
    # 模拟目标：左后方盲区有一辆快车正在接近
    target_blind_spot = VehicleState(
        x=-8.0, y=2.5, 
        speed=25.0, 
        heading=0.0
    )
    
    # 模拟目标：前方安全车
    target_safe = VehicleState(
        x=60.0, y=0.0, 
        speed=20.0, 
        heading=0.0
    )

    result = adas_system.process_frame(ego, [target_blind_spot, target_safe])

    print(f"自车状态: 速度 {ego.speed*3.6:.1f} km/h | 转向灯: {'左' if ego.turn_signal==1 else '右' if ego.turn_signal==-1 else '无'}")
    print(f"最终风险等级: Level {result['global_risk_level']}")
    print(f"触发事件: {result['active_events']}")