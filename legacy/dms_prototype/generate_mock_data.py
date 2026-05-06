import csv
import random
from datetime import datetime, timedelta

def generate_mock_csv(filename="logs/mock_dms_report.csv", rows=300):
    headers = [
        "timestamp", "danger_level", "event_type", "fatigue_level", 
        "distraction_level", "is_fatigue", "is_phone_calling", 
        "is_smoking", "is_yawning", "eye_closure_ratio", 
        "mouth_open_ratio", "ear_baseline"
    ]
    
    start_time = datetime.strptime("16:00:00", "%H:%M:%S")
    baseline = 0.250
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i in range(rows):
            current_time = (start_time + timedelta(seconds=i)).strftime("%H:%M:%S")
            
            # 基础波动 (模拟正常的微小形变)
            ear = baseline + random.uniform(-0.01, 0.01)
            mar = random.uniform(0.01, 0.05)
            
            level = 0
            event = "Normal"
            is_fatigue = is_phone = is_smoke = is_yawn = False
            
            # 模拟随机事件插入
            rand_event = random.randint(1, 100)
            
            if 10 <= rand_event <= 12:  # 模拟偶尔眨眼 (瞬间掉落但不触发报警)
                ear = random.uniform(0.05, 0.12)
            
            elif 20 <= rand_event <= 25:  # 模拟打哈欠 (持续时间较长)
                mar = random.uniform(0.60, 0.85)
                level = 2
                event = "YAWNING DETECTED"
                is_yawn = True
                
            elif 50 <= rand_event <= 55:  # 模拟危险闭眼 (疲劳)
                ear = random.uniform(0.02, 0.08)
                level = 3
                event = "FATIGUE (Closed Eyes)"
                is_fatigue = True
                
            elif rand_event == 90:  # 模拟拿手机
                level = 3
                event = "PHONE CALLING"
                is_phone = True

            writer.writerow([
                current_time, level, event, 
                3 if is_fatigue else 0, 1 if is_phone else 0,
                is_fatigue, is_phone, is_smoke, is_yawn,
                round(ear, 3), round(mar, 3), baseline
            ])
            
    print(f"成功生成模拟数据！已保存至 {filename}")

if __name__ == "__main__":
    generate_mock_csv()