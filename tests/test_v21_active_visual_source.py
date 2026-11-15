"""Regression tests for the single active V2.1 visual source gate."""
from __future__ import annotations
import json
import unittest
from pathlib import Path
from production.active_visual_source_v21 import EPISODE005_MANIFEST, forbidden_concept_hits, validate_scene_manifest
ROOT=Path(__file__).resolve().parents[1]
class ActiveVisualSourceV21Tests(unittest.TestCase):
    def test_episode005_complete_manifest_passes_source_gate(self):
        manifest=json.loads((ROOT/EPISODE005_MANIFEST).read_text(encoding="utf-8"))
        report=validate_scene_manifest(manifest,EPISODE005_MANIFEST)
        self.assertEqual(report["status"],"PASS",report)
        self.assertEqual(report["unresolved_shots"],[])
        self.assertEqual(report["asset_count"],16)
        self.assertEqual(report["assigned_shot_count"],16)
        self.assertEqual(report["forbidden_concept_hits"],{},report)
    def test_clock_candidate_is_rejected_by_editorial_exclusion(self):
        candidate={"candidate_id":"mixkit-clock-mechanism-3651","title":"Mechanism of a working clock","source_page_url":"https://mixkit.co/free-stock-video/mechanism-of-a-working-clock-3651/"}
        self.assertIn("clock",forbidden_concept_hits(candidate,["clock","alarm clock","timepiece","clock mechanism"]))
    def test_nasa_candidate_is_rejected_by_editorial_exclusion(self):
        candidate={"candidate_id":"nasa-svs-geos5-clouds-no-labels-4819","provider":"nasa","source_page_url":"https://svs.gsfc.nasa.gov/4819/"}
        self.assertIn("nasa",forbidden_concept_hits(candidate,["nasa"]))
    def test_active_manifest_has_no_clock_or_nasa_asset(self):
        manifest=json.loads((ROOT/EPISODE005_MANIFEST).read_text(encoding="utf-8"))
        active_ids={item["candidate_id"] for item in manifest["assets"]}
        providers={str(item.get("provider","")).lower() for item in manifest["assets"]}
        self.assertFalse(any("clock" in item.lower() for item in active_ids))
        self.assertNotIn("nasa",providers)
        self.assertNotIn("nasa-svs-geos5-clouds-no-labels-4819",active_ids)
if __name__=="__main__": unittest.main()
