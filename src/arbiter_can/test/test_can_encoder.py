from types import SimpleNamespace

from arbiter_can.can_encoder import encode_fusion_to_can_frame


def test_encode_fusion_to_can_frame_demo_mapping():
    msg = {
        "unified_risk_level": 4,
        "primary_event": "FCW_WARNING",
        "primary_source": "ADAS",
        "source_status": {
            "adas_valid": True,
            "dms_valid": True,
            "iqa_valid": True,
            "perception_degraded": True,
            "iqa_level": 3,
            "soiled_camera_count": 1,
        },
    }

    frame = encode_fusion_to_can_frame(msg, rolling_counter=7)

    assert frame.can_id == 0x321
    assert frame.semantic_name == "FUSION_RISK_STATUS"
    assert frame.is_extended is False
    assert list(frame.data[:7]) == [4, 0x0F, 1, 3, 1, 1, 7]
    assert frame.data[7] == sum(list(frame.data[:7])) & 0xFF


def test_encode_fusion_to_can_frame_accepts_ros_like_object():
    source_status = SimpleNamespace(
        adas_valid=True,
        dms_valid=False,
        iqa_valid=True,
        perception_degraded=False,
        iqa_level=2,
        soiled_camera_count=2,
    )
    msg = SimpleNamespace(
        unified_risk_level=2,
        primary_event="CAMERA_SOILING",
        primary_source="IQA",
        source_status=source_status,
    )

    frame = encode_fusion_to_can_frame(msg)

    assert list(frame.data[:6]) == [2, 0x05, 20, 2, 2, 3]
    assert frame.data[7] == sum(list(frame.data[:7])) & 0xFF
