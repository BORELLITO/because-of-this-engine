from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class StoragePolicyTests(unittest.TestCase):
    def test_actions_artifacts_are_not_used_for_delivery(self):
        offenders = []
        for path in sorted(WORKFLOWS.glob("*.yml")):
            if path.name == "video-engine-ci.yml":
                continue
            text = path.read_text(encoding="utf-8")
            if "actions/upload-" + "artifact" in text:
                offenders.append(path.name)
        self.assertEqual(offenders, [])

    def test_render_is_drive_first_and_fail_closed(self):
        production = (WORKFLOWS / "because-of-this-v7.yml").read_text(encoding="utf-8")
        draft = (WORKFLOWS / "draft-preview.yml").read_text(encoding="utf-8")
        self.assertIn("google_drive_delivery.py --preflight", production)
        self.assertIn('--collection "VIDEOS V7"', production)
        self.assertIn("Deliver only after V7 approval gates pass", production)
        self.assertIn('--collection "PREVIEWS V7"', draft)
        self.assertIn("Deliver verified preview bundle to Drive", draft)
        for text in (production, draft):
            self.assertNotIn("actions/upload-" + "artifact", text)

    def test_drive_delivery_verifies_remote_copy(self):
        text = (ROOT / "production" / "google_drive_delivery.py").read_text(encoding="utf-8")
        self.assertIn("md5Checksum", text)
        self.assertIn("remote_size != local_size", text)
        self.assertIn("checksum mismatch", text)


if __name__ == "__main__":
    unittest.main()


