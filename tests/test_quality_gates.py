import unittest

from production.quality_gates import GATES


class CanonicalGateTests(unittest.TestCase):
    def test_canonical_gates_are_complete_and_ordered(self):
        self.assertEqual([code for code, _ in GATES], [f"G{index}" for index in range(13)])
        self.assertEqual(GATES[0][1], "CONFIG")
        self.assertEqual(GATES[-1][1], "CLEANUP")


if __name__ == "__main__":
    unittest.main()
