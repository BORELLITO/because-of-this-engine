"""Creation-layer intelligence and policy gates for Because of This.

This module validates the story before rendering. It is intentionally separate from
asset, timeline, and render gates so that a weak premise cannot be rescued by
polished footage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


TRUTH_MODES = {
    "REAL_FACTUAL",
    "DOCUMENTED_RECONSTRUCTION",
    "DECLARED_FICTION",
}

CREATION_GATES = (
    ("C0", "IDEA_PROMISE"),
    ("C1", "TRUTH_MODE"),
    ("C2", "CAUSALITY"),
    ("C3", "EMOTIONAL_CALIBRATION"),
    ("C4", "PROMISE_PAYOFF_INTEGRITY"),
    ("C5", "STATE_CHANGE"),
    ("C6", "VISUAL_FEASIBILITY_BEFORE_SCRIPT"),
    ("C7", "CHANNEL_DIVERSITY"),
    ("C8", "ORIGINAL_AUTHORSHIP"),
    ("C9", "MONETIZATION_SAFETY"),
    ("C10", "NO_PADDING"),
    ("C11", "RED_TEAM"),
)

ALLOWED_ROLES = {
    "hook",
    "setup",
    "context",
    "contradiction",
    "investigation",
    "escalation",
    "disappearance",
    "reveal",
    "flight",
    "negative_evidence",
    "evidence",
    "complication",
    "reversal",
    "false_closure",
    "consequence",
    "payoff",
    "recurrence",
    "closure",
}

ALLOWED_EMOTIONS = {
    "curiosity",
    "unease",
    "anticipation",
    "dread",
    "confusion",
    "fear",
    "panic",
    "incertitude",
    "shock",
    "relief",
    "relief_then_doubt",
    "chill",
    "wonder",
    "urgency",
    "empathy",
    "surprise",
}


class StoryCreationError(ValueError):
    """Raised when a creation-layer report cannot be produced."""


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _all_text(values: Any) -> bool:
    return isinstance(values, list) and bool(values) and all(_text(value) for value in values)


def _gate(code: str, name: str, passed: bool, evidence: Iterable[str]) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "status": "PASS" if passed else "BLOCKED",
        "evidence": list(evidence),
    }


def _scene_ids(manifest: Mapping[str, Any]) -> list[str]:
    return [
        scene.get("scene_id")
        for scene in manifest.get("scenes", [])
        if isinstance(scene, Mapping) and _text(scene.get("scene_id"))
    ]


def _beats(manifest: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    graph = manifest.get("story_graph", {})
    beats = graph.get("beats", []) if isinstance(graph, Mapping) else []
    return [beat for beat in beats if isinstance(beat, Mapping)]


def _story_block(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    block = manifest.get("story_creation")
    return block if isinstance(block, Mapping) else {}


def _idea_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    idea = sc.get("idea")
    required = ("title", "premise", "audience_promise", "central_question", "hook_type")
    if not isinstance(idea, Mapping):
        return _gate("C0", "IDEA_PROMISE", False, ["story_creation.idea is missing"])
    missing = [key for key in required if not _text(idea.get(key))]
    passed = not missing
    return _gate(
        "C0",
        "IDEA_PROMISE",
        passed,
        ["title, premise, audience promise, central question and hook are explicit"]
        if passed
        else [f"missing fields: {', '.join(missing)}"],
    )


def _truth_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    truth = sc.get("truth")
    profile = manifest.get("story_profile", {})
    mode = truth.get("mode") if isinstance(truth, Mapping) else profile.get("truth_mode")
    if mode not in TRUTH_MODES:
        return _gate("C1", "TRUTH_MODE", False, ["truth mode must be explicitly declared"])
    evidence = [f"mode={mode}"]
    if mode == "REAL_FACTUAL":
        sources = truth.get("sources") if isinstance(truth, Mapping) else None
        passed = _all_text(sources)
        evidence.append("factual claims have source references" if passed else "REAL_FACTUAL requires non-empty sources")
    elif mode == "DOCUMENTED_RECONSTRUCTION":
        sources = truth.get("sources") if isinstance(truth, Mapping) else None
        note = truth.get("reconstruction_note") if isinstance(truth, Mapping) else None
        passed = _all_text(sources) and _text(note)
        evidence.append(
            "reconstruction boundaries are declared"
            if passed
            else "DOCUMENTED_RECONSTRUCTION requires sources and reconstruction_note"
        )
    else:
        disclosure = truth.get("disclosure") if isinstance(truth, Mapping) else None
        passed = _text(disclosure)
        evidence.append("fiction disclosure is explicit" if passed else "DECLARED_FICTION requires disclosure")
    return _gate("C1", "TRUTH_MODE", passed, evidence)


def _causality_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    chain = sc.get("causal_chain")
    beats = _beats(manifest)
    if not isinstance(chain, Mapping):
        return _gate("C2", "CAUSALITY", False, ["story_creation.causal_chain is missing"])
    required = ("cause", "escalation", "consequence", "why_it_mattered")
    missing = [key for key in required if not chain.get(key)]
    escalation = chain.get("escalation")
    role_sequence = [str(beat.get("causal_role", "")) for beat in beats]
    has_hook = any(role in {"hook", "setup", "context"} for role in role_sequence)
    has_escalation = any(role in {"escalation", "complication", "reversal"} for role in role_sequence)
    has_payoff_path = any(role in {"consequence", "payoff", "false_closure", "recurrence", "closure"} for role in role_sequence)
    passed = (
        not missing
        and isinstance(escalation, list)
        and len(escalation) >= 2
        and all(_text(item) for item in escalation)
        and len(beats) >= 3
        and has_hook
        and has_escalation
        and has_payoff_path
    )
    evidence = [
        "cause → escalation → consequence → why it mattered is explicit",
        f"beat roles: {' → '.join(role_sequence)}",
    ]
    if not passed:
        evidence.append("requires two escalation steps and a graph containing setup, escalation and payoff path")
    return _gate("C2", "CAUSALITY", passed, evidence)


def _emotion_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    arc = sc.get("emotional_arc")
    beats = _beats(manifest)
    if not isinstance(arc, Mapping):
        return _gate("C3", "EMOTIONAL_CALIBRATION", False, ["story_creation.emotional_arc is missing"])
    primary = arc.get("primary")
    secondary = arc.get("secondary")
    sensations = arc.get("target_sensations")
    beat_emotions = [beat.get("emotion") for beat in beats]
    passed = (
        _text(primary)
        and primary in ALLOWED_EMOTIONS
        and _text(secondary)
        and secondary in ALLOWED_EMOTIONS
        and _all_text(sensations)
        and len(sensations) <= 4
        and len(beat_emotions) >= 3
        and all(_text(emotion) and emotion in ALLOWED_EMOTIONS for emotion in beat_emotions)
        and len(set(beat_emotions)) >= 3
    )
    evidence = [
        f"primary={primary}, secondary={secondary}",
        f"target sensations={sensations}",
        "beat emotions vary across the arc" if len(set(beat_emotions)) >= 3 else "emotion arc is too flat",
    ]
    return _gate("C3", "EMOTIONAL_CALIBRATION", passed, evidence)


def _promise_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    promise = sc.get("promise_payoff")
    beats = _beats(manifest)
    if not isinstance(promise, Mapping):
        return _gate("C4", "PROMISE_PAYOFF_INTEGRITY", False, ["story_creation.promise_payoff is missing"])
    required = ("promise", "payoff", "payoff_type")
    missing = [key for key in required if not _text(promise.get(key))]
    paid = promise.get("promise_paid") is True
    final_role = beats[-1].get("causal_role") if beats else None
    has_payoff = any(beat.get("causal_role") in {"payoff", "consequence", "recurrence", "closure"} for beat in beats)
    passed = not missing and paid and has_payoff and final_role in {"payoff", "recurrence", "closure", "consequence", "false_closure"}
    evidence = [
        "opening promise and final payoff are both written",
        f"final beat role={final_role}",
    ]
    if not passed:
        evidence.append("promise_paid=true and a final payoff/recurrence/closure beat are required")
    return _gate("C4", "PROMISE_PAYOFF_INTEGRITY", passed, evidence)


def _state_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    beats = _beats(manifest)
    if len(beats) < 3:
        return _gate("C5", "STATE_CHANGE", False, ["at least three causal beats are required"])
    failures: list[str] = []
    transitions: list[str] = []
    for index, beat in enumerate(beats, start=1):
        before = beat.get("state_before")
        after = beat.get("state_after")
        if not _text(before) or not _text(after) or before == after:
            failures.append(f"beat {index} has no meaningful state change")
        else:
            transitions.append(f"{before} → {after}")
    passed = not failures
    evidence = [f"{len(transitions)} state transitions are explicit"]
    evidence.extend(failures[:3])
    return _gate("C5", "STATE_CHANGE", passed, evidence)


def _visual_feasibility_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    feasibility = sc.get("visual_feasibility")
    ids = _scene_ids(manifest)
    if not isinstance(feasibility, Mapping):
        return _gate("C6", "VISUAL_FEASIBILITY_BEFORE_SCRIPT", False, ["visual feasibility checkpoint is missing"])
    planned = feasibility.get("scene_ids")
    approved = feasibility.get("approved_scene_ids")
    ratio = feasibility.get("coverage_ratio")
    legacy = sc.get("legacy_backfill") is True
    checked = feasibility.get("checked_before_script") is True
    passed = (
        isinstance(planned, list)
        and isinstance(approved, list)
        and set(planned) == set(ids)
        and set(approved) == set(ids)
        and _number(ratio)
        and float(ratio) >= 1.0
        and (checked or legacy)
        and (not legacy or _text(sc.get("backfill_reason")))
    )
    evidence = [
        f"approved visual coverage={ratio}",
        "checked before script" if checked else "legacy manifest backfill recorded",
    ]
    if not passed:
        evidence.append("every scene must have an approved visual route before script lock")
    return _gate("C6", "VISUAL_FEASIBILITY_BEFORE_SCRIPT", passed, evidence)


def _diversity_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    diversity = sc.get("channel_diversity")
    if not isinstance(diversity, Mapping):
        return _gate("C7", "CHANNEL_DIVERSITY", False, ["channel diversity checkpoint is missing"])
    score = diversity.get("similarity_score")
    count = diversity.get("recent_episode_count")
    signature = diversity.get("unique_signature")
    status = diversity.get("similarity_status")
    legacy = sc.get("legacy_backfill") is True
    passed = (
        _number(score)
        and 0 <= float(score) <= 1
        and isinstance(count, int)
        and count >= 0
        and _text(signature)
        and status in {"PASS", "BASELINE"}
        and float(score) <= 0.55
        and (status == "PASS" or legacy)
    )
    evidence = [f"similarity_score={score}", f"status={status}", f"signature={signature}"]
    if not passed:
        evidence.append("new episodes must remain below 0.55 similarity and carry a unique signature")
    return _gate("C7", "CHANNEL_DIVERSITY", passed, evidence)


def _authorship_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    authorship = sc.get("original_authorship")
    if not isinstance(authorship, Mapping):
        return _gate("C8", "ORIGINAL_AUTHORSHIP", False, ["original authorship checkpoint is missing"])
    required_true = ("original_script", "original_narration", "editorial_transform", "asset_provenance_complete")
    missing = [key for key in required_true if authorship.get(key) is not True]
    risk = authorship.get("mass_production_risk")
    passed = not missing and risk == "LOW"
    evidence = [
        "script, narration, editorial transformation and asset provenance are marked original/complete",
        f"mass_production_risk={risk}",
    ]
    if missing:
        evidence.append(f"missing approvals: {', '.join(missing)}")
    return _gate("C8", "ORIGINAL_AUTHORSHIP", passed, evidence)


def _monetization_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    policy = sc.get("monetization_safety")
    if not isinstance(policy, Mapping):
        return _gate("C9", "MONETIZATION_SAFETY", False, ["monetization safety profile is missing"])
    risks = policy.get("risk_flags", {})
    if not isinstance(risks, Mapping):
        risks = {}
    blocked_values = {"HIGH", "GRAPHIC", "PRESENT", "UNVERIFIED", "MISLEADING"}
    blocked = [key for key, value in risks.items() if str(value).upper() in blocked_values]
    passed = (
        policy.get("youtube_ad_safety") in {"SAFE", "LOW_RISK"}
        and policy.get("tiktok_originality") in {"ORIGINAL", "TRANSFORMATIVE"}
        and policy.get("claims_reviewed") is True
        and not blocked
        and policy.get("disclosure_present") is True
    )
    evidence = [
        f"YouTube={policy.get('youtube_ad_safety')}",
        f"TikTok={policy.get('tiktok_originality')}",
        "claims reviewed and disclosure present" if passed else "claims/disclosure/risk profile incomplete",
    ]
    if blocked:
        evidence.append(f"blocking risk flags: {', '.join(blocked)}")
    return _gate("C9", "MONETIZATION_SAFETY", passed, evidence)


def _padding_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    duration = sc.get("duration")
    if not isinstance(duration, Mapping):
        return _gate("C10", "NO_PADDING", False, ["duration planning block is missing"])
    target = duration.get("target_seconds")
    planned = duration.get("planned_seconds")
    narration = duration.get("estimated_narration_seconds")
    padding = duration.get("padding_seconds")
    scene_total = sum(float(scene.get("duration", 0)) for scene in manifest.get("scenes", []) if isinstance(scene, Mapping))
    passed = (
        _number(target)
        and 60 <= float(target) <= 75
        and _number(planned)
        and 60 <= float(planned) <= 75
        and _number(narration)
        and _number(padding)
        and float(padding) <= 1.5
        and abs(float(planned) - scene_total) <= 1.5
        and duration.get("padding_status") == "PASS"
    )
    evidence = [
        f"planned={planned}s, narration={narration}s, scene_total={scene_total:.2f}s",
        f"padding={padding}s",
    ]
    if not passed:
        evidence.append("the 60–75 second target must be reached by story density, not filler")
    return _gate("C10", "NO_PADDING", passed, evidence)


def _red_team_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    red_team = sc.get("red_team")
    if not isinstance(red_team, Mapping):
        return _gate("C11", "RED_TEAM", False, ["editorial, factual and monetization red teams are missing"])
    reviewers = ("editorial", "factual", "monetization")
    failures: list[str] = []
    for reviewer in reviewers:
        entry = red_team.get(reviewer)
        if not isinstance(entry, Mapping) or entry.get("status") != "PASS":
            failures.append(f"{reviewer}=BLOCKED")
        elif entry.get("blocking_issues"):
            failures.append(f"{reviewer} has blocking_issues")
    passed = not failures and red_team.get("status") == "PASS"
    evidence = ["three independent pre-render red teams passed"]
    evidence.extend(failures)
    return _gate("C11", "RED_TEAM", passed, evidence)


def audit_story_creation(
    manifest: Mapping[str, Any],
    recent_manifests: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a deterministic creation-layer report for one episode."""
    if not isinstance(manifest, Mapping):
        raise StoryCreationError("manifest must be a mapping")
    sc = _story_block(manifest)
    gates = [
        _idea_gate(manifest, sc),
        _truth_gate(manifest, sc),
        _causality_gate(manifest, sc),
        _emotion_gate(manifest, sc),
        _promise_gate(manifest, sc),
        _state_gate(manifest, sc),
        _visual_feasibility_gate(manifest, sc),
        _diversity_gate(manifest, sc),
        _authorship_gate(manifest, sc),
        _monetization_gate(manifest, sc),
        _padding_gate(manifest, sc),
        _red_team_gate(manifest, sc),
    ]
    blocked = [gate["code"] for gate in gates if gate["status"] != "PASS"]
    return {
        "schema_version": "1.0",
        "status": "STORY_CREATION_PASS" if not blocked else "STORY_CREATION_BLOCKED",
        "video_id": manifest.get("video_id"),
        "title": manifest.get("title"),
        "gates": gates,
        "blocked_gates": blocked,
        "reviewed_dimensions": [
            "hook",
            "causal_escalation",
            "promise_payoff",
            "state_change",
            "emotional_arc",
            "visual_feasibility",
            "channel_diversity",
            "original_authorship",
            "monetization_safety",
            "duration_density",
            "red_team",
        ],
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoryCreationError(f"cannot read manifest {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the pre-render story creation layer.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = audit_story_creation(load_manifest(args.manifest))
    except StoryCreationError as exc:
        report = {
            "schema_version": "1.0",
            "status": "STORY_CREATION_BLOCKED",
            "blocked_gates": ["C0"],
            "error": str(exc),
            "gates": [],
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "blocked_gates": report.get("blocked_gates", [])}))
    return 0 if report["status"] == "STORY_CREATION_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
