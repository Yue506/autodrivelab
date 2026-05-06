import cv2
import yaml
import os
import sys
from core_perception import DMSProcessor
from visualizer import DMSVisualizer

def load_config(config_path="config.yaml"):
    if not os.path.exists(config_path):
        print(f"[ERROR] 找不到配置文件: {config_path}")
        sys.exit(1)
    with open(config_path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    print("="*50)
    print("自动驾驶座舱感知域 (DMS Module) - 毕设启动中")
    print("="*50)

    config = load_config()
    processor = DMSProcessor(config)
    visualizer = DMSVisualizer()
    
    csv_path = config.get('features', {}).get('csv_path', './logs/dms_report.csv')
    print(f"[INFO] 引擎就绪。数据流导出至: {os.path.abspath(csv_path)}")

    cap = cv2.VideoCapture(config.get('hardware', {}).get('camera_source', 0))
    if not cap.isOpened():
        print("[ERROR] 无法打开视频流！")
        sys.exit(1)

    window_name = "ADAS DMS Dashboard - Graduation Project"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1050, 560)         

    while True:
        ret, frame = cap.read()
        if not ret: break

        dms_info = processor.process(frame)
        dashboard_frame = visualizer.render(frame, dms_info, processor.calibrated)

        cv2.imshow(window_name, dashboard_frame)
        
        # 退出捕获逻辑
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n[INFO] 接收到退出指令，正在硬阻断音频...")
            processor.stop()  # 1. 释放终止信号灯
            break

    # 释放系统资源
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] 运行结束！")
    
    # 2. 终极必杀：强制终结当前 Python 进程，不给任何“僵尸环境”留活路
    os._exit(0) 

if __name__ == "__main__":
    main()