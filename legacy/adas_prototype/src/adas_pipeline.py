# -*- coding: utf-8 -*-
import math
import numpy as np
from enum import IntEnum
from pyquaternion import Quaternion
from nuscenes.nuscenes import NuScenes
from nuscenes.can_bus.can_bus_api import NuScenesCanBus

# ==========================================
# 1. 基础数据结构与枚举定义
# ==========================================

class WarningLevel(IntEnum):
    LEVEL_1_SAFE = 1      # 一级预警：安全 (BSD静默)
    LEVEL_2_ATTENTION = 2 # 二级预警：注意 (BSD常亮)
    LEVEL_3_WARNING = 3   # 三级预警：警告 (灯闪烁)
    LEVEL_4_EMERGENCY = 4 # 四级预警：紧急 (灯闪+蜂鸣+震动)

class VehicleState:
    """车辆状态数据结构 (包含高阶运动学参数)"""
    def __init__(self, x, y, speed, heading, acceleration=0.0, yaw_rate=0.0, steering_angle=0.0, turn_signal=0):
        self.x = x                      # 全局/相对 X 坐标 (m)
        self.y = y                      # 全局/相对 Y 坐标 (m)
        self.speed = speed              # 速度 (m/s)
        self.heading = heading          # 航向角 (rad)
        self.acceleration = acceleration # 纵向加速度 (m/s^2)
        self.yaw_rate = yaw_rate        # 横摆角速度 (rad/s)
        self.steering_angle = steering_angle # 方向盘转角 (rad)
        self.turn_signal = turn_signal  # 转向灯: 0=无, 1=左, -1=右

# ==========================================
# 2. 状态估计与滤波模块 (Kalman Filter)
# ==========================================

class Simple1DKalman:
    """轻量级 1D 卡尔曼滤波器，用于平滑带噪声的观测值并估计一阶导数"""
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
        
        # 处理角度越界突变
        if self.is_angle and abs(y) > math.pi:
            y = (y + math.pi) % (2 * math.pi) - math.pi
            
        self.X = X_pred + np.dot(K, y)
        self.P = P_pred - np.dot(np.dot(K, self.H), P_pred)
        
        return self.X[0, 0], self.X[1, 0] # 返回: [平滑值, 变化率]

# ==========================================
# 3. 核心算法与仲裁模块
# ==========================================

class TrajectoryPredictor:
    """轨迹预测模块：融合阿克曼几何、CTRV 与 CA 模型"""
    def __init__(self, wheelbase=2.8, predict_time=3.0, dt=0.5):
        self.wheelbase = wheelbase
        self.predict_time = predict_time
        self.dt = dt

    def predict_ego_trajectory(self, ego_state):
        trajectory = []
        x, y, theta = 0.0, 0.0, 0.0
        v = ego_state.speed
        
        # 转向比假设为 15:1 (方向盘转角转化为车轮偏角)
        delta = ego_state.steering_angle / 15.0 

        for t in range(int(self.predict_time / self.dt)):
            x += v * math.cos(theta) * self.dt
            y += v * math.sin(theta) * self.dt
            # 阿克曼转向几何方程
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
                # CTRV (匀速转弯模型)
                next_x = x + (v / omega) * (math.sin(theta + omega * t) - math.sin(theta))
                next_y = y + (v / omega) * (-math.cos(theta + omega * t) + math.cos(theta))
            else:
                # CA (匀加速直线模型)
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
        # 定义侧后方盲区坐标范围
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
    """五合一仲裁调度系统"""
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

            # --- 预警仲裁逻辑树 ---
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
# 4. 数据管道与集成 (Pipeline)
# ==========================================

class NuScenesBridge:
    def __init__(self, nusc, nusc_can, adas_system):
        self.nusc = nusc
        self.nusc_can = nusc_can
        self.adas = adas_system
        self.dt = 0.5
        self.target_filters = {} 

    def global_to_ego_frame(self, target_trans, ego_trans, ego_rot):
        dx = target_trans[0] - ego_trans[0]
        dy = target_trans[1] - ego_trans[1]
        ego_yaw = Quaternion(ego_rot).yaw_pitch_roll[0]
        rel_x = dx * math.cos(-ego_yaw) - dy * math.sin(-ego_yaw)
        rel_y = dx * math.sin(-ego_yaw) + dy * math.cos(-ego_yaw)
        return rel_x, rel_y, ego_yaw

    def run_scene_simulation(self, scene_name):
        print(f"--- 正在加载场景: {scene_name} 及其 CAN 总线数据 ---")
        
        scene_tokens = [s['token'] for s in self.nusc.scene if s['name'] == scene_name]
        if not scene_tokens: return
        scene = self.nusc.get('scene', scene_tokens[0])
        current_sample = self.nusc.get('sample', scene['first_sample_token'])
        
        # 提前提取当前场景的 CAN 报文
        try:
            # 修正了官方 API 的反馈键名
            steer_msgs = self.nusc_can.get_messages(scene_name, 'steeranglefeedback') 
            pose_msgs = self.nusc_can.get_messages(scene_name, 'pose')
            can_available = True
        except Exception as e:
            print(f"警告: 无法加载该场景的 CAN 数据，将回退到坐标估算模式。详细错误: {e}")
            can_available = False
            steer_msgs, pose_msgs = [], []

        prev_ego_trans = None
        frame_idx = 0

        while current_sample['token'] != '':
            frame_idx += 1
            timestamp = current_sample['timestamp']
            
            cam_data = self.nusc.get('sample_data', current_sample['data']['CAM_FRONT'])
            ego_pose_token = self.nusc.get('ego_pose', cam_data['ego_pose_token'])
            ego_trans = ego_pose_token['translation']
            ego_rot = ego_pose_token['rotation']
            
            # --- 提取真实本车 CAN 总线状态 (时间戳对齐) ---
            ego_speed, ego_steer_rad, ego_yaw_rate, ego_accel = 0.0, 0.0, 0.0, 0.0
            
            if can_available and steer_msgs and pose_msgs:
                closest_steer = min(steer_msgs, key=lambda m: abs(m['utime'] - timestamp))
                closest_pose = min(pose_msgs, key=lambda m: abs(m['utime'] - timestamp))
                
                ego_speed = closest_pose['vel'][0]
                ego_accel = closest_pose['accel'][0]
                ego_yaw_rate = closest_pose['rotation_rate'][2]
                ego_steer_rad = closest_steer['value'] # 提取真实转角
            else:
                if prev_ego_trans is not None:
                    ego_speed = math.hypot(ego_trans[0] - prev_ego_trans[0], ego_trans[1] - prev_ego_trans[1]) / self.dt
            
            prev_ego_trans = ego_trans
            
            ego_state = VehicleState(
                x=0, y=0, 
                speed=ego_speed, 
                heading=0.0,
                acceleration=ego_accel,
                yaw_rate=ego_yaw_rate,
                steering_angle=ego_steer_rad,
                turn_signal=0
            )
            
            # --- 提取并平滑目标状态 ---
            target_states = []
            for ann_token in current_sample['anns']:
                ann = self.nusc.get('sample_annotation', ann_token)
                if 'vehicle' not in ann['category_name']: continue
                    
                target_trans = ann['translation']
                target_yaw = Quaternion(ann['rotation']).yaw_pitch_roll[0]
                vel = self.nusc.box_velocity(ann_token)
                raw_speed = 0.0 if np.isnan(vel).any() else math.hypot(vel[0], vel[1])
                
                rel_x, rel_y, ego_yaw = self.global_to_ego_frame(target_trans, ego_trans, ego_rot)
                raw_rel_heading = target_yaw - ego_yaw

                if ann_token not in self.target_filters:
                    self.target_filters[ann_token] = {
                        'speed_kf': Simple1DKalman(initial_value=raw_speed, dt=self.dt, is_angle=False),
                        'heading_kf': Simple1DKalman(initial_value=raw_rel_heading, dt=self.dt, is_angle=True)
                    }
                
                smoothed_speed, acceleration = self.target_filters[ann_token]['speed_kf'].update(raw_speed)
                smoothed_heading, yaw_rate = self.target_filters[ann_token]['heading_kf'].update(raw_rel_heading)
                
                target_states.append(VehicleState(rel_x, rel_y, smoothed_speed, smoothed_heading, acceleration, yaw_rate))
            
            # --- 执行 ADAS 算法 ---
            result = self.adas.process_frame(ego_state, target_states)
            
            print(f"帧 {frame_idx:03d} | 自车真实时速: {ego_speed*3.6:04.1f}km/h | 转角: {ego_steer_rad:+.2f} | 目标: {len(target_states):02d} | 风险: {result['global_risk_level']} | 事件: {result['active_events']}")
            
            if current_sample['next'] == '': break
            current_sample = self.nusc.get('sample', current_sample['next'])

# ==========================================
# 5. 程序启动入口
# ==========================================
if __name__ == "__main__":
    # 请确保此路径指向你的 nuscenes 文件夹（包含 v1.0-mini 和 can_bus）
    DATAROOT = r'E:\vscode_projects\ADAS\data\nuscenes' 
    
    try:
        nusc = NuScenes(version='v1.0-mini', dataroot=DATAROOT, verbose=False)
        nusc_can = NuScenesCanBus(dataroot=DATAROOT)
        
        adas_system = ADASGlobalSystem()
        bridge = NuScenesBridge(nusc, nusc_can, adas_system)
        
        # 运行场景测试
        bridge.run_scene_simulation(scene_name='scene-0061')
        
    except Exception as e:
        print(f"初始化失败，请检查数据目录。错误信息: {e}")