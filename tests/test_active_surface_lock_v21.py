import tempfile
import unittest
from pathlib import Path

from production.active_surface_lock_v21 import _legacy_imports, audit


class ActiveSurfaceLockTest(unittest.TestCase):
    def test_active_surface_lock_passes(self):
        report = audit(Path(__file__).resolve().parents[1])
        self.assertEqual(report["status"], "ACTIVE_SURFACE_LOCK_PASS", report)
        self.assertEqual(report["failures"], [])

    def test_retired_runtime_import_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            production = root / "production"
            production.mkdir()
            (production / "active_helper.py").write_text(
                "from production.piper_tts import synthesize\n",
                encoding="utf-8",
            )
            failures = _legacy_imports(root)
            self.assertEqual(
                failures,
                ["active module imports retired runtime:active_helper.py->production.piper_tts"],
            )


if __name__ == "__main__":
    unittest.main()
