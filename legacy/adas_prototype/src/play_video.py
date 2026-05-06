# -*- coding: utf-8 -*-
import cv2
import os
from nuscenes.nuscenes import NuScenes

# 1. 你的数据集路径
DATAROOT = r'E:\vscode_projects\ADAS\data\nuscenes'

print("正在加载 nuScenes 核心组件...")
nusc = NuScenes(version='v1.0-mini', dataroot=DATAROOT, verbose=False)

scene_name = 'scene-0757'
scene_tokens = [s['token'] for s in nusc.scene if s['name'] == scene_name]

if not scene_tokens:
    print(f"未找到场景 {scene_name}")
    exit()

scene = nusc.get('scene', scene_tokens[0])
current_sample = nusc.get('sample', scene['first_sample_token'])

print(f"开始播放 {scene_name} 的前向摄像头画面...")
print("提示：在播放窗口中按 'Q' 键可随时退出播放。")

frame_idx = 1

while current_sample['token'] != '':
    # 2. 获取前向摄像头的数据记录
    cam_data = nusc.get('sample_data', current_sample['data']['CAM_FRONT'])
    
    # 3. 拼接出这帧照片在电脑上的绝对路径
    img_path = os.path.join(DATAROOT, cam_data['filename'])
    
    # 4. 用 OpenCV 读取图片
    img = cv2.imread(img_path)
    
    # 缩放一下图片，因为原图是 1600x900 的超高清图，普通屏幕可能放不下
    img_resized = cv2.resize(img, (1024, 576)) 
    
    # 在画面左上角打上帧号的水印，方便你和之前的终端输出对齐！
    cv2.putText(img_resized, f"Frame: {frame_idx:03d}", (20, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    # 5. 显示画面
    cv2.imshow(f'nuScenes Playback - {scene_name}', img_resized)
    
    # 等待 500 毫秒 (因为数据集是 2Hz，即每秒2帧，所以每帧真实停留时间为 0.5 秒)
    if cv2.waitKey(500) & 0xFF == ord('q'):
        break
        
    # 步进到下一帧
    if current_sample['next'] == '':
        break
    current_sample = nusc.get('sample', current_sample['next'])
    frame_idx += 1

# 清理窗口
cv2.destroyAllWindows()
print("播放结束。")