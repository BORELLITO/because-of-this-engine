"""Fail-closed audit of the V2.1 singleton runtime policy."""
from __future__ import annotations
import json
from pathlib import Path

# Gemini/Charon is the approved V2.1 TTS provider; it is NOT a legacy fallback.
# Block executable entrypoints of retired providers, without blocking the active
# Gemini adapter or archived historical evidence.
FORBIDDEN_PRODUCTION_FALLBACKS = (
    "production/microsoft_edge_tts.py",
    "production/align_edge_captions.py",
    "production/piper_tts.py",
    "production/cloud_tts.py",
    "production/v7_orchestrator.py",
    "production/v7_contract.py",
    "production/render_video_episode.py",
)
RETIRED_WORKFLOW_NAME_MARKERS = ("edge-tts", "piper-tts", "piper_tts", "legacy-render")
EXEMPT_WORKFLOWS = {"v21-integration-readonly.yml", "video-engine-ci.yml", "github-housekeeping.yml"}

def audit(repo_root: Path) -> dict:
    root = repo_root.resolve()
    failures: list[str] = []
    policy_path = root / "production" / "active_engine_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if policy.get("active_engine_version") != "2.1":
        failures.append("active policy is not V2.1")
    if policy.get("canonical_entrypoint") != "production/canonical_entrypoint.py":
        failures.append("canonical_entrypoint mismatch")
    if policy.get("production_enablement") is not False:
        failures.append("production_enablement must remain false in candidate")
    if policy.get("legacy_policy", {}).get("status") != "legacy_rollback_only":
        failures.append("legacy policy missing")
    # Caption layout and typography are part of the active V2.1 identity.
    # Keep this check in the singleton guard so an old caption motor cannot
    # silently re-enter through a workflow or helper script.
    caption_policy_path = root / "production" / "caption_policy_v21.json"
    if not caption_policy_path.is_file():
        failures.append("active V2.1 caption policy is missing")
    else:
        try:
            caption_policy = json.loads(caption_policy_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            failures.append(f"active V2.1 caption policy is unreadable:{exc}")
            caption_policy = {}
        if caption_policy.get("project") != "Because Of This Stories":
            failures.append("caption policy is not scoped to Because Of This Stories")
        if caption_policy.get("runtime") != "because_of_this_v21":
            failures.append("caption policy runtime must be because_of_this_v21")
        if caption_policy.get("forbidden_caption_characters") != ["—", "–"]:
            failures.append("caption policy must forbid em dash and en dash")
        layout = caption_policy.get("layout") if isinstance(caption_policy.get("layout"), dict) else {}
        if layout.get("margin_v") != 650 or layout.get("max_lines") != 2:
            failures.append("caption safe-zone layout drifted from the approved V2.1 lock")
        alignment = caption_policy.get("alignment") if isinstance(caption_policy.get("alignment"), dict) else {}
        if alignment.get("active_word_color") != "#F04444":
            failures.append("active karaoke red drifted from #F04444")
    active_caption_files = (
        root / "production" / "align_captions.py",
        root / "production" / "whisper_captions.py",
        root / "production" / "generate_phrase_captions.py",
        root / "production" / "caption_quality.py",
    )
    for path in active_caption_files:
        if not path.is_file():
            failures.append(f"active caption module missing:{path.relative_to(root).as_posix()}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if 'margin_v", 520' in text or "margin_v=520" in text or "#FF7777" in text:
            failures.append(f"legacy caption defaults remain active:{path.relative_to(root).as_posix()}")
        if path.name != "caption_quality.py" and "caption_style_v21" not in text:
            failures.append(f"active caption module is not wired to V2.1 policy:{path.relative_to(root).as_posix()}")
    # V2.1 final delivery must never bypass the audio postflight gate.
    # The currently approved candidate intentionally keeps remote final delivery off.
    if policy.get("final_drive_delivery_enablement") is not False:
        failures.append("final Drive media delivery must remain disabled in candidate V2.1")
    guard = policy.get("final_delivery_audio_gate") or {}
    if (guard.get("adapter") != "production/final_delivery_v21.py" or
            guard.get("drive_adapter") != "production/google_drive_delivery.py" or
            guard.get("receipt_required") is not True):
        failures.append("mandatory V2.1 final audio postflight policy is missing")
    adapter_path = root / "production" / "google_drive_delivery.py"
    if not adapter_path.is_file():
        failures.append("Drive delivery adapter missing")
    else:
        delivery_source = adapter_path.read_text(encoding="utf-8")
        if ("verify_drive_video_delivery(" not in delivery_source or
                'final_gate["status"] == "BLOCKED"' not in delivery_source):
            failures.append("Drive adapter lost mandatory final video postflight check")
    if not (root / "production" / "final_delivery_v21.py").is_file():
        failures.append("verified final video delivery gate missing")
    final_route = policy.get("final_render_route") or {}
    if (policy.get("final_render_entrypoint") != "production/render_v21_final.py"
            or final_route.get("status") != "IMPLEMENTED_FAIL_CLOSED_NO_PRODUCTION_AUTHORIZATION"
            or final_route.get("generate_new_TTS") is not False
            or final_route.get("publication") != "manual_only"):
        failures.append("singleton V2.1 final render route identity or no-TTS release lock changed")
    final_file = root / "production" / "render_v21_final.py"
    if not final_file.is_file():
        failures.append("canonical V2.1 final render adapter missing")
    else:
        final_source = final_file.read_text(encoding="utf-8")
        if ('validate_request(record, repo_root=repo_root, mode="final")'
                not in final_source or
                'validate_completed_audio_mix(' not in final_source or
                'build_audio_mix_command(' not in final_source):
            failures.append("canonical final renderer bypassed V2.1 preflight, mix or postflight")
    music = policy.get("final_render_route") or {}
    if (music.get("soundtrack_selection") != "production/music_direction_v21.py"
            or music.get("music_bed_required") is not True
            or music.get("music_covers_outro") is not True
            or music.get("voice_priority_ducking_required") is not True
            or music.get("no_sirens_alarms") is not True
            or music.get("music_rights_per_episode") is not True
            or music.get("music_volume_candidate") != 0.12):
        failures.append("singleton story-selected music or voice priority policy changed")
    if not (root / "production" / "music_direction_v21.py").is_file():
        failures.append("canonical music-direction verifier missing")
    if final_file.is_file():
        final_source=final_file.read_text(encoding="utf-8")
        if ("select_soundtrack(" not in final_source
                or "selected_audio_sha256" not in final_source
                or "sidechaincompress" not in final_source
                or "afade=t=out" not in final_source
                or '"-stream_loop"' in final_source):
            failures.append("final renderer lost automatic source-bound no-loop suspense bed")
    # GitHub CI invokes this guard both as a package and as a direct script.
    # Direct-script Python places production/ (not the repository root) on sys.path.
    if __package__ in (None, ""):
        from zero_cost_v21 import audit_repository as audit_zero_cost
    else:
        from production.zero_cost_v21 import audit_repository as audit_zero_cost
    no_charge = audit_zero_cost(root)
    if no_charge["status"] != "PASS":
        failures.extend("zero-cost:" + item for item in no_charge["failures"])
    # Source waveform diagnostics are evidence only, never a 'no sirens'
    # certificate. The final-release gate must still require qualified QA.
    if not (root / "production" / "music_content_screen_v21.py").is_file():
        failures.append("Selpan original-source sound screening missing")
    music_rights = root / "production" / "soundtrack_release_evidence_v21.py"
    if not music_rights.is_file():
        failures.append("music license/Content ID/historical SFX release verifier missing")
    manual = root / "production" / "render_v21_manual.py"
    if not manual.is_file() or (
        "audit_soundtrack_release(" not in manual.read_text(encoding="utf-8")):
        failures.append("final render preflight lost soundtrack release truth gate")
    workflow_root = root / ".github" / "workflows"
    workflows = sorted(workflow_root.glob("*.yml")) if workflow_root.exists() else []
    for path in workflows:
        if path.name in EXEMPT_WORKFLOWS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(marker in path.name.lower() for marker in RETIRED_WORKFLOW_NAME_MARKERS):
            failures.append(f"retired provider workflow remains active:{path.relative_to(root).as_posix()}")
        if any(token in text for token in FORBIDDEN_PRODUCTION_FALLBACKS):
            failures.append(f"legacy/provider entrypoint requires reconciliation:{path.relative_to(root).as_posix()}")
    if not (workflow_root / "v21-integration-readonly.yml").is_file():
        failures.append("canonical V2.1 workflow is missing")
    return {"status": "V21_SINGLETON_PASS" if not failures else "V21_SINGLETON_BLOCKED", "canonical_entrypoint": policy.get("canonical_entrypoint"), "failures": failures, "workflow_count": len(workflows)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    result = audit(parser.parse_args().repo_root.resolve())
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"].endswith("PASS") else 1)
