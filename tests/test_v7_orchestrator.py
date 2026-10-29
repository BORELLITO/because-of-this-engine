import json
import tempfile
import unittest
from pathlib import Path

from production.v7_orchestrator import _artifact_gate, evaluate


ROOT = Path(__file__).resolve().parents[1]


class V7OrchestratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest_path = ROOT / "episodes/video-001/manifest.json"
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    def test_contract_mode_defers_runtime_evidence_without_blocking(self):
        report = evaluate(
            self.manifest,
            repo_root=ROOT,
            manifest_dir=self.manifest_path.parent,
            mode="contract",
        )
        self.assertEqual(report["status"], "V7_PREFLIGHT_PASS")
        self.assertEqual(report["blocking_gates"], [])

    def test_hydrated_preflight_blocks_missing_assets_and_music(self):
        report = evaluate(
            self.manifest,
            repo_root=ROOT,
            manifest_dir=self.manifest_path.parent,
            mode="preflight",
        )
        self.assertEqual(report["status"], "V7_PREFLIGHT_BLOCKED")
        self.assertEqual(report["blocking_gates"], ["G3", "G5"])

    def test_artifact_gate_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "rendered" / "preview.mp4"
            artifact.parent.mkdir()
            artifact.write_bytes(b"actual")
            manifest = {
                "runtime_artifacts": {"preview": "rendered/preview.mp4"},
                "runtime_artifact_hashes": {"preview": "0" * 64},
            }
            check = _artifact_gate(manifest, root, ("preview",), "preview", blocking=True)
            self.assertEqual(check["status"], "BLOCKED")
            self.assertIn("sha256 mismatch", check["evidence"])


if __name__ == "__main__":
    unittest.main()
