std_msgs/Header header
string camera_name

# Legacy image quality fields used by iqa_monitor.
float32 blur_score
float32 brightness
float32 occlusion_score
bool usable
string reason

# IQA arbitration fields.
string quality_state
float32 soiling_score
bool is_soiled
bool is_critical
