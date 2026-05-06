# -*- coding: utf-8 -*-
import cv2
import os
import math
import numpy as np
from pyquaternion import Quaternion
from nuscenes.nuscenes import NuScenes
from nuscenes.can_bus.can_bus_api import NuScenesCanBus

# ?? 极其关键：直接导入你写好的 ADAS 核心算法！
from adas_pipeline import ADASGlobalSystem, VehicleState, Simple1DKalman

# ==========================================
# 1. 基础配置
# ==========================================
DATAROOT = r'E:\vscode_projects\ADAS\data\nuscenes'
SCENE_NAME = 'scene-0061' # 这个场景完美包含 Level 2(BSD) 和 Level 3(FCW)
DT = 0.5

print("正在加载 nuScenes 核心组件与 CAN 总线数据...")
nusc = NuScenes(version='v1.0-mini', dataroot=DATAROOT, verbose=False)
nusc_can = NuScenesCanBus(dataroot=DATAROOT)

# 初始化你的 ADAS 仲裁系统
adas = ADASGlobalSystem()
target_filters = {} # 用于卡尔曼滤波

# ==========================================
# 2. 场景与数据初始化
# ==========================================
scene_tokens = [s['token'] for s in nusc.scene if s['name'] == SCENE_NAME]
if not scene_tokens:
    print(f"未找到场景 {SCENE_NAME}")
    exit()

scene = nusc.get('scene', scene_tokens[0])
current_sample = nusc.get('sample', scene['first_sample_token'])

try:
    steer_msgs = nusc_can.get_messages(SCENE_NAME, 'steeranglefeedback')
    pose_msgs = nusc_can.get_messages(SCENE_NAME, 'pose')
    can_available = True
except Exception as e:
    can_available = False
    steer_msgs, pose_msgs = [], []

prev_ego_trans = None
frame_idx = 1

print(f"? 开始可视化播放 {SCENE_NAME} ... (按 Q 键退出)")

# ==========================================
# 3. 核心大循环：一边播视频，一边算算法
# ==========================================
while current_sample['token'] != '':
    timestamp = current_sample['timestamp']
    
    # --- A. 获取图像并调整大小 ---
    cam_data = nusc.get('sample_data', current_sample['data']['CAM_FRONT'])
    img_path = os.path.join(DATAROOT, cam_data['filename'])
    img = cv2.imread(img_path)
    img = cv2.resize(img, (1280, 720)) # 调整为 720p 高清显示
    
    # --- B. 获取自车状态与 CAN 数据 ---
    ego_pose_token = nusc.get('ego_pose', cam_data['ego_pose_token'])
    ego_trans = ego_pose_token['translation']
    ego_rot = ego_pose_token['rotation']
    
    ego_speed, ego_steer_rad, ego_yaw_rate, ego_accel = 0.0, 0.0, 0.0, 0.0
    if can_available and steer_msgs and pose_msgs:
        closest_steer = min(steer_msgs, key=lambda m: abs(m['utime'] - timestamp))
        closest_pose = min(pose_msgs, key=lambda m: abs(m['utime'] - timestamp))
        ego_speed = closest_pose['vel'][0]
        ego_accel = closest_pose['accel'][0]
        ego_yaw_rate = closest_pose['rotation_rate'][2]
        ego_steer_rad = closest_steer['value']
    else:
        if prev_ego_trans is not None:
            ego_speed = math.hypot(ego_trans[0] - prev_ego_trans[0], ego_trans[1] - prev_ego_trans[1]) / DT
    prev_ego_trans = ego_trans
    
    ego_state = VehicleState(x=0, y=0, speed=ego_speed, heading=0.0, 
                             acceleration=ego_accel, yaw_rate=ego_yaw_rate, 
                             steering_angle=ego_steer_rad, turn_signal=0)

    # --- C. 提取目标并进行卡尔曼滤波 ---
    target_states = []
    ego_yaw_global = Quaternion(ego_rot).yaw_pitch_roll[0]
    
    for ann_token in current_sample['anns']:
        ann = nusc.get('sample_annotation', ann_token)
        if 'vehicle' not in ann['category_name']: continue
            
        target_trans = ann['translation']
        target_yaw_global = Quaternion(ann['rotation']).yaw_pitch_roll[0]
        vel = nusc.box_velocity(ann_token)
        raw_speed = 0.0 if np.isnan(vel).any() else math.hypot(vel[0], vel[1])
        
        # 坐标系转换
        dx = target_trans[0] - ego_trans[0]
        dy = target_trans[1] - ego_trans[1]
        rel_x = dx * math.cos(-ego_yaw_global) - dy * math.sin(-ego_yaw_global)
        rel_y = dx * math.sin(-ego_yaw_global) + dy * math.cos(-ego_yaw_global)
        raw_rel_heading = target_yaw_global - ego_yaw_global

        if ann_token not in target_filters:
            target_filters[ann_token] = {
                'speed_kf': Simple1DKalman(initial_value=raw_speed, dt=DT, is_angle=False),
                'heading_kf': Simple1DKalman(initial_value=raw_rel_heading, dt=DT, is_angle=True)
            }
        
        smoothed_speed, acc = target_filters[ann_token]['speed_kf'].update(raw_speed)
        smoothed_heading, yr = target_filters[ann_token]['heading_kf'].update(raw_rel_heading)
        target_states.append(VehicleState(rel_x, rel_y, smoothed_speed, smoothed_heading, acc, yr))
        
    # --- D. 运行你的 ADAS 算法！ ---
    result = adas.process_frame(ego_state, target_states)
    risk_level = result['global_risk_level']
    events = result['active_events']

    # ==========================================
    # 4. HUD UI 绘制 (毕业答辩的门面)
    # ==========================================
    # 颜色配置 (BGR)
    color_map = {
        1: (0, 255, 0),       # Level 1: 绿色 (安全)
        2: (0, 255, 255),     # Level 2: 黄色 (注意)
        3: (0, 165, 255),     # Level 3: 橙色 (警告)
        4: (0, 0, 255)        # Level 4: 红色 (紧急)
    }
    current_color = color_map.get(risk_level, (255, 255, 255))

    # 绘制基础信息面板
    cv2.rectangle(img, (10, 10), (450, 180), (0, 0, 0), -1) # 黑色半透明背景
    
    cv2.putText(img, f"Frame: {frame_idx:03d} | Targets: {len(target_states)}", (20, 45), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(img, f"Speed: {ego_speed*3.6:04.1f} km/h", (20, 85), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(img, f"Steer: {ego_steer_rad:+.2f} rad", (20, 125), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # 绘制风险等级与事件
    cv2.putText(img, f"RISK LEVEL: {risk_level}", (20, 165), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, current_color, 3)

    if events:
        event_str = " + ".join(events)
        cv2.putText(img, f"EVENTS: {event_str}", (20, 210), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, current_color, 2)

    # ? 触发 3 级或 4 级警告时，屏幕中央疯狂闪烁！
    if risk_level >= 3:
        cv2.rectangle(img, (0, 0), (1280, 720), current_color, 15) # 屏幕加粗边框
        cv2.putText(img, "WARNING: FCW COLLISION RISK!", (250, 360), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, current_color, 4)

    # --- E. 显示画面 ---
    cv2.imshow(f'ADAS Joint Testing System - {SCENE_NAME}', img)
    
    # 减慢播放速度到 400ms 一帧，方便你肉眼观察危险是怎么发生的
    if cv2.waitKey(400) & 0xFF == ord('q'):
        break
        
    if current_sample['next'] == '':
        break
    current_sample = nusc.get('sample', current_sample['next'])
    frame_idx += 1

cv2.destroyAllWindows()
print("播放结束。")