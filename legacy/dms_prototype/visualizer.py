import cv2
import time
import numpy as np
from core_perception import DmsOutput

class DMSVisualizer:
    def __init__(self):
        self.colors = {
            0: (0, 255, 0),    
            1: (0, 255, 255),  
            2: (0, 165, 255),  
            3: (0, 0, 255)     
        }
        self.prev_time = time.time()
        self.fps_filter = 0

    def render(self, frame, d: DmsOutput, is_calibrated: bool):
        frame = cv2.resize(frame, (640, 480))
        bg_color = (25, 25, 25)
        canvas = np.full((560, 1050, 3), bg_color, dtype=np.uint8)
        
        curr_time = time.time()
        fps = 1 / (curr_time - self.prev_time) if (curr_time - self.prev_time) > 0 else 0
        self.prev_time = curr_time
        self.fps_filter = self.fps_filter * 0.9 + fps * 0.1

        # 左侧实时画面
        canvas[40:520, 40:680] = frame
        cv2.rectangle(canvas, (38, 38), (682, 522), (100, 100, 100), 2)
        cv2.putText(canvas, "LIVE CABIN FEED", (40, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

        # 右侧 UI 控制面板
        panel_x = 720
        ui_color = self.colors.get(d.danger_level, (255, 255, 255))
        
        cv2.putText(canvas, "DMS PERCEPTION DOMAIN", (panel_x, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(canvas, f"SYS TIME: {d.timestamp}", (panel_x, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        cv2.line(canvas, (panel_x, 110), (1000, 110), (100, 100, 100), 1)

        if not is_calibrated:
            cv2.putText(canvas, "SYSTEM INITIALIZING...", (panel_x, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(canvas, "Please keep eyes open", (panel_x, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        else:
            # 核心状态区
            cv2.putText(canvas, "CURRENT STATUS:", (panel_x, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(canvas, f"LEVEL {d.danger_level}", (panel_x, 180), cv2.FONT_HERSHEY_DUPLEX, 1.2, ui_color, 2)
            cv2.putText(canvas, d.event_type, (panel_x, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.7, ui_color, 2)

            # 动态 EAR 条形进度条
            cv2.putText(canvas, f"EYE OPENNESS (EAR): {d.eye_closure_ratio:.3f}", (panel_x, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            bar_w = 280
            bar_h = 15
            fill_ratio = min(1.0, max(0.0, d.eye_closure_ratio / (d.ear_baseline * 1.5 + 0.001)))
            fill_w = int(bar_w * fill_ratio)
            
            cv2.rectangle(canvas, (panel_x, 285), (panel_x + bar_w, 285 + bar_h), (80, 80, 80), 2)
            if fill_w > 0:
                cv2.rectangle(canvas, (panel_x + 2, 287), (panel_x + fill_w - 2, 285 + bar_h - 2), ui_color, -1)
            thresh_x = panel_x + int(bar_w * (d.ear_baseline * 0.75 / (d.ear_baseline * 1.5 + 0.001)))
            cv2.line(canvas, (thresh_x, 280), (thresh_x, 305), (0, 0, 255), 2)

            # 新增：动态 MAR 数据展示
            cv2.putText(canvas, f"MOUTH OPEN (MAR): {d.mouth_open_ratio:.3f}", (panel_x, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # 布尔状态指示灯阵列 (加入打哈欠)
            y_offset = 370
            bool_stats = [
                ("Fatigue (Eyes)", d.is_fatigue),
                ("Phone Usage", d.is_phone_calling),
                ("Yawning", d.is_yawning),
                ("Smoking", d.is_smoking)
            ]
            for label, status in bool_stats:
                box_color = (0, 0, 255) if status else (0, 255, 0)
                cv2.circle(canvas, (panel_x + 10, y_offset - 5), 6, box_color, -1)
                cv2.putText(canvas, label, (panel_x + 30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                y_offset += 30

        # 底部性能状态
        cv2.line(canvas, (panel_x, 490), (1000, 490), (100, 100, 100), 1)
        cv2.putText(canvas, f"FPS: {int(self.fps_filter)} | ENGINE: YOLOv8 + MediaPipe", (panel_x, 515), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        # 危险屏幕红框反馈
        if d.danger_level == 3 and int(time.time() * 5) % 2 == 0:
            cv2.rectangle(canvas, (0, 0), (1050, 560), (0, 0, 255), 8)

        return canvas