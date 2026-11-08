"""EP005 music/Content ID/archival SFX: no invented rights or release approval."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from production.soundtrack_release_evidence_v21 import audit

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = "episodes/episode-005/music-clearance-v21.json"
QA = "reports/EP005_MIXKIT_INVESTIGATIVE_HEAD_TO_HEAD_QA_20261108.json"
MASTERS = "episodes/audio-rendered-master-registry.json"


class V21SoundtrackReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for relative in (DOSSIER, QA, MASTERS):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())

    def dossier(self):
        path = self.root / DOSSIER
        return json.loads(path.read_text(encoding="utf-8"))

    def write_dossier(self, data):
        (self.root / DOSSIER).write_text(json.dumps(data), encoding="utf-8")

    def test_real_provider_rights_and_real_media_qa_pass_separately(self):
        result = audit(ROOT, "episode-005")
        self.assertEqual(result["status"], "BLOCKED", result)
        e = result["evidence"]
        self.assertEqual(
            e["license_for_commercial_online_video"],
            "SOURCE_TERMS_CONFIRMED_NOT_GLOBAL_CLAIM_WAIVER")
        self.assertEqual(e["original_music_bytes"],
                         "SHA256_VERIFIED_IN_EXISTING_PRIVATE_QA_RUN")
        self.assertEqual(e["new_song_vs_five_known_historical_sources"],
                         "NO_MATCH_IN_KNOWN_CATALOG_ONLY")
        self.assertEqual(e["actual_private_audio_mix"],
                         "TECHNICAL_PASS_NOT_MASTER_OR_PUBLICATION")
        self.assertEqual(e["content_id_claim_risk"],
                         "PENDING_PLATFORM_OR_PROVIDER_CASE_EVIDENCE")
        self.assertEqual(e["historical_sfx"],
                         "ZERO_INDEPENDENT_STEM_PROOFS_DO_NOT_RETROACTIVELY_APPROVE")
        self.assertEqual(result["historical_inventory"]["historical_master_count"], 4)
        self.assertEqual(result["historical_inventory"]["historical_verified_sfx_source_count"], 0)
        self.assertEqual(result["historical_inventory"]["historical_soundtrack_collision_count"], 1)
        self.assertFalse(result["production_authorized"])
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["monetary_spend_authorized"])

    def test_fake_content_id_approval_without_platform_evidence_is_blocked(self):
        dossier = self.dossier()
        dossier["content_id"]["status"] = "PLATFORM_EVIDENCE_REVIEWED_NO_UNRESOLVED_CLAIM"
        dossier["content_id"]["claim_exists"] = False
        dossier["decision"]["status"] = "APPROVED_FOR_RELEASE"
        self.write_dossier(dossier)
        result = audit(self.root, "episode-005")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("Content ID assertion lacks" in x for x in result["failures"]))

    def test_fake_historical_sfx_clearance_cannot_override_master_registry(self):
        dossier=self.dossier()
        dossier["historical_sfx"]["status"] = "VERIFIED_COMPLETE"
        dossier["historical_sfx"]["verified_sfx_stem_sources"] = 5
        dossier["decision"]["status"] = "APPROVED_FOR_RELEASE"
        self.write_dossier(dossier)
        result=audit(self.root, "episode-005")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("SFX dossier disagrees" in x for x in result["failures"]))
        self.assertTrue(any("historical SFX contributions remain unproven" in x for x in result["failures"]))

    def test_provider_investigative_tags_do_not_replace_independent_listening_QA(self):
        result=audit(self.root, "episode-005")
        self.assertEqual(result["evidence"]["creative_fitness_for_story"],
                         "PENDING_STORY_MUSIC_AUDITION_PROVIDER_TAGS_ONLY")
        self.assertTrue(any("editorial fit" in x for x in result["failures"]))

    def test_fake_official_url_and_original_song_sha_are_rejected(self):
        dossier=self.dossier()
        dossier["official_listing_url"] = "https://mixkit.co.attacker.example/free-stock-music/"
        dossier["source_sha256"] = "f" * 64
        self.write_dossier(dossier)
        result=audit(self.root, "episode-005")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("source/provider/license URLs" in x for x in result["failures"]))
        self.assertTrue(any("Selpan original MP3" in x for x in result["failures"]))

    def test_music_QA_cannot_be_changed_to_claim_release_pass(self):
        qa_path=self.root / QA
        qa=json.loads(qa_path.read_text())
        qa["status"]="PRODUCTION_APPROVED"
        qa_path.write_text(json.dumps(qa))
        result=audit(self.root,"episode-005")
        self.assertEqual(result["status"],"BLOCKED")
        self.assertTrue(any("selected Selpan preview/voice mix" in x for x in result["failures"]))

    def test_selpan_is_active_but_its_content_screen_is_not_falsely_certified(self):
        a = audit(self.root, "episode-005")
        self.assertEqual(a["evidence"]["music_sfx_content_review"],
                         "PENDING_FULL_SOURCE_AUDITION_AND_VOICE_CLARITY")
        self.assertTrue(any("source listening/SFX" in x for x in a["failures"]))
        dossier = self.dossier()
        self.assertEqual(dossier["title"], "Selpan")
        self.assertEqual(dossier["audio_content_screen"]["siren_absence_certified"], False)
        self.assertTrue((ROOT / "episodes/episode-005/music-clearance-silent-descent-archive-v21.json").is_file())

    def test_ledger_missing_and_missing_candidate_dossier_block(self):
        (self.root / MASTERS).unlink()
        result=audit(self.root, "episode-005")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("historical master SFX evidence" in x for x in result["failures"]))
        (self.root / DOSSIER).unlink()
        result=audit(self.root, "episode-005")
        self.assertTrue(any("dossier missing" in x for x in result["failures"]))

    def test_an_unrelated_episode_cannot_borrow_ep005_approval(self):
        result=audit(self.root,"episode-006")
        self.assertEqual(result["status"],"BLOCKED")
        self.assertFalse(result["publication_authorized"])

    def test_zero_cost_and_manual_only_are_preserved(self):
        result=audit(self.root, "episode-005")
        self.assertEqual(result["audit_mode"],"READ_ONLY")
        self.assertEqual(result["tts_requests"],0)
        self.assertFalse(result["monetary_spend_authorized"])
        self.assertFalse(result["production_authorized"])


if __name__ == "__main__":
    unittest.main()
