import unittest
from pathlib import Path

from production.active_surface_lock_v21 import audit


class ActiveSurfaceLockTest(unittest.TestCase):
    def test_active_surface_lock_passes(self):
        report = audit(Path(__file__).resolve().parents[1])
        self.assertEqual(report["status"], "ACTIVE_SURFACE_LOCK_PASS", report)
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
