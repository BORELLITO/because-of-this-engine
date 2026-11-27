import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "episodes" / "brazil-files" / "episode-001" / "clip-research-seed.json"


class ClipResearchSeedTests(unittest.TestCase):
    def test_seed_never_pretends_selection_or_rights(self):
        data = json.loads(SEED.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "RESEARCH_SEED_PARTIAL_SELECTION_NOT_STARTED")
        self.assertEqual(data["policy"]["rights_status"], "NOT_VERIFIED_PER_ASSET")
        self.assertEqual(data["policy"]["selected_count"], 0)
        self.assertFalse(data["policy"]["production_started"])
        self.assertTrue(all(candidate["decision"] in {"HOLD", "REJECTED"} for beat in data["beats"] for candidate in beat["candidates"]))
        self.assertTrue(all(candidate.get("rights_status", "NOT_VERIFIED_PER_ASSET") == "NOT_VERIFIED_PER_ASSET" for beat in data["beats"] for candidate in beat["candidates"]))

    def test_seed_covers_all_sixteen_beats_and_has_rejections(self):
        data = json.loads(SEED.read_text(encoding="utf-8"))
        self.assertEqual([beat["beat_id"] for beat in data["beats"]], [f"B{i:02d}" for i in range(1, 17)])
        self.assertTrue(any(candidate["decision"] == "REJECTED" for beat in data["beats"] for candidate in beat["candidates"]))


if __name__ == "__main__":
    unittest.main()
