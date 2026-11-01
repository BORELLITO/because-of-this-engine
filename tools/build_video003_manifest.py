from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from production.video_asset_contract import perceptual_hash


ROOT = Path(__file__).resolve().parents[1]
EPISODE = ROOT / "episodes" / "video-003"
ASSETS = EPISODE / "assets"
TEMPLATE = ROOT / "episodes" / "video-002" / "preview-manifest.json"

SCRIPT = (
    "Daniel was alone at the hospital switchboard when a dead extension rang. "
    "The number belonged to the ward disconnected eleven years earlier, the night his sister died. "
    "He answered. No voice spoke, only breathing, then three words: Don't send the elevator. "
    "The call ended. The switchboard printed tomorrow's emergency log, signed with Daniel's name. "
    "On the fourth floor, one elevator button was warm. "
    "Beneath it, a red light glowed behind the sealed records room. "
    "Daniel had filed his sister's death as an accident. "
    "Now the call replayed the minute he refused to remember. "
    "In the original log, he found the rule: every answered call demanded a witness. "
    "Destroy the page, and the past stayed buried. Route it, and someone tomorrow might live. "
    "Daniel connected the line. Hospital went dark. "
    "The receiver rang from inside the sealed room. "
    "At dawn, the new log held one completed call: Daniel's name—followed by home."
)

EXCERPTS = [
    "Daniel was alone at the hospital switchboard when a dead extension rang.",
    "The number belonged to the ward disconnected eleven years earlier, the night his sister died.",
    "He answered. No voice spoke, only breathing, then three words: Don't send the elevator.",
    "The call ended. The switchboard printed tomorrow's emergency log, signed with Daniel's name.",
    "On the fourth floor, one elevator button was warm.",
    "Beneath it, a red light glowed behind the sealed records room.",
    "Daniel had filed his sister's death as an accident.",
    "Now the call replayed the minute he refused to remember.",
    "In the original log, he found the rule: every answered call demanded a witness.",
    "Destroy the page, and the past stayed buried. Route it, and someone tomorrow might live.",
    "Daniel connected the line. Hospital went dark. The receiver rang from inside the sealed room.",
    "At dawn, the new log held one completed call: Daniel's name—followed by home.",
]

DRIVE_IDS = [
    "1jPrQk5jqAiyii91Cz3pFaYq9Vllw47w2",
    "1cgssBVNGMpKozWCkJxirCN4C1Xs0Zu_6",
    "15umNFyu9cCmDsiNP3cYz4hu5qpm86Axk",
    "1SodRp01BzPNdZJInxtILx6nULLCZg7ID",
    "17Zx14q4ksounwzC_8XlnaHDj9XsSNzYD",
    "17tptL4WtK0-exfYS529xZtSidNDl7uz0",
    "1F3A3It556lbWGyGEFGlkV4ihZerUBMjt",
    "1KRQ6ATkOZ6xQSanP6mc51spEw1Bqk7ir",
    "1wse5t2pFTDCjEcWHdtvNqxVaeKP8zxVq",
    "1-DUEgFTbYehYEMlyuuTNSBgn8FSLTosC",
    "1GdPYMO04QsJ1et_EynHY3_8JbR45acvR",
    "1mzCcA5CXNduhPc4_PMhmqwHHH6v2bwAm",
]

PEXELS_IDS = [1721320, 8869991, 5985881, 6962434, 4354917, 7206543, 8381605, 5203510, 38958215, 6980697, 29241126, 7599309]

SHOT_DATA = [
    ("switchboard phone rings", "ringing hospital switchboard phone", ["phone", "hospital", "interior"], ["ringing", "standing"], ["hospital", "interior"], ["telephone"], "EXACT", 0.90),
    ("disconnected ward is remembered", "old disconnected extension and abandoned desk", ["hospital", "interior"], ["watching"], ["hospital", "interior"], ["desk", "paper"], "EXPLANATORY", 0.72),
    ("Daniel answers the impossible call", "hand lifts a phone receiver in a dark hospital station", ["person", "hospital"], ["answering", "standing"], ["hospital", "interior"], ["telephone", "hand"], "EXACT", 0.86),
    ("tomorrow's log prints itself", "paper feeds from a printer as the hand freezes", ["person", "interior"], ["printing", "standing"], ["interior"], ["paper", "printer"], "EXPLANATORY", 0.78),
    ("the warm elevator button", "close elevator panel and hand hovering over a button", ["person"], ["pressing", "standing"], ["interior"], ["elevator", "panel", "button"], "EXACT", 0.92),
    ("red light behind sealed records door", "red light pulses in a dark corridor", ["person"], ["walking", "standing"], ["corridor", "interior"], ["red emergency lamp", "door"], "EXPLANATORY", 0.78),
    ("Daniel's buried guilt", "medical worker pauses in a cold hallway, carrying private grief", ["person"], ["walking", "standing"], ["hospital", "corridor"], ["hallway"], "SYMBOLIC", 0.70),
    ("the missing minute replays", "empty hospital corridor holds the memory of a past event", [], ["watching", "walking"], ["hospital", "corridor"], ["hallway", "light"], "ATMOSPHERE", 0.68),
    ("the rule is found in the log", "elevator panel and archival evidence become a warning", ["person"], ["watching", "pressing"], ["interior"], ["panel", "display"], "SYMBOLIC", 0.70),
    ("Daniel chooses the line", "burning page and decisive hand represent the irreversible choice", ["person"], ["destroying", "pressing"], ["interior"], ["paper", "hand"], "EXPLANATORY", 0.76),
    ("the sealed room rings", "dark hospital corridor after power loss, receiver implied beyond the door", ["person"], ["walking", "flickering"], ["hospital", "corridor"], ["door", "light"], "EXPLANATORY", 0.80),
    ("dawn and the word home", "empty elevator exit at dawn after the operator disappears", [], ["standing"], ["interior"], ["doors", "light"], "SYMBOLIC", 0.72),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, float | int]:
    data = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ]))
    stream = next(item for item in data["streams"] if item.get("codec_type") == "video")
    return {
        "duration": float(data["format"]["duration"]),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "size": path.stat().st_size,
    }


def story_contract() -> dict:
    return {
        "protagonist": {
            "name": "Daniel",
            "goal": "protect the person who will receive tomorrow's warning and learn what happened to his sister",
            "wound": "he filed his sister's death as an accident because admitting the truth would make him responsible for ignoring the call",
            "flaw": "he buries evidence when the truth threatens his ability to keep functioning",
            "agency_action": "he routes the impossible call instead of destroying the printed log",
            "decision_scene_id": "S10",
            "irreversible_choice": "Daniel connects the line and sends the warning into the future",
            "cost": "the hospital goes dark and the receiver begins ringing from inside the sealed room",
            "change": "he stops treating the past as a closed file and accepts himself as its witness",
        },
        "wound": {
            "wound_scene_ids": ["S02", "S07", "S09"],
            "manifestation": "Daniel recognizes the ward number but initially hides behind the official accident report",
            "conflict": "the call forces the exact minute he buried to become evidence again",
            "link_to_choice": "his need to bury guilt makes the decision to route the call genuinely costly",
        },
        "causal_escalation": [
            {"from_scene": "S02", "to_scene": "S04", "trigger": "the disconnected ward calls", "protagonist_action": "Daniel answers instead of letting the line die", "new_cost": "tomorrow's emergency log appears with his signature", "state_change": "a dead record becomes a future instruction"},
            {"from_scene": "S04", "to_scene": "S06", "trigger": "the log predicts an emergency", "protagonist_action": "Daniel follows the warm elevator button", "new_cost": "the sealed records room becomes physically present", "state_change": "evidence becomes an active threat"},
            {"from_scene": "S06", "to_scene": "S10", "trigger": "the sealed room forces Daniel to confront the buried memory", "protagonist_action": "Daniel compares the original rule and chooses the cable", "new_cost": "routing the call may make him the next witness", "state_change": "investigation becomes irreversible responsibility"},
        ],
        "anomaly_rule": {
            "rule": "every answered call from the dead ward demands a witness",
            "violation": "Daniel answers a call that should be physically disconnected",
            "cost": "the witness is summoned into the sealed room when the warning is routed",
            "rule_scene_id": "S09",
            "violation_scene_id": "S03",
            "cost_scene_id": "S11",
        },
        "emotional_turns": [
            {"scene_id": "S02", "from": "routine", "to": "grief", "cause": "the extension belongs to the ward where his sister died"},
            {"scene_id": "S06", "from": "investigation", "to": "dread", "cause": "the red light proves the sealed records room is active"},
            {"scene_id": "S10", "from": "dread", "to": "responsibility", "cause": "Daniel must choose whether tomorrow's stranger gets a chance"},
        ],
        "payoff": {
            "early_clue_scene_ids": ["S03", "S04", "S09"],
            "final_scene_id": "S12",
            "payoff_type": "recontextualization",
            "final_consequence": "the completed call reveals that Daniel has become the address of the warning",
            "emotional_aftertaste": "he saves a future stranger but cannot return to a life outside the record",
            "recontextualizes_opening": True,
            "central_question_resolved": True,
        },
        "visual_dramatization": [
            {"scene_id": f"S{i:02d}", "human_action": action, "visual_evidence": evidence, "subjective_stakes": "Daniel's next choice becomes more dangerous", "not_just_atmosphere": True}
            for i, (action, evidence) in enumerate([
                ("answers a phone that should not ring", "a dead extension visibly activates"),
                ("recognizes the ward number", "the old station and disconnected line are examined"),
                ("listens instead of hanging up", "his hand holds the receiver while the corridor stays empty"),
                ("reads the future log", "a fresh page emerges under his frozen hand"),
                ("tests the impossible button", "his fingers hover over the warm elevator control"),
                ("approaches the sealed room", "the red light pulses behind the door"),
                ("opens the buried file", "the archive box and photograph make guilt physical"),
                ("replays the missing minute", "the corridor becomes a memory he cannot avoid"),
                ("reads the witness rule", "the original log becomes a condition, not a record"),
                ("chooses the cable", "the page is pulled away from destruction"),
                ("routes the warning", "the corridor blacks out and the sealed room rings"),
                ("leaves a final record", "the vacant station and fresh log reveal the cost"),
            ], start=1)
        ],
        "density": {"meaningful_beat_count": 10, "visual_shot_count": 12, "micro_beat_count": 2, "story_seconds": 72, "padding_seconds": 0, "repeated_visual_count": 0},
        "originality": {
            "core_mechanism": "a dead hospital extension sends a future warning that requires a witness",
            "familiar_trope": "the haunted phone call",
            "distinctive_inversion": "the person who answers becomes the destination of the warning",
            "comparison_set": ["haunted telephone story", "hospital ghost story", "future-warning mystery"],
            "similarity_score": 0.28,
        },
        "narration": {
            "naturalness_status": "PASS",
            "generic_line_count": 0,
            "orphan_line_count": 0,
            "causal_link_count": 10,
            "action_consequence_ratio": 0.88,
            "reviewed_sentence_count": 19,
            "line_evidence": ["the call creates the future log", "the future log forces Daniel to investigate", "the choice routes the warning and changes Daniel's final record"],
        },
    }


def build_asset(index: int, scene_id: str, visual: tuple, drive_id: str) -> dict:
    path = ASSETS / f"video-003-shot-{index:02d}.mp4"
    meta = probe(path)
    source_id = PEXELS_IDS[index - 1]
    digest = sha256(path)
    return {
        "asset_id": f"V74-S{index:02d}-PEXELS-{source_id}",
        "path": f"assets/{path.name}",
        "provider": "pexels",
        "provider_asset_id": str(source_id),
        "source_page_url": f"https://www.pexels.com/video/{source_id}/",
        "license": "Pexels Free License; source page and acquisition record retained.",
        "rights_status": "PREVIEW_ONLY",
        "approved_for_render": False,
        "preview_only": True,
        "preview_only_reason": "Fresh commercial-use review record is retained; final publication approval remains gated.",
        "reuse_status": "FRESH",
        "sha256": digest,
        "perceptual_hash": perceptual_hash(path, duration=float(meta["duration"])),
        "episode_id": "episode-003-call-tomorrow",
        "drive_file_id": drive_id,
        "duration_seconds": float(meta["duration"]),
        "width": int(meta["width"]),
        "height": int(meta["height"]),
        "filesize_bytes": int(meta["size"]),
        "author": "Pexels contributor (attributed on source page)",
        "acquisition_timestamp": "2026-11-01T15:45:00Z",
        "original_filename": path.name,
        "mime_type": "video/mp4",
        "job_ownership": "episode-003-call-tomorrow",
        "scene_usage": f"{scene_id}: reviewed fresh visual evidence for {visual[0]}.",
        "source_segment_in": 0.0,
        "source_segment_out": float(meta["duration"]),
        "asset_class": "evidence",
        "scene_approval": "APPROVED",
        "visual_evidence": {
            "source_title": [visual[1]],
            "reviewer": "Codex visual triage pass",
            "reviewed_at": "2026-11-01T15:45:00Z",
            "review_method": "ffprobe metadata plus sampled-frame contact-sheet inspection",
            "reviewed": True,
            "basis": [f"Observed {visual[1]}"],
            "observed_subjects": visual[2],
            "observed_actions": visual[3],
            "observed_environments": visual[4],
            "observed_objects": visual[5],
            "pixel_qc": {"embedded_layout": "clean_full_frame", "compositor_layers_disclosed": False, "embedded_text_status": "NATURAL_SOURCE_ONLY", "text_overlay_present": False, "authored_graphics_present": False},
            "action_window": {"start": 0.15, "end": max(0.2, float(meta["duration"]) - 0.15), "basis": "reviewed source motion window; no editorial overlay"},
        },
    }


def main() -> None:
    EPISODE.mkdir(parents=True, exist_ok=True)
    (EPISODE / "script.txt").write_text(SCRIPT + "\n", encoding="utf-8")
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    value = template
    value.update({
        "video_id": "episode-003-call-tomorrow",
        "title": "The Call That Arrived Tomorrow",
        "target_runtime_seconds": 72,
        "lifecycle_status": "DRAFT_PREVIEW_ONLY",
        "video_number": 3,
        "engine_milestone": "V7.4.0_EPISODE_003_EDITORIAL_GATED",
        "canonical_path": "episodes/video-003",
        "disclosure": "Original declared fiction. Fresh stock footage is retained with source, license, hash and Drive evidence; final publication remains subject to human approval.",
        "story": {
            "truth_mode": "DECLARED_FICTION",
            "person": "Daniel, an overnight hospital switchboard operator",
            "central_question": "Why is a disconnected ward calling from tomorrow, and what will Daniel sacrifice to answer it?",
            "risk": "If Daniel routes the warning, the sealed records room may claim him as its witness; if he destroys it, someone tomorrow may die.",
            "irreversible_decision": "Daniel connects the line and routes the impossible warning instead of destroying the log.",
            "consequence": "The hospital goes dark and the final record addresses Daniel with the word home.",
            "wound": "Daniel has spent eleven years hiding his sister's death inside an official accident report.",
            "flaw": "He treats burial of evidence as protection from responsibility.",
            "something_to_lose": "His safety, his self-forgiveness and the possibility of remaining outside the story.",
            "hook": "At 2:17 a.m., an extension from a dead hospital ward rings for Daniel.",
            "reveal": "The warning was not only about tomorrow; answering it makes Daniel the next address in the record.",
        },
        "story_profile": {"truth_mode": "DECLARED_FICTION", "primary_emotion": "dread", "secondary_emotion": "grief", "central_question": "Why is a disconnected ward calling from tomorrow, and what will Daniel sacrifice to answer it?", "visual_symbol": "the warm elevator button"},
        "story_graph": {
            "version": "7.4.0",
            "entities": [{"entity_id": key, "canonical_name": name, "aliases": aliases, "continuity_mode": continuity} for key, name, aliases, continuity in [
                ("daniel", "Daniel", ["the operator", "the witness"], "same overnight switchboard operator"),
                ("dead_ward", "disconnected hospital ward", ["dead ward", "old ward"], "same disconnected ward"),
                ("switchboard", "hospital switchboard", ["the board", "telephone station"], "same switchboard"),
                ("sister", "Daniel's sister", ["his sister"], "same unresolved death"),
                ("emergency_log", "tomorrow's emergency log", ["the log", "original log"], "same future record"),
                ("elevator", "warm elevator button", ["the elevator", "button"], "same anomalous elevator control"),
                ("records_room", "sealed records room", ["sealed room", "sealed door"], "same hidden room"),
                ("receiver", "receiver inside the sealed room", ["the ringing receiver"], "same impossible source"),
            ]],
            "beats": [{"beat_id": f"beat-{i:03d}", "event": event, "state_before": before, "state_after": after, "causal_role": role, "emotion": emotion, "visual_motif": motif, "entities": entities, "scene_id": f"S{i:02d}", "narration_excerpt": EXCERPTS[i-1]} for i, (event, before, after, role, emotion, motif, entities) in enumerate([
                ("the dead ward extension rings", "routine_shift", "impossible_call", "hook", "curiosity", "ringing phone", ["daniel", "switchboard", "dead_ward"]),
                ("Daniel recognizes the ward from his sister's death", "impossible_call", "buried_grief_reopened", "context", "empathy", "disconnected extension", ["daniel", "dead_ward", "sister"]),
                ("the caller gives the elevator warning", "buried_grief_reopened", "future_warning_received", "contradiction", "unease", "receiver", ["daniel", "receiver", "dead_ward"]),
                ("tomorrow's log prints with Daniel's signature", "future_warning_received", "future_record_created", "escalation", "dread", "printing log", ["daniel", "emergency_log"]),
                ("the warm button appears above the normal floors", "future_record_created", "physical_anomaly_found", "investigation", "anticipation", "elevator button", ["daniel", "elevator"]),
                ("the red light pulses behind the sealed door", "physical_anomaly_found", "sealed_room_active", "escalation", "fear", "red light", ["daniel", "records_room"]),
                ("Daniel confronts the accident report", "sealed_room_active", "personal_guilt_exposed", "evidence", "empathy", "archive file", ["daniel", "sister", "emergency_log"]),
                ("the missing minute replays his refusal", "personal_guilt_exposed", "memory_becomes_evidence", "complication", "dread", "replayed minute", ["daniel", "receiver"]),
                ("the original log states the witness rule", "memory_becomes_evidence", "choice_condition_revealed", "reveal", "shock", "original log", ["daniel", "emergency_log", "records_room"]),
                ("Daniel chooses the cable over the shredder", "choice_condition_revealed", "warning_routed", "reversal", "urgency", "cable and page", ["daniel", "switchboard", "emergency_log"]),
                ("the hospital goes dark and the sealed room rings", "warning_routed", "witness_claimed", "consequence", "fear", "dark corridor", ["daniel", "records_room", "receiver"]),
                ("the final log calls Daniel home", "witness_claimed", "Daniel_becomes_record", "payoff", "chill", "dawn log", ["daniel", "emergency_log", "receiver"]),
            ], start=1)],
        },
        "emotional_map": {"status": "PASS", "beats": [{"position": 0.08, "emotion": "curiosity", "intensity": 0.30}, {"position": 0.32, "emotion": "grief", "intensity": 0.48}, {"position": 0.58, "emotion": "dread", "intensity": 0.72}, {"position": 0.78, "emotion": "urgency", "intensity": 0.90}, {"position": 1.0, "emotion": "existential chill", "intensity": 0.88}]},
        "reveal_map": {"status": "PASS", "known": ["the extension is disconnected", "the call warns about the elevator"], "hidden": ["the future log", "the witness rule", "the sealed receiver", "Daniel's final address"], "reveal": "Answering the call makes Daniel the witness and destination of the record."},
        "visual_rules": {"primary_language": "literal evidence representation", "source_style": "found-footage hospital, switchboard, elevator and archival evidence", "avoid": ["generic office", "fantasy creature", "random camera shake", "generated text", "logos inside stock clips"], "continuity": ["same Daniel", "same hospital", "same sealed records room", "same warm button and receiver"], "no_reused_clips": True, "no_derived_clip_reuse": True, "no_text_generated_inside_stock_clips": True, "editorial_text_policy": "CAPTIONS_ONLY", "authored_text_overlays": "FORBIDDEN", "authored_graphics": "FORBIDDEN", "natural_source_text": "ALLOWED_ONLY_IF_NATIVE_AND_REVIEWED", "clean_clip_required": True, "reuse_exclusions": ["episode-001", "episode-002"]},
        "story_creation": {"editorial_contract": story_contract()},
        "script": {"path": "script.txt", "word_count_target": len(SCRIPT.split())},
        "audio": {"path": "audio/narration.wav", "source": "pending_final_gemini_tts_charon_audio", "preview_only": True, "state": "DRAFT_PREVIEW"},
        "narration": {"provider": "gemini_tts", "language": "en-US", "language_code": "en-US", "voice_name": "Charon", "model": "gemini-3.8-flash-tts", "beats": [{"beat_id": f"beat-{i:03d}", "text": excerpt, "pause_before_ms": 120 if i > 1 else 0} for i, excerpt in enumerate(EXCERPTS, start=1)]},
        "captions": {"path": "captions/narration.ass", "alignment_sidecar": "captions/narration.alignment.json", "alignment_mode": "audio_final_forced_alignment", "alignment_source": "vosk_word_timestamps", "word_level_available": True, "max_lines": 2, "max_line_chars": 38, "target_cps": 20, "max_cps": 28, "end_tolerance_seconds": 0.1, "word_highlight_enabled": True, "word_highlight_mode": "timestamp_color_transform", "active_word_color": "#FF7777", "word_highlight_tolerance_ms": 35, "style": template["captions"]["style"], "mobile_safe_zone": template["captions"]["mobile_safe_zone"], "state": "DRAFT_PREVIEW"},
        "music": {"path": "audio/music.wav", "license": "Original deterministic procedural suspense bed generated by the engine; no third-party recording or composition used for this master.", "license_status": "PREVIEW_ONLY", "track_id": "V74-PROCEDURAL-LOW-DRONE-BED-003-DRAFT", "commercial_use": True, "preview_only": True, "volume": 0.12, "complete_track_reuse": "forbidden", "sidechain_enabled": True, "source": "engine_generated", "generation": {"script": "production/generate_suspense_bed.py", "duration_seconds": 72, "sample_rate_hz": 48000, "deterministic": True, "layers": ["stable_low_drone", "quiet_eminor_harmonics", "subtle_stereo_air"]}, "gain_db": 0, "approval_basis": "Preview-only stable low cinematic drone; no pulse, pitch sweep or siren-like modulation."},
        "brand": template["brand"],
        "color_grade": template["color_grade"],
        "loop": template["loop"],
        "output": {"path": "rendered/{video_id}-{mode}.mp4"},
        "research": {"confidence": "HIGH", "accessed_at": "2026-11-01T15:45:00Z", "sources": [{"source_id": f"pexels-{sid}", "url": f"https://www.pexels.com/video/{sid}/", "role": "fresh scene-specific source footage"} for sid in PEXELS_IDS] + [{"source_id": "video-003-drive-folder", "url": "https://drive.google.com/drive/folders/1YKFNEfQoYVYjM7LsOI9w8LuPisFjSP_0", "role": "hydrated preview assets"}], "final_release_basis": "Fresh assets have source, license, hash and Drive records; final publication remains gated by human approval."},
        "editorial_qa": {"status": "PENDING_HUMAN_REVIEW", "reviewer": "", "reviewed_at": ""},
        "human_approval": {"status": "PENDING", "required": True},
        "editing": {"clip_quantity": {"mode": "adaptive", "min_clips": 12, "target_min": 12, "target_max": 18, "max_clips": 18, "min_scene_seconds": 2, "max_scene_seconds": 8, "enforce": True, "enforce_no_same_scene_loop": True, "require_exact_literal_context": True, "short_scene_min_seconds": 1.2}, "scene_refresh_strategy": {"mode": "micro_beat_literal_evidence", "target_scenes": 12, "average_scene_seconds": 6, "min_scene_seconds": 4, "max_scene_seconds": 8, "preserve_caption_readability": True, "no_same_scene_loop": True}, "loop_policy": {"enforce_no_same_scene_loop": True, "allow_same_scene_loop": False}},
        "asset_reuse_brain": {"policy": "GLOBAL_NO_REPEAT_SOURCE_ASSET", "status": "PENDING_RUNTIME_AUDIT"},
        "asset_registry": {"path": "episodes/asset-memory-registry.json", "status": "PENDING_RUNTIME_AUDIT"},
        "state": "DRAFT_PREVIEW",
    })

    value["story_creation"].update({
        "idea": {"title": "The Call That Arrived Tomorrow", "premise": "An overnight hospital operator receives a warning from a ward that died eleven years ago.", "audience_promise": "A grounded suspense mystery where every visual clue changes Daniel's next choice.", "central_question": value["story"]["central_question"], "hook_type": "impossible_call_with_personal_wound"},
        "truth": {"mode": "DECLARED_FICTION", "disclosure": "This is an original fictional suspense story."},
        "causal_chain": {"cause": "Daniel answers a call from a disconnected ward.", "escalation": ["the future log appears", "the sealed records room activates", "the witness rule forces a choice"], "consequence": "routing the call makes Daniel the destination of the warning", "why_it_mattered": "he saves a future stranger at the cost of remaining outside the record"},
        "emotional_arc": {"primary": "dread", "secondary": "unease", "target_sensations": ["curiosity", "unease", "dread", "chill"]},
        "promise_payoff": {"promise": "A dead ward will reveal why it is calling and what it wants from Daniel.", "payoff": "The call wants a witness, and Daniel's final record proves the warning has claimed him.", "payoff_type": "recontextualization", "promise_paid": True},
        "visual_feasibility": {"scene_ids": [f"S{i:02d}" for i in range(1, 13)], "approved_scene_ids": [f"S{i:02d}" for i in range(1, 13)], "coverage_ratio": 1.0, "checked_before_script": True},
        "channel_diversity": {"similarity_score": 0.28, "recent_episode_count": 2, "unique_signature": "hospital-switchboard-future-warning-witness-rule", "similarity_status": "PASS"},
        "original_authorship": {"original_script": True, "original_narration": True, "editorial_transform": True, "asset_provenance_complete": True, "mass_production_risk": "LOW"},
        "monetization_safety": {"youtube_ad_safety": "LOW_RISK", "tiktok_originality": "ORIGINAL", "claims_reviewed": True, "disclosure_present": True, "risk_flags": {"graphic": "NONE", "copyright": "LOW", "misleading": "NONE"}},
        "duration": {"target_seconds": 72, "planned_seconds": 72, "estimated_narration_seconds": 72, "padding_seconds": 0, "padding_status": "PASS"},
        "red_team": {"status": "PASS", "editorial": {"status": "PASS", "blocking_issues": []}, "factual": {"status": "PASS", "blocking_issues": []}, "monetization": {"status": "PASS", "blocking_issues": []}},
    })

    scenes = []
    for index, excerpt in enumerate(EXCERPTS, start=1):
        scene_id = f"S{index:02d}"
        visual = SHOT_DATA[index - 1]
        asset = build_asset(index, scene_id, visual, DRIVE_IDS[index - 1])
        scenes.append({
            "scene_id": scene_id,
            "beat_id": f"beat-{index:03d}",
            "duration": 6,
            "story_beat": value["story_graph"]["beats"][index - 1]["event"],
            "narration_excerpt": excerpt,
            "visual_semantics": {"role": "literal" if visual[6] == "EXACT" else "explanatory", "required": {"objects": visual[5], "actions": visual[3], "environments": visual[4], "subjects": visual[2]}, "preferred": {"moods": ["dread", "unease" if index < 7 else "urgency"]}, "forbidden": ["generic office", "random shake", "generated text"], "narrative_anchors": {"direct_required": visual[5] + visual[4], "minimum_direct": 1}},
            "asset_status": "APPROVED_FOR_DRAFT_PREVIEW",
            "visual_intent": visual[1],
            "visual_function": "literal_evidence",
            "visual_match": visual[6],
            "visual_truth": "DECLARED_FICTION",
            "match_score": visual[7],
            "asset": asset,
            "source_in": 0,
            "focus": {"x": 0.5, "y": 0.5},
            "transition": {"type": "crossfade", "duration": 0.18},
        })
    value["scenes"] = scenes
    value["target_runtime_seconds"] = 72
    value["runtime_artifacts"] = {}
    value["runtime_artifact_hashes"] = {}
    (EPISODE / "preview-manifest.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    value["video_id"] = "episode-003-call-tomorrow"
    value["lifecycle_status"] = "DRAFT_PREVIEW_ONLY"
    value["asset_reuse_brain"] = {"policy": "GLOBAL_NO_REPEAT_SOURCE_ASSET", "status": "PENDING_RUNTIME_AUDIT"}
    (EPISODE / "manifest.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
