"""Senior editorial gates for story depth and narrative memorability.

The legacy C0-C11 checks validate that a story has the expected production fields.
This module adds a stricter, deterministic editorial contract so a sequence of
atmospheric anomalies cannot pass as a complete human story.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


EDITORIAL_GATES = (
    ("E0", "EDITORIAL_CONTRACT"),
    ("E1", "PROTAGONIST_AGENCY"),
    ("E2", "WOUND_DRAMATIZATION"),
    ("E3", "CAUSAL_ESCALATION"),
    ("E4", "ANOMALY_RULE_AND_COST"),
    ("E5", "EMOTIONAL_TURNS"),
    ("E6", "PAYOFF_RECONTEXTUALIZATION"),
    ("E7", "VISUAL_DRAMATIZATION"),
    ("E8", "NARRATIVE_DENSITY"),
    ("E9", "ORIGINAL_MECHANISM"),
    ("E10", "NARRATION_DRAMATIZATION"),
)

PAYOFF_TYPES = {"recontextualization", "reversal", "earned_consequence"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _gate(code: str, name: str, passed: bool, evidence: Iterable[str]) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "status": "PASS" if passed else "BLOCKED",
        "evidence": list(evidence),
    }


def _scene_ids(manifest: Mapping[str, Any]) -> list[str]:
    return [
        str(scene.get("scene_id"))
        for scene in manifest.get("scenes", [])
        if isinstance(scene, Mapping) and _text(scene.get("scene_id"))
    ]


def _beat_ids(manifest: Mapping[str, Any]) -> list[str]:
    graph = manifest.get("story_graph") or {}
    beats = graph.get("beats", []) if isinstance(graph, Mapping) else []
    return [
        str(beat.get("scene_id") or beat.get("beat_id"))
        for beat in beats
        if isinstance(beat, Mapping) and _text(beat.get("scene_id") or beat.get("beat_id"))
    ]


def _valid_ids(values: Any, known: set[str]) -> bool:
    return (
        isinstance(values, list)
        and bool(values)
        and all(_text(value) and str(value) in known for value in values)
    )


def _contract(sc: Mapping[str, Any]) -> Mapping[str, Any]:
    value = sc.get("editorial_contract")
    return value if isinstance(value, Mapping) else {}


def _contract_gate(sc: Mapping[str, Any]) -> dict[str, Any]:
    contract = _contract(sc)
    required = (
        "protagonist",
        "wound",
        "causal_escalation",
        "anomaly_rule",
        "emotional_turns",
        "payoff",
        "visual_dramatization",
        "density",
        "originality",
        "narration",
    )
    missing = [key for key in required if key not in contract]
    passed = bool(contract) and not missing
    evidence = (
        ["explicit v7.4 editorial contract is present with all required sections"]
        if passed
        else ["new episodes require story_creation.editorial_contract"]
    )
    if missing:
        evidence.append(f"missing sections: {', '.join(missing)}")
    return _gate("E0", "EDITORIAL_CONTRACT", passed, evidence)


def _agency_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    protagonist = _contract(sc).get("protagonist")
    required = (
        "name",
        "goal",
        "wound",
        "flaw",
        "agency_action",
        "decision_scene_id",
        "irreversible_choice",
        "cost",
        "change",
    )
    missing = [key for key in required if not isinstance(protagonist, Mapping) or not _text(protagonist.get(key))]
    known = set(_scene_ids(manifest)) | set(_beat_ids(manifest))
    decision_scene = protagonist.get("decision_scene_id") if isinstance(protagonist, Mapping) else None
    passed = not missing and str(decision_scene) in known
    evidence = [
        "the protagonist has a goal, a contradiction, an active choice and a measurable change",
        f"decision_scene_id={decision_scene}",
    ]
    if missing:
        evidence.append(f"missing protagonist fields: {', '.join(missing)}")
    if decision_scene and str(decision_scene) not in known:
        evidence.append("decision_scene_id is not present in the story graph")
    return _gate("E1", "PROTAGONIST_AGENCY", passed, evidence)


def _wound_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    wound = _contract(sc).get("wound")
    known = set(_scene_ids(manifest)) | set(_beat_ids(manifest))
    required = ("wound_scene_ids", "manifestation", "conflict", "link_to_choice")
    missing = [key for key in required if not isinstance(wound, Mapping) or not wound.get(key)]
    scene_ids = wound.get("wound_scene_ids") if isinstance(wound, Mapping) else None
    passed = (
        not missing
        and _valid_ids(scene_ids, known)
        and all(_text(wound.get(key)) for key in ("manifestation", "conflict", "link_to_choice"))
    )
    evidence = [
        f"wound is dramatized in scenes={scene_ids}",
        "the wound changes the protagonist's decision rather than merely describing backstory",
    ]
    if not passed:
        evidence.append("wound_scene_ids, manifestation, conflict and link_to_choice are required")
    return _gate("E2", "WOUND_DRAMATIZATION", passed, evidence)


def _causal_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    escalation = _contract(sc).get("causal_escalation")
    known = set(_scene_ids(manifest)) | set(_beat_ids(manifest))
    required = ("from_scene", "to_scene", "trigger", "protagonist_action", "new_cost", "state_change")
    failures: list[str] = []
    if not isinstance(escalation, list) or len(escalation) < 3:
        failures.append("at least three action → consequence links are required")
        escalation_items: list[Any] = []
    else:
        escalation_items = escalation
        for index, item in enumerate(escalation, start=1):
            if not isinstance(item, Mapping):
                failures.append(f"link {index} is not an object")
                continue
            missing = [key for key in required if not _text(item.get(key))]
            if missing:
                failures.append(f"link {index} missing: {', '.join(missing)}")
            for key in ("from_scene", "to_scene"):
                if _text(item.get(key)) and str(item.get(key)) not in known:
                    failures.append(f"link {index} references unknown {key}={item.get(key)}")
            if item.get("from_scene") == item.get("to_scene"):
                failures.append(f"link {index} does not move to a new scene")
    passed = not failures
    evidence = [
        f"causal links={len(escalation_items)}",
        "each escalation has a trigger, protagonist action, new cost and state change",
    ]
    evidence.extend(failures[:5])
    return _gate("E3", "CAUSAL_ESCALATION", passed, evidence)


def _rule_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    rule = _contract(sc).get("anomaly_rule")
    known = set(_scene_ids(manifest)) | set(_beat_ids(manifest))
    required = ("rule", "violation", "cost", "rule_scene_id", "cost_scene_id")
    missing = [key for key in required if not isinstance(rule, Mapping) or not _text(rule.get(key))]
    passed = (
        not missing
        and str(rule.get("rule_scene_id")) in known
        and str(rule.get("cost_scene_id")) in known
        and str(rule.get("rule_scene_id")) != str(rule.get("cost_scene_id"))
    )
    evidence = [
        "the supernatural or investigative mechanism has a stated rule, violation and price",
        f"rule_scene_id={rule.get('rule_scene_id') if isinstance(rule, Mapping) else None}",
        f"cost_scene_id={rule.get('cost_scene_id') if isinstance(rule, Mapping) else None}",
    ]
    if not passed:
        evidence.append("rule and cost must be dramatized in different known scenes")
    return _gate("E4", "ANOMALY_RULE_AND_COST", passed, evidence)


def _emotion_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    turns = _contract(sc).get("emotional_turns")
    known = set(_scene_ids(manifest)) | set(_beat_ids(manifest))
    failures: list[str] = []
    pairs: set[tuple[str, str]] = set()
    if not isinstance(turns, list) or len(turns) < 3:
        failures.append("at least three emotional turns are required")
        turn_items: list[Any] = []
    else:
        turn_items = turns
        for index, item in enumerate(turns, start=1):
            if not isinstance(item, Mapping):
                failures.append(f"turn {index} is not an object")
                continue
            for key in ("scene_id", "from", "to", "cause"):
                if not _text(item.get(key)):
                    failures.append(f"turn {index} missing {key}")
            if _text(item.get("scene_id")) and str(item.get("scene_id")) not in known:
                failures.append(f"turn {index} references an unknown scene")
            if _text(item.get("from")) and _text(item.get("to")):
                pair = (str(item["from"]).strip().lower(), str(item["to"]).strip().lower())
                if pair[0] == pair[1]:
                    failures.append(f"turn {index} does not change emotional state")
                pairs.add(pair)
    if len(pairs) < 3:
        failures.append("the emotional arc needs three distinct state changes")
    passed = not failures
    evidence = [
        f"emotional turns={len(turn_items)}",
        f"distinct emotional transitions={len(pairs)}",
    ]
    evidence.extend(failures[:5])
    return _gate("E5", "EMOTIONAL_TURNS", passed, evidence)


def _payoff_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    payoff = _contract(sc).get("payoff")
    known = set(_scene_ids(manifest)) | set(_beat_ids(manifest))
    story_ids = _beat_ids(manifest) or _scene_ids(manifest)
    required = (
        "early_clue_scene_ids",
        "final_scene_id",
        "payoff_type",
        "final_consequence",
        "emotional_aftertaste",
    )
    missing = [key for key in required if not isinstance(payoff, Mapping) or not payoff.get(key)]
    clues = payoff.get("early_clue_scene_ids") if isinstance(payoff, Mapping) else None
    final_id = payoff.get("final_scene_id") if isinstance(payoff, Mapping) else None
    passed = (
        not missing
        and _valid_ids(clues, known)
        and len(clues) >= 2
        and final_id in known
        and (not story_ids or final_id == story_ids[-1])
        and payoff.get("payoff_type") in PAYOFF_TYPES
        and payoff.get("recontextualizes_opening") is True
        and payoff.get("central_question_resolved") is True
    )
    evidence = [
        f"early clues={clues}",
        f"payoff type={payoff.get('payoff_type') if isinstance(payoff, Mapping) else None}",
        "the ending recontextualizes the opening and resolves the central question",
    ]
    if not passed:
        evidence.append("requires two planted clues, an earned consequence, recontextualization and resolution")
    return _gate("E6", "PAYOFF_RECONTEXTUALIZATION", passed, evidence)


def _visual_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    visual = _contract(sc).get("visual_dramatization")
    known = set(_scene_ids(manifest))
    if not isinstance(visual, list):
        return _gate("E7", "VISUAL_DRAMATIZATION", False, ["visual_dramatization must cover every scene"])
    by_id = {item.get("scene_id"): item for item in visual if isinstance(item, Mapping)}
    failures: list[str] = []
    for scene_id in known:
        item = by_id.get(scene_id)
        if not isinstance(item, Mapping):
            failures.append(f"{scene_id} has no dramatic visual plan")
            continue
        for key in ("human_action", "visual_evidence", "subjective_stakes"):
            if not _text(item.get(key)):
                failures.append(f"{scene_id} missing {key}")
        if item.get("not_just_atmosphere") is not True:
            failures.append(f"{scene_id} is atmosphere-only")
    extra = sorted(set(by_id) - known)
    if extra:
        failures.append(f"unknown visual scene ids: {', '.join(extra)}")
    passed = bool(known) and not failures and len(by_id) == len(known)
    evidence = [
        f"dramatic visual coverage={len(by_id)}/{len(known)}",
        "every scene has an action, evidence and subjective stake",
    ]
    evidence.extend(failures[:6])
    return _gate("E7", "VISUAL_DRAMATIZATION", passed, evidence)


def _density_gate(manifest: Mapping[str, Any], sc: Mapping[str, Any]) -> dict[str, Any]:
    density = _contract(sc).get("density")
    if not isinstance(density, Mapping):
        return _gate("E8", "NARRATIVE_DENSITY", False, ["density contract is missing"])
    meaningful = density.get("meaningful_beat_count")
    shots = density.get("visual_shot_count")
    padding = density.get("padding_seconds")
    repeated = density.get("repeated_visual_count")
    duration = density.get("story_seconds")
    micro = density.get("micro_beat_count")
    passed = (
        isinstance(meaningful, int)
        and 8 <= meaningful <= 14
        and isinstance(shots, int)
        and 12 <= shots <= 24
        and _number(padding)
        and float(padding) <= 1.0
        and repeated == 0
        and _number(duration)
        and 60 <= float(duration) <= 80
        and isinstance(micro, int)
        and micro <= 6
    )
    evidence = [
        f"meaningful_beats={meaningful}, visual_shots={shots}, micro_beats={micro}",
        f"duration={duration}s, padding={padding}s, repeated_visuals={repeated}",
        "short visual changes are subordinate to meaningful dramatic beats",
    ]
    if not passed:
        evidence.append("use 8–14 meaningful beats, 12–24 visual shots, <=1s padding and <=6 micro-beats")
    return _gate("E8", "NARRATIVE_DENSITY", passed, evidence)


def _originality_gate(sc: Mapping[str, Any]) -> dict[str, Any]:
    originality = _contract(sc).get("originality")
    required = ("core_mechanism", "familiar_trope", "distinctive_inversion", "comparison_set", "similarity_score")
    missing = [key for key in required if not isinstance(originality, Mapping) or not originality.get(key)]
    comparisons = originality.get("comparison_set") if isinstance(originality, Mapping) else None
    score = originality.get("similarity_score") if isinstance(originality, Mapping) else None
    passed = (
        not missing
        and isinstance(comparisons, list)
        and len(comparisons) >= 3
        and all(_text(value) for value in comparisons)
        and _number(score)
        and 0 <= float(score) <= 0.55
        and str(originality.get("familiar_trope")).strip().lower()
        != str(originality.get("distinctive_inversion")).strip().lower()
    )
    evidence = [
        f"similarity_score={score}",
        f"comparison_set_size={len(comparisons) if isinstance(comparisons, list) else 0}",
        "the story names its familiar trope and its specific inversion",
    ]
    if not passed:
        evidence.append("a distinctive mechanism must be documented, compared and kept below 0.55 similarity")
    return _gate("E9", "ORIGINAL_MECHANISM", passed, evidence)


def _narration_gate(sc: Mapping[str, Any]) -> dict[str, Any]:
    narration = _contract(sc).get("narration")
    required = (
        "naturalness_status",
        "generic_line_count",
        "orphan_line_count",
        "causal_link_count",
        "action_consequence_ratio",
        "reviewed_sentence_count",
        "line_evidence",
    )
    missing = [key for key in required if not isinstance(narration, Mapping) or narration.get(key) is None]
    ratio = narration.get("action_consequence_ratio") if isinstance(narration, Mapping) else None
    evidence_lines = narration.get("line_evidence") if isinstance(narration, Mapping) else None
    passed = (
        not missing
        and narration.get("naturalness_status") == "PASS"
        and narration.get("generic_line_count") == 0
        and narration.get("orphan_line_count") == 0
        and isinstance(narration.get("causal_link_count"), int)
        and narration.get("causal_link_count") >= 3
        and _number(ratio)
        and float(ratio) >= 0.70
        and isinstance(narration.get("reviewed_sentence_count"), int)
        and narration.get("reviewed_sentence_count") >= 8
        and isinstance(evidence_lines, list)
        and len(evidence_lines) >= 3
        and all(_text(line) for line in evidence_lines)
    )
    evidence = [
        f"naturalness={narration.get('naturalness_status') if isinstance(narration, Mapping) else None}",
        f"generic_lines={narration.get('generic_line_count') if isinstance(narration, Mapping) else None}",
        f"action→consequence ratio={ratio}",
        "narration lines were reviewed for action, consequence and human stakes",
    ]
    if not passed:
        evidence.append("generic/orphan narration is forbidden; causal language and line-level evidence are required")
    return _gate("E10", "NARRATION_DRAMATIZATION", passed, evidence)


def audit_editorial_story(manifest: Mapping[str, Any], story_creation: Mapping[str, Any]) -> dict[str, Any]:
    """Audit the explicit senior-editorial contract for one story."""
    contract = _contract(story_creation)
    gates = [
        _contract_gate(story_creation),
        _agency_gate(manifest, story_creation),
        _wound_gate(manifest, story_creation),
        _causal_gate(manifest, story_creation),
        _rule_gate(manifest, story_creation),
        _emotion_gate(manifest, story_creation),
        _payoff_gate(manifest, story_creation),
        _visual_gate(manifest, story_creation),
        _density_gate(manifest, story_creation),
        _originality_gate(story_creation),
        _narration_gate(story_creation),
    ]
    blocked = [gate["code"] for gate in gates if gate["status"] != "PASS"]
    return {
        "schema_version": "7.4",
        "status": "EDITORIAL_STORY_PASS" if not blocked else "EDITORIAL_STORY_BLOCKED",
        "contract_present": bool(contract),
        "contract_source": "explicit" if contract else "missing",
        "gates": gates,
        "blocked_gates": blocked,
        "reviewed_dimensions": [
            "protagonist_agency",
            "wound_dramatization",
            "causal_escalation",
            "anomaly_rule_and_cost",
            "emotional_turns",
            "payoff_recontextualization",
            "visual_dramatization",
            "narrative_density",
            "original_mechanism",
            "narration_dramatization",
        ],
    }
