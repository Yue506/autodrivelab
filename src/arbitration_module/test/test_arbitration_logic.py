import unittest

from arbitration_module.iqa_gate import apply_iqa_gate
from arbitration_module.risk_matrix import fuse_adas_dms


class ArbitrationLogicTest(unittest.TestCase):
    def test_risk_matrix_expected_cases(self):
        cases = [
            (0, 0, 0),
            (0, 3, 3),
            (2, 0, 2),
            (2, 3, 3),
            (3, 0, 3),
            (3, 3, 4),
            (4, 0, 4),
            (4, 3, 4),
        ]
        for adas, dms, expected in cases:
            self.assertEqual(fuse_adas_dms(adas, dms), expected)

    def test_iqa_gate_expected_cases(self):
        cfg = {"min_level_when_iqa_level2": 2, "min_level_when_iqa_level3": 2, "mark_degraded_from_level": 2}
        cases = [
            (0, 0, 0, False),
            (0, 1, 1, False),
            (0, 2, 2, True),
            (0, 3, 2, True),
            (2, 2, 2, True),
            (3, 3, 3, True),
            (4, 3, 4, True),
        ]
        for base, iqa_level, expected, degraded in cases:
            final, flag = apply_iqa_gate(base, iqa_level, True, cfg)
            self.assertEqual(final, expected)
            self.assertEqual(flag, degraded)

    def test_invalid_iqa_does_not_gate(self):
        final, degraded = apply_iqa_gate(1, 3, False, {})
        self.assertEqual(final, 1)
        self.assertFalse(degraded)


if __name__ == "__main__":
    unittest.main()
