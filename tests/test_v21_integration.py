from __future__ import annotations

import copy
import unittest
from pathlib import Path

from production.canonical_entrypoint import evaluate
from production.package_gate_pre import evaluate_package_gate
from production.ledgers_v21 import load_registry
from production.pipeline_state_v21 import StateTransitionError, advance


def historical_registry() -> list[dict]:
    return [
        {
            "asset_id": "historical-asset-001",
            "provider": "fixture",
            "provider_asset_id": "historical-source-001",
            "source_url": "https://example.test/historical",
            "sha256": "b" * 64,
            "perceptual_fingerprint": "phash-historical-001",
            "incident_id": "historical-incident-001",
            "story_id": "historical-story-001",
        }
    ]


def valid_manifest() -> dict:
    return {
        "implementation_id": "IMPL-V21-20261105-01",
        "audit_id": "AUDIT-V21-20261105-01",
        "episode_id": "episode-v21-fixture",
        "story_id": "story-v21-fixture",
        "editorial_mode": "factual_documentary",
        "pillar": "human_or_system_failure",
        "series_id": "pilot-factual-001",
        "incident_id": "incident-fixture-001",
        "central_question": "How did one maintenance decision turn a routine failure into a survival event?",
        "audience_promise": "A real system failure, the decision that worsened it, and the consequence nobody could reverse.",
        "impossible_event": "A safety system repeatedly reported normal conditions while the structure was already failing.",
        "human_anchor": "A night-shift technician had seconds to decide whether to trust the panel or the sound behind it.",
        "causal_hinge": "The technician silenced the alarm to reach a trapped worker.",
        "causal_chain": ["alarm drifted", "alarm was silenced", "structure failed", "worker survived with permanent cost"],
        "proof_level": "primary_plus_corroboration",
        "proof_assets": ["incident report", "maintenance log"],
        "visual_truth_classes": ["DOCUMENTARY_EVIDENCE", "ARCHIVAL_MATERIAL", "MAP_OR_DIAGRAM"],
        "visual_representation_by_stage": ["alarm panel", "maintenance log", "structural diagram"],
        "escalation_beats": ["false normal", "silenced alarm", "collapse", "survival"],
        "irreversible_choice": "The technician enters the failing section after silencing the alarm.",
        "payoff": "The final log shows the alarm was right before anyone believed it.",
        "title_candidates": ["THE ALARM THAT SAID EVERYTHING WAS SAFE", "THE SYSTEM FAILED BEFORE THE BUILDING DID", "HE SILENCED THE WARNING"],
        "opening_frame": "A warning panel shows NORMAL while dust falls from the ceiling.",
        "opening_sentence": "The panel said NORMAL. The ceiling was already coming down.",
        "package_variants": [{"title": "THE ALARM THAT SAID EVERYTHING WAS SAFE", "thumbnail_text": "NORMAL?"}],
        "next_video_bridge": "A related story about a warning ignored at the exact wrong second.",
        "source_ledger_id": "source-ledger-fixture-001",
        "rights_ledger_id": "rights-ledger-fixture-001",
        "reuse_scope": "global",
        "story_score": 10,
        "package_status": "PENDING_HUMAN_APPROVAL",
        "human_editor_status": "PENDING",
        "thumbnail_concept_id": "thumb-concept-fixture-001",
        "thumbnail_manifest_id": "thumb-manifest-fixture-001",
        "thumbnail_status": "CONCEPT_READY",
        "platform_thumbnail_mode": {"youtube_shorts": "custom_if_supported", "tiktok": "approved_video_frame"},
        "pipeline_state": "DRAFT",
        "production_enablement": False,
        "audio_contract": {
            "source": "final_audio",
            "status": "OFFLINE_CONTRACT_VERIFIED",
            "real_audio_generated": False,
            "final_transcription_required": True,
            "target_duration_seconds": 65,
            "adapter": "production/microsoft_edge_tts.py",
        },
        "captions_contract": {
            "source": "final_audio_transcription",
            "word_level": True,
            "status": "OFFLINE_CONTRACT_VERIFIED",
            "real_caption_generated": False,
            "safe_zone_status": "PENDING_REAL_CAPTURE",
            "source_audio_sha256": "d" * 64,
            "adapter": "production/align_captions.py",
        },
        "render_contract": {
            "width": 1080,
            "height": 1920,
            "fps": 60,
            "status": "OFFLINE_CONTRACT_VERIFIED",
            "render_executed": False,
            "duration_target_seconds": 65,
            "adapter": "production/render_video_episode.py",
        },
        "drive_contract": {
            "mode": "read_only",
            "write_authorized": False,
            "status": "OFFLINE_CONTRACT_VERIFIED",
            "receipt_status": "NOT_RUN",
            "assets_adapter": "production/google_drive_assets.py",
            "delivery_adapter": "production/google_drive_delivery.py",
        },
        "tts_contract": {
            "provider": "microsoft_edge_tts",
            "voice_name": "en-US-ChristopherNeural",
            "language_code": "en-US",
            "model": "edge_neural",
            "provider_fallback": "forbidden",
            "status": "OFFLINE_CONTRACT_VERIFIED",
            "real_call_authorized": False,
            "request_count": 0,
            "script_sha256": "c" * 64,
            "estimated_characters": 900,
            "character_budget": 10000,
            "estimated_duration_seconds": 65,
        },
        "factuality_status": "PENDING",
        "safety_status": "READY",
        "thumbnail_concept": {
            "concept_id": "thumb-concept-fixture-001",
            "title_alignment": "same alarm failure as title",
            "hero_visual": "warning panel with falling dust",
            "thumbnail_text": "NORMAL?",
            "visual_truth_class": "MAP_OR_DIAGRAM",
        },
        "thumbnail_manifest": {
            "episode_id": "episode-v21-fixture",
            "story_id": "story-v21-fixture",
            "incident_id": "incident-fixture-001",
            "title_variant": "THE ALARM THAT SAID EVERYTHING WAS SAFE",
            "thumbnail_text": "NORMAL?",
            "hero_asset_id": "fixture-asset-001",
            "visual_truth_class": "MAP_OR_DIAGRAM",
            "source_url": "https://example.test/asset",
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
                "thumbnail_master_9x16_png": "episodes/episode-v21-fixture/delivery/thumbnail/thumbnail_master_9x16.png",
                "thumbnail_master_9x16_jpg": "episodes/episode-v21-fixture/delivery/thumbnail/thumbnail_master_9x16.jpg",
                "thumbnail_source_frame": "episodes/episode-v21-fixture/delivery/thumbnail/source-frame.png",
                "thumbnail_preview_mobile": "episodes/episode-v21-fixture/delivery/thumbnail/thumbnail_preview_mobile.png",
                "platform_cover_record": "episodes/episode-v21-fixture/delivery/thumbnail/platform-cover-record.json",
            },
        },
        "question_answers": {
            "what_happened": "A real safety system misreported a dangerous structural failure.",
            "why_it_happened": "A maintenance decision suppressed the warning.",
            "who_was_affected": "The technician and the trapped worker.",
            "what_changed_everything": "The alarm was silenced.",
            "why_it_seems_impossible": "The system displayed normal conditions as the structure failed.",
            "proof_or_source_note": "Incident report plus maintenance log.",
            "how_danger_grows": "False normal becomes silence, then collapse.",
            "irreversible_consequence": "The technician enters and cannot undo the collapse.",
            "visual_representation_by_stage": "Each stage has a documented visual class.",
            "first_frame_promise": "The normal warning is visibly contradicted.",
        },
        "source_ledger": [
            {
                "claim_id": "C1",
                "claim_text": "The panel displayed normal before the collapse.",
                "source_url": "https://example.test/incident-report",
                "source_type": "incident_report",
                "publisher_or_author": "Safety Board",
                "publication_date": "2024-01-01",
                "primary_or_secondary": "primary",
                "corroboration_source": "maintenance-log",
                "reliability_notes": "official incident record",
                "accessed_at": "2026-11-05T00:00:00Z",
                "evidence_excerpt_or_note": "panel state recorded at 02:14",
                "visual_support": "CCTV frame",
                "fact_check_status": "VERIFIED",
            },
            {
                "claim_id": "C1",
                "claim_text": "The panel displayed normal before the collapse.",
                "source_url": "https://example.test/maintenance-log",
                "source_type": "maintenance_log",
                "publisher_or_author": "Independent Investigator",
                "publication_date": "2024-01-02",
                "primary_or_secondary": "secondary",
                "corroboration_source": "incident-report",
                "reliability_notes": "independent technical review",
                "accessed_at": "2026-11-05T00:00:00Z",
                "evidence_excerpt_or_note": "maintenance entry corroborates timestamp",
                "visual_support": "log scan",
                "fact_check_status": "VERIFIED",
            },
        ],
        "rights_ledger": [
            {
                "asset_id": "fixture-asset-001",
                "source_url": "https://example.test/asset",
                "provider": "fixture",
                "author": "fixture-author",
                "license_name": "CC BY 4.0",
                "commercial_use": True,
                "platform_scope": ["youtube_shorts", "tiktok"],
                "download_date": "2026-11-05",
                "license_evidence": "https://example.test/license",
                "sha256": "a" * 64,
                "perceptual_fingerprint": "phash-fixture-001",
                "incident_id": "incident-fixture-001",
                "used_by": ["episode-v21-fixture"],
                "rights_status": "APPROVED",
                "approved_for_render": True,
            }
        ],
    }


class V21IntegrationTests(unittest.TestCase):
    def test_package_gate_scores_and_passes(self):
        report = evaluate_package_gate(valid_manifest())
        self.assertEqual(report["status"], "PACKAGE_GATE_PASS")
        self.assertEqual(report["score"], 10)

    def test_full_contract_is_schema_valid_and_read_only(self):
        report = evaluate(valid_manifest(), registry=historical_registry())
        self.assertEqual(report["status"], "PASS", report)
        self.assertFalse(report["production_enablement"])
        self.assertEqual(report["media_generation"], "NOT_RUN")
        self.assertEqual(report["publication"], "MANUAL_ONLY_NOT_RUN")

    def test_repository_registry_is_complete_and_loadable(self):
        root = Path(__file__).resolve().parents[1]
        registry = load_registry(root / "episodes" / "asset-memory-registry.json")
        self.assertEqual(len(registry), 13)
        self.assertTrue(all(item.get("perceptual_fingerprint") for item in registry))

    def test_canonical_contract_accepts_verified_repository_catalog(self):
        root = Path(__file__).resolve().parents[1]
        registry = load_registry(root / "episodes" / "asset-memory-registry.json")
        report = evaluate(valid_manifest(), registry=registry)
        self.assertEqual(report["status"], "PASS", report)

    def test_missing_registry_is_blocked(self):
        report = evaluate(valid_manifest(), registry=[])
        self.assertIn("global_no_reuse", report["blocking_gates"])

    def test_missing_thumbnail_manifest_is_blocked(self):
        manifest = valid_manifest()
        manifest.pop("thumbnail_manifest")
        report = evaluate(manifest, registry=historical_registry())
        self.assertIn("THUMBNAIL_QA", report["blocking_gates"])

    def test_schema_required_field_is_enforced(self):
        manifest = valid_manifest()
        manifest.pop("incident_id")
        report = evaluate(manifest, registry=historical_registry())
        self.assertIn("PRODUCTION_RECORD_SCHEMA", report["blocking_gates"])

    def test_existing_runtime_adapters_are_wired(self):
        report = evaluate(valid_manifest(), registry=historical_registry())
        self.assertNotIn("ADAPTER_WIRING", report["blocking_gates"])

    def test_tts_contract_rejects_provider_drift(self):
        manifest = valid_manifest()
        manifest["tts_contract"]["provider"] = "gemini_tts"
        report = evaluate(manifest, registry=historical_registry())
        self.assertIn("TTS_CONTRACT", report["blocking_gates"])

    def test_commercial_rights_are_hard_blocking(self):
        manifest = valid_manifest()
        manifest["rights_ledger"][0]["commercial_use"] = False
        report = evaluate(manifest, registry=historical_registry())
        self.assertIn("rights_ledger", report["blocking_gates"])

    def test_factual_mode_is_hard_locked(self):
        manifest = valid_manifest()
        manifest["editorial_mode"] = "fiction"
        self.assertEqual(evaluate_package_gate(manifest)["status"], "PACKAGE_GATE_BLOCKED")

    def test_global_reuse_blocks_incident_collision(self):
        report = evaluate(valid_manifest(), registry=[{"incident_id": "incident-fixture-001"}])
        self.assertIn("global_no_reuse", report["blocking_gates"])

    def test_state_machine_rejects_skips_and_requires_gate_evidence(self):
        with self.assertRaises(StateTransitionError):
            advance("DRAFT", "VOICE_PENDING", evidence={"gate": "PACKAGE", "status": "PASS", "evidence_id": "x"})
        with self.assertRaises(StateTransitionError):
            advance("DRAFT", "PACKAGE_PENDING", evidence={"test": "skip"})
        result = advance("DRAFT", "PACKAGE_PENDING", evidence={"gate": "PACKAGE_GATE_PRE", "status": "PASS", "evidence_id": "fixture"})
        self.assertEqual(result["state"], "PACKAGE_PENDING")


if __name__ == "__main__":
    unittest.main()