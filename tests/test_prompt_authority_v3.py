import tempfile
import unittest
from pathlib import Path

from production.prompt_authority_v3 import PROMPT_SHA256, validate_prompt_authority


class PromptAuthorityV3Tests(unittest.TestCase):
    def test_policy_requires_prompt_v3(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt = root / "docs" / "PROMPT_MESTRE_BECAUSE_OF_THIS_V3.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_bytes(b"wrong")
            report = validate_prompt_authority(
                root,
                {
                    "master_prompt_version": "V2.1",
                    "master_prompt_path": str(prompt),
                    "master_prompt_sha256": "wrong",
                },
            )
            self.assertEqual(report["status"], "PROMPT_AUTHORITY_BLOCKED")
            self.assertTrue(report["failures"])

    def test_declared_digest_is_fixed(self):
        self.assertEqual(len(PROMPT_SHA256), 64)


if __name__ == "__main__":
    unittest.main()
