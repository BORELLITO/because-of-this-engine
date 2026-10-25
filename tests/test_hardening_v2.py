            (root / "captions").mkdir()
            for relative in (
                "script.txt",
                "audio/narration.wav",
                "captions/narration.ass",
                "captions/narration.alignment.json",
                "rendered/hash-test-001-preview.mp4",
            ):
                path = root / relative
                path.write_bytes(b"test")
            manifest = {
                "schema_version": "2.0",
                "video_id": "hash-test-001",
                "job_id": "hash-test-001",
                "output": {"path": "rendered/{video_id}-{mode}.mp4"},
                "script": {"path": "script.txt"},
                "audio": {"path": "audio/narration.wav"},
                "captions": {
                    "path": "captions/narration.ass",
                    "alignment_sidecar": "captions/narration.alignment.json",
                    "alignment_mode": "forced_alignment",
                    "alignment_source": "test",
                    "word_level_available": True,
                },
                "scenes": [{
                    "scene_id": "S01",
                    "duration": 1,
                    "asset": {"asset_id": "asset-001", "sha256": "asset-hash-001"},
                    "visual_match": "EXACT",
                    "visual_truth": "DECLARED_FICTION",
                }],
            }
            (root / "manifest.json").write_bytes(b"manifest")
            (root / "release.json").write_text(json.dumps({"status": "VIDEO_RELEASE_VALIDATED"}), encoding="utf-8")
            (root / "delivery.json").write_text(json.dumps({"status": "DRIVE_VERIFIED"}), encoding="utf-8")
            with patch("production.finalize_manifest.load_manifest", return_value=manifest):
                result = finalize(
                    root / "manifest.json",
                    root / "release.json",
                    root / "delivery.json",
                    "preview",
                )
            self.assertEqual(result["status"], "FINAL_MANIFEST_WRITTEN")
            payload = json.loads((root / "rendered" / "final-manifest-hash-test-001-preview.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["fingerprints"]["footage_sha256"], "0515b3da9dcde5c270e0386efc69ee94f234164ef19f646e750ad56394682546")

    def test_direct_production_scripts_bootstrap_repository_root(self):
        expected = "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))"
        for filename in (
            "production/google_drive_assets.py",
            "production/render_video_episode.py",
            "production/validate_video_release.py",
            "production/finalize_manifest.py",
            "production/quality_gates.py",
        ):
            content = (self.ROOT / filename).read_text(encoding="utf-8")
            self.assertIn(expected, content, filename)


if __name__ == "__main__":
    unittest.main()