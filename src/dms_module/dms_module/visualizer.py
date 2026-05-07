def draw_dms_overlay(frame, event, perception_result):
    try:
        import cv2
    except Exception:
        return frame

    if frame is None:
        return frame
    text = f"DMS L{event.danger_level} {event.event_type} valid={event.valid}"
    cv2.putText(frame, text, (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    metrics = f"EAR={perception_result.eye_closure_ratio:.2f} MAR={perception_result.mouth_open_ratio:.2f} {perception_result.latency_ms:.1f}ms"
    cv2.putText(frame, metrics, (20, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    return frame
