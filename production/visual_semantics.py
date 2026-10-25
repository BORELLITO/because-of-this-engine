#!/usr/bin/env python3
"""Semantic visual-story contract for Because of This Engine v2.

The engine must select footage for the narrated beat, not for an isolated
keyword.  This module deliberately uses a small, auditable ontology instead
of opaque similarity: subject, action, environment, object, mood and
forbidden concepts are recorded with every approved asset.
"""

from __future__ import annotations

import re
from typing import Any

DIMENSIONS = ("subjects", "actions", "environments", "objects", "moods", "composition")

# Canonical concepts with controlled aliases.  This is intentionally small and
# reviewable; unknown terms never become a silent semantic match.
CONCEPT_ALIASES: dict[str, set[str]] = {
    "person": {"person", "people", "human", "man", "woman", "figure", "guard", "officer"},
    "silhouette": {"silhouette", "shadow", "shadows", "dark figure", "mysterious figure"},
    "security_guard": {"security guard", "guard", "watchman", "security officer"},
    "hotel": {"hotel", "motel", "inn", "lodge", "abandoned hotel"},
    "interior": {"interior", "inside", "room", "building"},
    "hallway": {"hallway", "corridor", "passage", "hall"},
    "glass_door": {"glass door", "glass", "windowed door", "glass wall"},
    "sealed_room": {"sealed room", "sealed", "locked room", "locked door", "locked"},
    "security_camera": {"security camera", "surveillance camera", "cctv", "camera", "monitor"},
    "clock": {"clock", "analog clock", "wall clock", "time", "3:17", "3:18"},
    "screen": {"screen", "monitor", "laptop", "display", "recording"},
    "light": {"light", "lights", "lamp", "wall lamp", "illumination"},
    "darkness": {"dark", "darkness", "night", "dim", "black"},
    "police": {"police", "police officer", "officer"},
    "footprints": {"footprints", "footprint", "tracks", "shoeprints"},
    "lock": {"lock", "locked", "padlock", "broken lock"},
    "smoke": {"smoke", "mist", "fog", "haze"},
    "hourglass": {"hourglass", "sand timer", "falling sand"},
    "medical_vial": {"ampoule", "ampule", "vial", "medical vial", "medicine", "syringe"},
    "laboratory": {"laboratory", "lab", "clinic", "hospital", "medical room"},
    "beach": {"beach", "ocean", "sea", "sand", "palm tree"},
    "office": {"office", "corporate office", "desk office"},
    "standing": {"standing", "stand", "wait", "waiting", "still"},
    "watching": {"watching", "watch", "monitoring", "recording", "observing"},
    "pressing": {"pressing", "pressed", "hands against glass", "face against glass"},
    "pointing": {"pointing", "point", "points", "gesture", "raises one hand"},
    "opening": {"opening", "open", "opened", "door opens"},
    "flickering": {"flickering", "flicker", "flashing", "lights out", "power outage"},
    "running": {"running", "run", "runs", "fleeing", "escape"},
    "demolition": {"demolished", "demolition", "destroyed", "wrecking"},
    "eerie": {"eerie", "ominous", "sinister", "suspense", "mysterious", "creepy"},
    "close_up": {"close up", "close-up", "detail shot", "macro"},
    "wide_shot": {"wide shot", "wide", "establishing shot", "long shot"},
}

MATCH_COVERAGE = {
    "EXACT": 1.0,
    "NEAR": 0.66,
    "EXPLANATORY": 0.50,
    "SYMBOLIC": 0.34,
    "ATMOSPHERE": 0.25,
}


def normalize(value: Any) -> str:
    text = str(value or "").lower().replace("_", " ").replace("-", " ")
    return re.sub(r"[^a-z0-9: ]+", " ", text).strip()


def values(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def aliases(value: Any) -> set[str]:
    raw = normalize(value)
    result = {raw} if raw else set()
    for canonical, variants in CONCEPT_ALIASES.items():
        normalized_variants = {normalize(item) for item in variants}
        if raw == canonical or raw in normalized_variants:
            result.add(canonical)
            result.update(normalized_variants)
    return result


def text_has_concept(text: str, concept: str) -> bool:
    normalized_text = normalize(text)
    wanted = aliases(concept)
    return any(
        phrase and (phrase in normalized_text or phrase.replace(" ", "") in normalized_text.replace(" ", ""))
        for phrase in wanted
    )


def _dimension_values(record: dict[str, Any], dimension: str) -> list[str]:
    evidence = record.get("visual_evidence") or {}
    if isinstance(evidence, dict) and values(evidence.get(dimension)):
        return values(evidence.get(dimension))
    return []


def evidence_text(record: dict[str, Any]) -> str:
    evidence = record.get("visual_evidence") or {}
    parts: list[str] = []
    for key in ("source_title", "source_description", "title", "description", "tags", "category", "mood", "motion", "composition"):
        parts.extend(values(record.get(key)))
    if isinstance(evidence, dict):
        for key in ("source_title", "source_description", "notes", *DIMENSIONS):
            parts.extend(values(evidence.get(key)))
    parts.extend(values(record.get("source_page_url")))
    return " ".join(parts)


def _matched(required: list[str], available: list[str], text: str) -> list[str]:
    found: list[str] = []
    available_text = " ".join(available)
    for wanted in required:
        if any(text_has_concept(candidate, wanted) for candidate in available):
            found.append(wanted)
        elif text_has_concept(available_text, wanted) or text_has_concept(text, wanted):
            found.append(wanted)
    return found


def _available_for_dimension(record: dict[str, Any], dimension: str) -> list[str]:
    explicit = _dimension_values(record, dimension)
    if explicit:
        return explicit
    # Search metadata only as a fallback.  The approved record should still
    # carry explicit visual_evidence for a final release.
    return [evidence_text(record)]


def visual_match_report(scene: dict[str, Any], candidate: dict[str, Any], *, require_review: bool = False) -> dict[str, Any]:
    spec = scene.get("visual_semantics") or {}
    if not isinstance(spec, dict):
        return {
            "status": "BLOCKED",
            "score": 0.0,
            "reason": "scene.visual_semantics is missing",
            "missing_contract": ["visual_semantics"],
        }

    required = spec.get("required") or {}
    preferred = spec.get("preferred") or {}
    forbidden = values(spec.get("forbidden"))
    role = str(spec.get("role", "literal")).lower()
    text = evidence_text(candidate)
    evidence = candidate.get("visual_evidence") or {}
    reviewed = isinstance(evidence, dict) and evidence.get("reviewed") is True
    basis = str(evidence.get("basis", "")).strip() if isinstance(evidence, dict) else ""

    forbidden_hits = [item for item in forbidden if text_has_concept(text, item)]
    matched: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    required_count = 0
    matched_count = 0
    anchor_hits = 0

    for dimension in DIMENSIONS:
        wanted = values(required.get(dimension))
        if not wanted:
            continue
        required_count += len(wanted)
        found = _matched(wanted, _available_for_dimension(candidate, dimension), text)
        matched[dimension] = found
        missing[dimension] = [item for item in wanted if item not in found]
        matched_count += len(found)
        if found and dimension in {"subjects", "actions", "environments", "objects"}:
            anchor_hits += 1

    preferred_count = sum(len(values(preferred.get(dimension))) for dimension in DIMENSIONS)
    preferred_hits = 0
    for dimension in DIMENSIONS:
        wanted = values(preferred.get(dimension))
        if wanted:
            preferred_hits += len(_matched(wanted, _available_for_dimension(candidate, dimension), text))

    coverage = matched_count / required_count if required_count else 0.0
    preferred_coverage = preferred_hits / preferred_count if preferred_count else 0.0
    if required_count:
        score = round(min(1.0, 0.78 * coverage + 0.17 * preferred_coverage + 0.05 * min(anchor_hits / 4, 1.0)), 4)
    else:
        score = round(min(1.0, 0.70 * preferred_coverage + 0.30 * (0.0 if not text_has_concept(text, "eerie") else 1.0)), 4)

    claimed_match = str(scene.get("visual_match", "NEAR")).upper()
    needed_coverage = MATCH_COVERAGE.get(claimed_match, MATCH_COVERAGE["NEAR"])
    min_anchors = 1 if role in {"symbolic", "atmosphere"} else 2
    reasons: list[str] = []
    if forbidden_hits:
        reasons.append("forbidden concepts detected: " + ", ".join(forbidden_hits))
    if require_review and not reviewed:
        reasons.append("visual evidence was not reviewed")
    if require_review and not basis:
        reasons.append("visual evidence basis is missing")
    if required_count and coverage < needed_coverage:
        reasons.append(f"required visual coverage {coverage:.2f} is below {needed_coverage:.2f} for {claimed_match}")
    if required_count and anchor_hits < min_anchors:
        reasons.append(f"only {anchor_hits} narrative anchor dimension(s) matched; at least {min_anchors} required")

    status = "PASS" if not reasons else "BLOCKED"
    return {
        "status": status,
        "score": score,
        "claimed_match": claimed_match,
        "role": role,
        "coverage": round(coverage, 4),
        "preferred_coverage": round(preferred_coverage, 4),
        "matched": matched,
        "missing": missing,
        "forbidden_hits": forbidden_hits,
        "reviewed": reviewed,
        "evidence_basis": basis,
        "reason": "; ".join(reasons) if reasons else "subject/action/environment/object fit passed",
    }


def require_visual_fit(scene: dict[str, Any], candidate: dict[str, Any], *, mode: str = "preview") -> dict[str, Any]:
    evidence = candidate.get("visual_evidence")
    if not isinstance(evidence, dict):
        raise ValueError(f"Scene {scene.get('scene_id', '?')} asset requires visual_evidence.")
    report = visual_match_report(scene, candidate, require_review=True)
    if report["status"] != "PASS":
        raise ValueError(f"Scene {scene.get('scene_id', '?')} visual semantic gate blocked: {report['reason']}")
    if mode == "final" and evidence.get("reviewed") is not True:
        raise ValueError(f"Scene {scene.get('scene_id', '?')} requires reviewed visual evidence for final release.")
    return report
