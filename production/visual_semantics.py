#!/usr/bin/env python3
"""Auditable visual semantics for Because of This Engine v2.

Metadata can discover a candidate, but only explicit reviewed visual evidence
can approve it for a narrative beat.  The ontology is intentionally small and
fail-closed so generic words cannot launder an unrelated clip into a match.
"""

from __future__ import annotations

import re
from typing import Any

DIMENSIONS = ("subjects", "actions", "environments", "objects", "moods", "composition")
ALLOWED_ROLES = {"literal", "explanatory", "symbolic", "atmosphere"}
MOTION_SENSITIVE_ACTIONS = {"running", "walking", "pointing", "opening", "recording", "flickering", "demolition"}

CONCEPT_ALIASES: dict[str, set[str]] = {
    "person": {"person", "people", "human", "man", "woman", "figure", "guard", "officer"},
    "figure": {"figure", "silhouette", "shadow", "dark figure", "mysterious figure"},
    "silhouette": {"silhouette", "shadow", "shadows", "dark figure", "mysterious figure"},
    "security_guard": {"security guard", "guard", "watchman", "security officer"},
    "hotel": {"hotel", "motel", "inn", "lodge", "abandoned hotel"},
    "interior": {"interior", "inside", "room", "building"},
    "hallway": {"hallway", "corridor", "passage", "hall"},
    "glass_door": {"glass door", "windowed door"},
    "glass_surface": {"glass surface", "glass", "window", "windows", "glass window", "glass windows"},
    "sealed_room": {"sealed room", "sealed", "locked room", "locked door", "locked"},
    "security_camera": {"security camera", "surveillance camera", "cctv"},
    "clock": {"clock", "analog clock", "wall clock", "time", "3:17", "3:18"},
    "screen": {"screen", "laptop", "display"},
    "light": {"light", "lights", "lamp", "wall lamp", "illumination"},
    "darkness": {"dark", "darkness", "night", "dim", "black"},
    "police": {"police", "police officer", "officer"},
    "footprints": {"footprints", "footprint", "tracks", "shoeprints"},
    "lock": {"lock", "locked", "padlock", "broken lock"},
    "smoke": {"smoke", "mist", "fog", "haze"},
    "hourglass": {"hourglass", "sand timer", "falling sand"},
    "medical_vial": {"ampoule", "ampule", "vial", "medical vial", "medicine", "syringe"},
    "laboratory": {"laboratory", "lab", "clinic", "hospital", "medical room"},
    "beach": {"beach", "ocean", "sea", "palm tree"},
    "office": {"office", "corporate office", "desk office"},
    "standing": {"standing", "stand", "wait", "waiting", "still"},
    "watching": {"watching", "watch", "monitoring", "observing"},
    "recording": {"recording", "records", "captured", "surveillance footage"},
    "pressing": {"pressing", "pressed", "hands against glass", "face against glass"},
    "pointing": {"pointing", "point", "points", "gesture", "raises one hand"},
    "opening": {"opening", "open", "opened", "door opens"},
    "flickering": {"flickering", "flicker", "flashing", "lights out", "power outage"},
    "running": {"running", "run", "runs", "fleeing", "escape"},
    "walking": {"walking", "walk", "walks", "jogging", "jog"},
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

# Concrete anchors are intentionally narrow.  They prevent an atmospheric
# metaphor from substituting for a narrated event such as demolition, running,
# pointing or recording.  Abstract concepts like time and fear are not anchors.
NARRATIVE_ANCHOR_DIMENSIONS = {
    "person": "subjects",
    "figure": "subjects",
    "silhouette": "subjects",
    "security_guard": "subjects",
    "police": "subjects",
    "camera": "objects",
    "security_camera": "objects",
    "glass_door": "objects",
    "glass_surface": "objects",
    "lock": "objects",
    "light": "objects",
    "hourglass": "objects",
    "footprints": "objects",
    "recording": "actions",
    "standing": "actions",
    "walking": "actions",
    "running": "actions",
    "pointing": "actions",
    "opening": "actions",
    "flickering": "actions",
    "demolition": "actions",
    "hotel": "environments",
    "hallway": "environments",
    "interior": "environments",
    "exterior": "environments",
    "darkness": "environments",
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
    for phrase in aliases(concept):
        if not phrase:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
        if re.search(pattern, normalized_text):
            return True
    return False


def _dimension_values(record: dict[str, Any], dimension: str) -> list[str]:
    evidence = record.get("visual_evidence") or {}
    if isinstance(evidence, dict):
        return values(evidence.get(dimension))
    return []


def observed_evidence_text(record: dict[str, Any]) -> str:
    """Return only reviewer-declared observations from sampled pixels."""
    evidence = record.get("visual_evidence") or {}
    if not isinstance(evidence, dict):
        return ""
    parts: list[str] = []
    for key in ("observed_subjects", "observed_actions", "observed_environments", "observed_objects"):
        parts.extend(values(evidence.get(key)))
    return " ".join(parts)


def evidence_text(record: dict[str, Any]) -> str:
    """Return discovery/review text, never editorial notes or source URLs."""
    evidence = record.get("visual_evidence") or {}
    parts: list[str] = []
    for key in ("source_title", "source_description", "title", "description", "tags", "category", "mood", "motion", "composition"):
        parts.extend(values(record.get(key)))
    if isinstance(evidence, dict):
        for key in ("source_title", "source_description", *DIMENSIONS):
            parts.extend(values(evidence.get(key)))
    return " ".join(parts)


def _available_for_dimension(
    record: dict[str, Any],
    dimension: str,
    *,
    allow_text_fallback: bool,
) -> list[str]:
    explicit = _dimension_values(record, dimension)
    if explicit:
        return explicit
    return [evidence_text(record)] if allow_text_fallback else []


def _matched(
    required: list[str],
    available: list[str],
    text: str,
    *,
    allow_text_fallback: bool,
) -> list[str]:
    found: list[str] = []
    available_text = " ".join(available)
    for wanted in required:
        if any(text_has_concept(candidate, wanted) for candidate in available):
            found.append(wanted)
        elif allow_text_fallback and text_has_concept(available_text or text, wanted):
            found.append(wanted)
    return found


def _merged_dimensions(*specs: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for dimension in DIMENSIONS:
        result: list[str] = []
        for spec in specs:
            if not isinstance(spec, dict):
                continue
            for item in values(spec.get(dimension)):
                if item not in result:
                    result.append(item)
        if result:
            merged[dimension] = result
    return merged


def _pixel_review_issues(scene: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    evidence = candidate.get("visual_evidence") or {}
    if not isinstance(evidence, dict):
        return ["visual_evidence is missing"]
    issues: list[str] = []
    for key in ("reviewer", "reviewed_at", "review_method"):
        if not str(evidence.get(key, "")).strip():
            issues.append(f"pixel evidence requires {key}")
    timestamps = evidence.get("sample_timestamps")
    if not isinstance(timestamps, list) or len(timestamps) < 3:
        issues.append("pixel evidence requires at least three sample_timestamps")
    elif any(isinstance(item, bool) or not isinstance(item, (int, float)) or item < 0 for item in timestamps):
        issues.append("pixel evidence sample_timestamps must be non-negative numbers")
    for key in ("observed_subjects", "observed_actions", "observed_environments", "observed_objects"):
        if not isinstance(evidence.get(key), list):
            issues.append(f"pixel evidence requires {key}")
    spec = candidate.get("_visual_semantics_for_review") or scene.get("visual_semantics") or {}
    required_actions = _merged_dimensions(spec.get("required") or {}, spec.get("critical") or {}).get("actions", [])
    if set(required_actions) & MOTION_SENSITIVE_ACTIONS:
        if not evidence.get("action_window") and not evidence.get("usable_window"):
            issues.append("motion-sensitive beat requires action_window or usable_window")
    return issues


def _narrative_anchor_report(
    scene: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Verify direct visual evidence for concrete narrated anchors.

    A scene may still use symbolism for mood, time or uncertainty, but an
    explicitly declared concrete anchor must be visible in the reviewed
    evidence.  This is deliberately separate from the generic semantic score,
    which otherwise allows a strong symbolic match to hide a missing event.
    """
    spec = scene.get("visual_semantics") or {}
    contract = spec.get("narrative_anchors")
    if not isinstance(contract, dict) or not contract:
        return {
            "status": "BLOCKED",
            "direct_required": [],
            "direct_hits": [],
            "direct_missing": [],
            "minimum_direct": 0,
            "invalid": ["narrative_anchors is required for every scene"],
        }

    direct_required = values(contract.get("direct_required"))
    direct_hits: list[str] = []
    direct_missing: list[str] = []
    invalid: list[str] = []
    for anchor in direct_required:
        normalized = normalize(anchor).replace(" ", "_")
        dimension = NARRATIVE_ANCHOR_DIMENSIONS.get(normalized)
        if not dimension:
            invalid.append(anchor)
            continue
        available = _available_for_dimension(
            candidate,
            dimension,
            allow_text_fallback=False,
        )
        if any(text_has_concept(item, anchor) for item in available):
            direct_hits.append(anchor)
        else:
            direct_missing.append(anchor)

    minimum_raw = contract.get("minimum_direct", 1 if direct_required else 0)
    try:
        minimum_direct = int(minimum_raw)
    except (TypeError, ValueError):
        minimum_direct = -1
    if minimum_direct < 0 or minimum_direct > len(direct_required):
        invalid.append("minimum_direct")
    status = (
        "PASS"
        if not invalid and len(direct_hits) >= minimum_direct
        else "BLOCKED"
    )
    return {
        "status": status,
        "direct_required": direct_required,
        "direct_hits": direct_hits,
        "direct_missing": direct_missing,
        "minimum_direct": minimum_direct,
        "invalid": invalid,
    }


def visual_match_report(
    scene: dict[str, Any],
    candidate: dict[str, Any],
    *,
    require_review: bool = False,
) -> dict[str, Any]:
    spec = scene.get("visual_semantics") or {}
    if not isinstance(spec, dict):
        return {
            "status": "BLOCKED",
            "score": 0.0,
            "reason": "scene.visual_semantics is missing",
            "missing_contract": ["visual_semantics"],
        }

    role = str(spec.get("role", "literal")).lower()
    narrative_contract_declared = isinstance(spec.get("narrative_anchors"), dict)
    narrative_alignment = (
        _narrative_anchor_report(scene, candidate)
        if narrative_contract_declared
        else {
            "status": "NOT_DECLARED",
            "direct_required": [],
            "direct_hits": [],
            "direct_missing": [],
            "minimum_direct": 0,
            "invalid": [],
        }
    )
    required = spec.get("required") or {}
    critical = spec.get("critical") or {}
    preferred = spec.get("preferred") or {}
    forbidden = values(spec.get("forbidden")) + values(spec.get("must_not_show"))
    semantic_required = _merged_dimensions(required, critical)
    has_semantic_contract = bool(semantic_required or _merged_dimensions(preferred))
    text = evidence_text(candidate)
    evidence = candidate.get("visual_evidence") or {}
    reviewed = isinstance(evidence, dict) and evidence.get("reviewed") is True
    basis = str(evidence.get("basis", "")).strip() if isinstance(evidence, dict) else ""
    allow_text_fallback = not require_review

    forbidden_basis = observed_evidence_text(candidate) if require_review else text
    forbidden_hits = [item for item in forbidden if text_has_concept(forbidden_basis, item)]
    matched: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    critical_missing: dict[str, list[str]] = {}
    required_count = 0
    matched_count = 0
    anchor_hits = 0

    for dimension in DIMENSIONS:
        wanted = values(semantic_required.get(dimension))
        if not wanted:
            continue
        required_count += len(wanted)
        available = _available_for_dimension(
            candidate,
            dimension,
            allow_text_fallback=allow_text_fallback,
        )
        found = _matched(wanted, available, text, allow_text_fallback=allow_text_fallback)
        matched[dimension] = found
        missing[dimension] = [item for item in wanted if item not in found]
        critical_wanted = values(critical.get(dimension))
        critical_missing[dimension] = [item for item in critical_wanted if item not in found]
        if not critical_missing[dimension]:
            critical_missing.pop(dimension)
        matched_count += len(found)
        if found and dimension in {"subjects", "actions", "environments", "objects"}:
            anchor_hits += 1

    preferred_count = sum(len(values(preferred.get(dimension))) for dimension in DIMENSIONS)
    preferred_hits = 0
    for dimension in DIMENSIONS:
        wanted = values(preferred.get(dimension))
        if not wanted:
            continue
        available = _available_for_dimension(
            candidate,
            dimension,
            allow_text_fallback=allow_text_fallback,
        )
        preferred_hits += len(_matched(wanted, available, text, allow_text_fallback=allow_text_fallback))

    coverage = matched_count / required_count if required_count else 0.0
    preferred_coverage = preferred_hits / preferred_count if preferred_count else 0.0
    if required_count:
        score = round(min(1.0, 0.78 * coverage + 0.17 * preferred_coverage + 0.05 * min(anchor_hits / 4, 1.0)), 4)
    else:
        score = round(min(1.0, 0.70 * preferred_coverage + 0.30 * (0.0 if not text_has_concept(text, "eerie") else 1.0)), 4)

    claimed_match = str(scene.get("visual_match", "NEAR")).upper()
    needed_coverage = MATCH_COVERAGE.get(claimed_match, MATCH_COVERAGE["NEAR"])
    required_dimensions = sum(
        1 for dimension in ("subjects", "actions", "environments", "objects")
        if values(semantic_required.get(dimension))
    )
    min_anchors = 1 if role in {"symbolic", "atmosphere"} else min(2, required_dimensions)
    reasons: list[str] = []
    if narrative_alignment["status"] == "BLOCKED" and narrative_alignment["invalid"]:
        reasons.append("invalid narrative anchor contract: " + ", ".join(narrative_alignment["invalid"]))
    if narrative_alignment["status"] == "BLOCKED" and (
        narrative_alignment["direct_missing"]
        or len(narrative_alignment["direct_hits"]) < narrative_alignment["minimum_direct"]
    ):
        reasons.append(
            "direct narrative anchors missing: "
            + ", ".join(narrative_alignment["direct_missing"] or ["minimum_direct"])
        )
    if role not in ALLOWED_ROLES:
        reasons.append(f"invalid visual semantic role: {role}")
    if not has_semantic_contract:
        reasons.append("visual_semantics must declare required, critical or preferred dimensions")
    if forbidden_hits:
        reasons.append("forbidden concepts detected: " + ", ".join(forbidden_hits))
    if require_review and not reviewed:
        reasons.append("visual evidence was not reviewed")
    if require_review and not basis:
        reasons.append("visual evidence basis is missing")
    if critical_missing:
        reasons.append("critical visual anchors missing: " + ", ".join(
            f"{dimension}={','.join(items)}" for dimension, items in critical_missing.items()
        ))
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
        "critical_missing": critical_missing,
        "forbidden_hits": forbidden_hits,
        "reviewed": reviewed,
        "evidence_basis": basis,
        "pixel_evidence": {
            "status": "PRESENT" if not _pixel_review_issues(scene, {**candidate, "_visual_semantics_for_review": spec}) else "MISSING_OR_INCOMPLETE",
            "issues": _pixel_review_issues(scene, {**candidate, "_visual_semantics_for_review": spec}),
        },
        "narrative_alignment": narrative_alignment,
        "reason": "; ".join(reasons) if reasons else "subject/action/environment/object fit passed",
    }


def require_visual_fit(
    scene: dict[str, Any],
    candidate: dict[str, Any],
    *,
    mode: str = "preview",
) -> dict[str, Any]:
    evidence = candidate.get("visual_evidence")
    if not isinstance(evidence, dict):
        raise ValueError(f"Scene {scene.get('scene_id', '?')} asset requires visual_evidence.")
    report = visual_match_report(scene, candidate, require_review=True)
    if report["status"] != "PASS":
        raise ValueError(f"Scene {scene.get('scene_id', '?')} visual semantic gate blocked: {report['reason']}")
    if mode == "final":
        pixel_issues = _pixel_review_issues(scene, candidate)
        if pixel_issues:
            raise ValueError(
                f"Scene {scene.get('scene_id', '?')} pixel evidence gate blocked: "
                + "; ".join(pixel_issues)
            )
    return report
