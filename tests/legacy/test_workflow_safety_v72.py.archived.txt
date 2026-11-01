from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class V72WorkflowSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=(ROOT/".github/workflows/draft-preview.yml").read_text()
        cls.p=(ROOT/".github/workflows/because-of-this-v7.yml").read_text()
    def test_original_preview_is_skipped_when_verified(self):
        self.assertIn("needs: preflight-reuse",self.d)
        self.assertIn("if: needs.preflight-reuse.outputs.existing_preview != 'true'",self.d)
        self.assertIn("verify_drive_receipt.py",self.d)
    def test_both_workflows_use_same_media_lock(self):
        self.assertIn("group: because-of-this-v7-media-global",self.d)
        self.assertIn("group: because-of-this-v7-media-global",self.p)
        self.assertIn("cancel-in-progress: false",self.d)
    def test_piper_cached_without_silent_fallback(self):
        for body in (self.d,self.p):
            self.assertIn("production/narration_cache.py",body)
            self.assertIn("--restore",body)
            self.assertIn("--store",body)
            self.assertIn("if: env.PIPER_CACHE_HIT != 'true'",body)
            self.assertNotIn("production/edge_tts.py",body)
            self.assertNotIn("production/cloud_tts.py",body)
    def test_future_captions_archived_for_recovery(self):
        self.assertIn('--path "episodes/video-001/captions"',self.d)
        self.assertIn('--path "${EPISODE_DIR}/captions"',self.p)
    def test_manual_only_publication(self):
        self.assertIn('No production approval or publication was recorded.',self.d)
        self.assertIn('no automatic platform publication is permitted',self.p)
if __name__=="__main__":unittest.main()
