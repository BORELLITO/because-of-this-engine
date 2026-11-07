"""Fail-closed PACKAGE_GATE_PRE for Because Of This V2.1."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

ALLOWED_PILLARS = {"invisible_natural_dangers","human_or_system_failure","survival_against_impossible_conditions"}
REQUIRED_FIELDS = ("editorial_mode","pillar","series_id","incident_id","central_question","audience_promise","impossible_event","human_anchor","causal_hinge","causal_chain","proof_level","proof_assets","visual_truth_classes","escalation_beats","irreversible_choice","payoff","title_candidates","opening_frame","opening_sentence","package_variants","next_video_bridge","source_ledger_id","rights_ledger_id","reuse_scope","story_score","package_status","human_editor_status","thumbnail_concept_id","thumbnail_manifest_id","thumbnail_status","platform_thumbnail_mode")
QUESTION_FIELDS = ("what_happened","why_it_happened","who_was_affected","what_changed_everything","why_it_seems_impossible","proof_or_source_note","how_danger_grows","irreversible_consequence","visual_representation_by_stage","first_frame_promise")
TRUTH_CLASSES = {"DOCUMENTARY_EVIDENCE","ARCHIVAL_MATERIAL","STOCK_REPRESENTATION","RECONSTRUCTION","GENERATED_VISUAL","MAP_OR_DIAGRAM","ABSTRACT_ATMOSPHERE"}
THUMBNAIL_CONCEPT_STATUSES = {"CONCEPT_READY","PENDING_HUMAN_APPROVAL","THUMBNAIL_QA","APPROVED"}
PACKAGE_STATUSES = {"DRAFT","PACKAGE_PENDING","PENDING_HUMAN_APPROVAL","APPROVED"}

def _present(value: Any) -> bool:
    if isinstance(value, str): return bool(value.strip())
    if isinstance(value, (list, tuple, dict)): return bool(value)
    return value is not None

def _text(value: Any) -> bool: return isinstance(value, str) and bool(value.strip())
def _list(value: Any, minimum: int = 1) -> bool: return isinstance(value, list) and len(value) >= minimum

def _score(record: Mapping[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    checks = [
        ("specific_hook", _text(record.get("opening_sentence")) and _text(record.get("opening_frame"))),
        ("understandable_danger", _text(record.get("impossible_event")) and _text(record.get("central_question"))),
        ("human_anchor", _text(record.get("human_anchor"))),
        ("clear_causality", _list(record.get("causal_chain"), 2) and _text(record.get("causal_hinge"))),
        ("proof_or_documentation", _list(record.get("proof_assets"), 2) and _text(record.get("proof_level"))),
        ("escalation", _list(record.get("escalation_beats"), 2)),
        ("visuality", _list(record.get("visual_truth_classes")) and _list(record.get("visual_representation_by_stage"))),
        ("payoff", _text(record.get("payoff")) and _text(record.get("irreversible_choice"))),
        ("originality", _list(record.get("title_candidates"), 3) and _list(record.get("package_variants"), 1)),
        ("american_audience_clarity", _text(record.get("audience_promise")) and _text((record.get("question_answers") or {}).get("first_frame_promise"))),
    ]
    details = [{"dimension": name, "score": int(passed)} for name, passed in checks]
    return sum(item["score"] for item in details), details

def evaluate_package_gate(record: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    failures.extend(f"missing:{field}" for field in REQUIRED_FIELDS if not _present(record.get(field)))
    if record.get("editorial_mode") != "factual_documentary": failures.append("editorial_mode must be factual_documentary")
    if record.get("pillar") not in ALLOWED_PILLARS: failures.append("pillar is outside the first-pilot factual pillars")
    if record.get("reuse_scope") != "global": failures.append("reuse_scope must be global")
    if record.get("package_status") not in PACKAGE_STATUSES: failures.append("package_status is missing or invalid")
    if record.get("thumbnail_status") not in THUMBNAIL_CONCEPT_STATUSES: failures.append("thumbnail concept must exist before media/TTS work")
    truth_classes = record.get("visual_truth_classes")
    if isinstance(truth_classes, list):
        invalid = sorted(set(truth_classes) - TRUTH_CLASSES)
        if invalid: failures.append("invalid visual_truth_classes:" + ",".join(invalid))
    questions = record.get("question_answers")
    if not isinstance(questions, Mapping):
        failures.append("question_answers is required")
    else:
        failures.extend(f"missing:question_answers.{field}" for field in QUESTION_FIELDS if not _present(questions.get(field)))
    score, dimensions = _score(record)
    if record.get("story_score") is not None and record.get("story_score") != score:
        failures.append(f"story_score mismatch:declared={record.get('story_score')}:computed={score}")
    if score < 8: failures.append(f"story_score {score}/10 is below the minimum 8/10")
    if score == 8: warnings.append("score 8/10 requires explicit human editorial review")
    if record.get("factuality_status") in {"BLOCKED","REJECTED"}: failures.append("factuality_status is blocked")
    if record.get("safety_status") in {"BLOCKED","REJECTED"}: failures.append("safety_status is blocked")
    deferred = [key for key in ("source_ledger_status","rights_ledger_status","reuse_status") if record.get(key) not in {"READY","PASS","APPROVED"}]
    warnings.extend(f"{key} remains deferred to its downstream gate" for key in deferred)
    return {"gate":"PACKAGE_GATE_PRE","status":"PACKAGE_GATE_PASS" if not failures else "PACKAGE_GATE_BLOCKED","production_enablement":False,"score":score,"score_max":10,"score_scope":"STRUCTURAL_COMPLETENESS_ONLY","editorial_quality_proven":False,"score_dimensions":dimensions,"failures":failures,"warnings":warnings,"hard_gates_deferred":deferred,"next_state":"FACT_CHECK_PENDING" if not failures else "BLOCKED"}
