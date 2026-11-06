import json
import unittest
from pathlib import Path

from production.render_v21_manual import validate_request


class ManualRenderGateTests(unittest.TestCase):
    def test_candidate_policy_blocks_manual_render(self) -> None:
        with self.subTest("candidate policy"):
            with __import__("tempfile").TemporaryDirectory() as raw:
                tmp_path = Path(raw)
                record = {
                    "production_enablement": False,
                    "render_contract": {
                        "width": 1080,
                        "height": 1920,
                        "fps": 60,
                        "render_executed": False,
                    },
                }
                policy = tmp_path / "policy.json"
                policy.write_text(
                    json.dumps(
                        {
                            "active_engine_version": "2.1",
                            "canonical_entrypoint": "production/canonical_entrypoint.py",
                            "manual_render_entrypoint": "production/render_v21_manual.py",
                            "publication_policy": "manual_only",
                            "production_enablement": False,
                        }
                    ),
                    encoding="utf-8",
                )
                report = validate_request(record, repo_root=tmp_path, policy_path=policy, mode="final")
                self.assertEqual(report["status"], "V21_MANUAL_RENDER_BLOCKED")
                self.assertEqual(report["render"], "NOT_RUN")
                self.assertTrue(
                    any("production_enablement=false" in item for item in report["failures"])
                )

    def test_final_thumbnail_and_human_authorization_are_required(self) -> None:
        with __import__("tempfile").TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            record = {
                "production_enablement": True,
                "render_authorization": {"status": "PENDING"},
                "render_contract": {
                    "width": 1080,
                    "height": 1920,
                    "fps": 60,
                    "render_executed": False,
                },
            }
            policy = tmp_path / "policy.json"
            policy.write_text(
                json.dumps(
                    {
                        "active_engine_version": "2.1",
                        "canonical_entrypoint": "production/canonical_entrypoint.py",
                        "manual_render_entrypoint": "production/render_v21_manual.py",
                        "publication_policy": "manual_only",
                        "production_enablement": True,
                    }
                ),
                encoding="utf-8",
            )
            report = validate_request(record, repo_root=tmp_path, policy_path=policy, mode="final")
            self.assertEqual(report["status"], "V21_MANUAL_RENDER_BLOCKED")
            self.assertTrue(any("render_authorization" in item for item in report["failures"]))
            self.assertTrue(any("thumbnail_manifest" in item for item in report["failures"]))


    def test_preview_enablement_allows_preflight_without_production(self) -> None:
        with __import__("tempfile").TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            record = {
                "preview_enablement": True,
                "production_enablement": False,
                "render_authorization": {"status": "APPROVED"},
                "render_contract": {
                    "width": 1080,
                    "height": 1920,
                    "fps": 60,
                    "render_executed": False,
                },
                "thumbnail_manifest": {
                    "episode_id": "episode-005",
                    "story_id": "story",
                    "incident_id": "incident",
                    "title_variant": "TITLE",
                    "thumbnail_text": "TEXT",
                    "hero_asset_id": "hero",
                    "visual_truth_class": "MAP_OR_DIAGRAM",
                    "source_url": "https://example.invalid/hero",
                    "rights_status": "APPROVED",
                    "sha256": "a" * 64,
                    "dimensions": [1080, 1920],
                    "safe_margin_status": "PASS",
                    "mobile_legibility_status": "PASS",
                    "human_review_status": "APPROVED",
                    "youtube_thumbnail_mode": "custom_if_supported",
                    "tiktok_cover_mode": "approved_video_frame",
                    "final_status": "APPROVED",
                    "delivery_paths": {
                        "thumbnail_master_9x16_png": "missing.png",
                        "thumbnail_master_9x16_jpg": "missing.jpg",
                        "thumbnail_source_frame": "missing-source.png",
                        "thumbnail_preview_mobile": "missing-mobile.png",
                        "platform_cover_record": "missing.json",
                    },
                },
            }
            policy = tmp_path / "policy.json"
            policy.write_text(
                json.dumps(
                    {
                        "active_engine_version": "2.1",
                        "canonical_entrypoint": "production/canonical_entrypoint.py",
                        "manual_render_entrypoint": "production/render_v21_manual.py",
                        "publication_policy": "manual_only",
                        "preview_enablement": True,
                        "production_enablement": False,
                    }
                ),
                encoding="utf-8",
            )
            report = validate_request(record, repo_root=tmp_path, policy_path=policy, mode="preview")
            self.assertEqual(report["status"], "V21_MANUAL_RENDER_PREFLIGHT_PASS")
            self.assertFalse(report["production_enablement"])
            self.assertTrue(report["preview_enablement"])
            self.assertEqual(report["render"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
