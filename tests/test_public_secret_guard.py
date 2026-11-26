from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from production.public_secret_guard import scan_paths


ROOT = Path(__file__).resolve().parents[1]


class PublicSecretGuardTests(unittest.TestCase):
    def test_current_repository_passes(self):
        report = scan_paths(ROOT)
        self.assertEqual(report["status"], "PUBLIC_SECRET_GUARD_PASS", report)

    def test_private_key_is_blocked_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.txt"
            candidate.write_text(
                "-----BEGIN OPENSSH PRIVATE KEY-----\nsecret-material\n",
                encoding="utf-8",
            )
            report = scan_paths(root, [candidate])
            self.assertEqual(report["status"], "PUBLIC_SECRET_GUARD_BLOCKED")
            self.assertEqual(report["failures"][0]["rule"], "private-key")
            self.assertNotIn("secret-material", str(report))

    def test_github_token_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.txt"
            candidate.write_text("ghp_123456789012345678901234567890\n", encoding="utf-8")
            report = scan_paths(root, [candidate])
            self.assertEqual(report["status"], "PUBLIC_SECRET_GUARD_BLOCKED")
            self.assertEqual(report["failures"][0]["rule"], "github-token")


if __name__ == "__main__":
    unittest.main()
