from .utils import clamp_int


RISK_MATRIX = {
    0: {0: 0, 1: 1, 2: 2, 3: 3},
    1: {0: 1, 1: 1, 2: 2, 3: 2},
    2: {0: 2, 1: 2, 2: 3, 3: 3},
    3: {0: 3, 1: 3, 2: 4, 3: 4},
    4: {0: 4, 1: 4, 2: 4, 3: 4},
}


def fuse_adas_dms(adas_level, dms_level, adas_valid=True, dms_valid=True):
    if not adas_valid and not dms_valid:
        return 0
    adas_level = clamp_int(adas_level, 0, 4)
    dms_level = clamp_int(dms_level, 0, 3)
    if adas_valid and adas_level >= 4:
        return 4
    if adas_valid and not dms_valid:
        return adas_level
    if not adas_valid and dms_valid:
        return dms_level
    return RISK_MATRIX[adas_level][dms_level]
