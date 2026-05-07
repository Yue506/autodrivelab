bool adas_valid
bool dms_valid
bool iqa_valid

builtin_interfaces/Time adas_stamp
builtin_interfaces/Time dms_stamp
builtin_interfaces/Time iqa_stamp

float32 adas_age_ms
float32 dms_age_ms
float32 iqa_age_ms
float32 adas_dms_time_diff_ms
float32 fusion_latency_ms

bool adas_timeout
bool dms_timeout
bool iqa_timeout

bool perception_degraded
int32 iqa_level
int32 soiled_camera_count
string[] soiled_cameras
bool critical_camera_soiled
