import unittest

from production.quality_gates import GATES


class CanonicalGateTests(unittest.TestCase):
    def test_canonical_gates_are_complete_and_ordered(self):
        self.assertEqual([code for code, _ in GATES], [f"G{index}" for index in range(12)])
        self.assertEqual(GATES[0][1], "PRE_FLIGHT")
        self.assertEqual(GATES[-1][1], "POST_PUBLICATION")


if __name__ == "__main__":
    unittest.main()
