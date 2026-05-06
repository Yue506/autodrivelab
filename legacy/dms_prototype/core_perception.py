import cv2
import time
import csv
import os
import math
import threading
import mediapipe as mp
from ultralytics import YOLO
from dataclasses import dataclass, asdict
import winsound

@dataclass
class DmsOutput:
    timestamp: str
    danger_level: int       
    event_type: str         
    fatigue_level: int      
    distraction_level: int  
    is_fatigue: bool
    is_phone_calling: bool
    is_smoking: bool
    is_yawning: bool         
    eye_closure_ratio: float 
    mouth_open_ratio: float  
    ear_baseline: float      

class DMSProcessor:
    def __init__(self, config: dict):
        self.cfg = config
        self.yolo = YOLO(self.cfg['hardware']['model_path'])
        self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True
        )
        self.calibrated = False
        self.calib_data = []
        self.ear_base = 0.25 
        
        self.fatigue_counter = 0
        self.warning_counter = 0

        # --- 🛠️ 核心修复：引入 Event 机制，实现毫秒级瞬间打断 ---
        self.current_alarm_level = 0  
        self.stop_event = threading.Event()  # 线程终止信号灯
        self.alarm_thread = threading.Thread(target=self._alarm_worker, daemon=True)
        self.alarm_thread.start()
        
        self._init_csv_logger()

    def stop(self):
        """引擎销毁指令：释放信号灯，线程瞬间死亡"""
        self.stop_event.set()
        self.current_alarm_level = 0
        # 发送空音频冲刷 Windows 缓冲区
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except:
            pass

    def _init_csv_logger(self):
        if not self.cfg['features']['save_csv']: return
        self.csv_path = self.cfg['features']['csv_path']
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=DmsOutput.__dataclass_fields__.keys()).writeheader()

    def _alarm_worker(self):
        """后台守护线程：只要 stop_event 未被触发，就持续轮询"""
        while not self.stop_event.is_set():
            if not self.cfg['features']['enable_alarm']:
                self.stop_event.wait(0.5)
                continue

            level = self.current_alarm_level
            if level == 3:
                winsound.Beep(1000, 150)
                # 使用 wait 代替 sleep，可以在休眠中途被瞬间唤醒并打断！
                self.stop_event.wait(0.1) 
            elif level == 2:
                winsound.Beep(600, 250)
                self.stop_event.wait(0.3)
            else:
                self.stop_event.wait(0.05) # 静默状态，高频检测

    def _euclidean_distance(self, p1, p2, w, h):
        return math.hypot((p1.x - p2.x) * w, (p1.y - p2.y) * h)

    def _calculate_ear(self, landmarks, w, h) -> float:
        v1 = self._euclidean_distance(landmarks[159], landmarks[145], w, h)
        v2 = self._euclidean_distance(landmarks[158], landmarks[153], w, h)
        h1 = self._euclidean_distance(landmarks[33], landmarks[133], w, h)
        return (v1 + v2) / (2.0 * h1) if h1 != 0 else 0.2

    def _calculate_mar(self, landmarks, w, h) -> float:
        v_mouth = self._euclidean_distance(landmarks[13], landmarks[14], w, h)
        h_mouth = self._euclidean_distance(landmarks[78], landmarks[308], w, h)
        return v_mouth / h_mouth if h_mouth != 0 else 0.0

    def process(self, frame) -> DmsOutput:
        h, w, _ = frame.shape
        yolo_results = self.yolo(frame, verbose=False)
        fm_results = self.mp_face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        has_phone = any(self.yolo.names[int(b.cls[0])] == 'cell phone' for r in yolo_results for b in r.boxes)
        has_smoke = any(self.yolo.names[int(b.cls[0])] == 'cigarette' for r in yolo_results for b in r.boxes)
        
        current_ear = 0.25
        current_mar = 0.0
        if fm_results.multi_face_landmarks:
            landmarks = fm_results.multi_face_landmarks[0].landmark
            current_ear = self._calculate_ear(landmarks, w, h)
            current_mar = self._calculate_mar(landmarks, w, h)

        if not self.calibrated:
            self.calib_data.append(current_ear)
            if len(self.calib_data) >= self.cfg['calibration']['duration_frames']:
                sorted_data = sorted(self.calib_data)
                valid_data = sorted_data[10:-10] if len(sorted_data) > 20 else sorted_data
                self.ear_base = sum(valid_data) / len(valid_data)
                self.calibrated = True
            return self._build_output(0, "SYSTEM CALIBRATING...", current_ear, current_mar, False, False, False)

        level = 0
        event = "Normal"
        dynamic_ear_thresh = self.ear_base * self.cfg['calibration']['sensitivity_factor']
        yawn_thresh = self.cfg['thresholds'].get('yawn_ratio', 0.5) 

        is_eyes_closed = current_ear < dynamic_ear_thresh
        is_yawning = current_mar > yawn_thresh

        # 1. 危险判定
        if is_eyes_closed or has_phone:
            self.fatigue_counter += 1
            if self.fatigue_counter >= self.cfg['thresholds']['confirm_frames']:
                level = 3
                event = "FATIGUE (Closed Eyes)" if is_eyes_closed else "PHONE CALLING"
        else:
            self.fatigue_counter = 0  

        # 2. 警告判定
        if level < 3:
            if is_yawning or has_smoke:
                self.warning_counter += 1
                if self.warning_counter >= 3: 
                    level = 2
                    event = "YAWNING DETECTED" if is_yawning else "SMOKING DETECTED"
            else:
                self.warning_counter = 0

        # --- 强制底层同步指令 ---
        if level >= 2:
            self.current_alarm_level = level
        else:
            self.current_alarm_level = 0 

        output = self._build_output(level, event, current_ear, current_mar, has_phone, has_smoke, is_yawning)
        
        if self.cfg['features']['save_csv']:
            try:
                with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                    csv.DictWriter(f, fieldnames=asdict(output).keys()).writerow(asdict(output))
            except PermissionError: pass
            
        return output

    def _build_output(self, level, event, ear, mar, phone, smoke, yawn) -> DmsOutput:
        return DmsOutput(
            timestamp=time.strftime("%H:%M:%S"),
            danger_level=level, event_type=event,
            fatigue_level=level if "FATIGUE" in event else 0,
            distraction_level=1 if event == "DISTRACTED" else 0,
            is_fatigue=(level == 3 and "FATIGUE" in event),
            is_phone_calling=phone, is_smoking=smoke, is_yawning=yawn,
            eye_closure_ratio=round(ear, 3), mouth_open_ratio=round(mar, 3),
            ear_baseline=round(self.ear_base, 3)
        )