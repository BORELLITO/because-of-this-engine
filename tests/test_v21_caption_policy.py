import json
import tempfile
import unittest
from pathlib import Path

from production.caption_style_v21 import (
    caption_ass_style_line,
    default_active_word_color,
    validate_caption_text,
)
from production.v21_singleton_guard import audit


class V21CaptionPolicyTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def test_policy_is_scoped_and_locked(self):
        policy = json.loads((self.ROOT / "production/caption_policy_v21.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["project"], "Because Of This Stories")
        self.assertEqual(policy["runtime"], "because_of_this_v21")
        self.assertEqual(policy["forbidden_caption_characters"], ["—", "–"])
        self.assertEqual(policy["layout"]["margin_v"], 650)
        self.assertEqual(policy["layout"]["max_lines"], 2)
        self.assertEqual(default_active_word_color(), "#F04444")
        self.assertIn(",650,1", caption_ass_style_line())

    def test_em_and_en_dash_are_rejected_but_internal_hyphen_is_allowed(self):
        validate_caption_text("The B-52 crossed the sky.")
        with self.assertRaisesRegex(ValueError, "forbidden dash"):
            validate_caption_text("The aircraft vanished — without a trace.")
        with self.assertRaisesRegex(ValueError, "forbidden dash"):
            validate_caption_text("The aircraft vanished – without a trace.")

    def test_singleton_guard_requires_active_caption_policy(self):
        result = audit(self.ROOT)
        self.assertEqual(result["status"], "V21_SINGLETON_PASS", result)

    def test_singleton_guard_blocks_caption_policy_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "production").mkdir(parents=True)
            for path in (self.ROOT / "production").glob("*.py"):
                (root / "production" / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            for path in (self.ROOT / "production").glob("*.json"):
                (root / "production" / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            policy_path = root / "production/active_engine_policy.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            (root / "production/caption_policy_v21.json").write_text(
                json.dumps({"project": "Other Project", "runtime": "other", "layout": {}, "alignment": {}, "forbidden_caption_characters": []}),
                encoding="utf-8",
            )
            (root / ".github/workflows").mkdir(parents=True)
            for path in (self.ROOT / ".github/workflows").glob("*.yml"):
                (root / ".github/workflows" / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            result = audit(root)
            self.assertEqual(result["status"], "V21_SINGLETON_BLOCKED")
            self.assertTrue(any("caption policy is not scoped" in failure for failure in result["failures"]))


if __name__ == "__main__":
    unittest.main()
