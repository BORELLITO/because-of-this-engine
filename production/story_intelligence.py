#!/usr/bin/env python3
"""Story-first integrity and narration coverage gates for engine v2."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


class StoryIntegrityError(ValueError):
    """Raised when the story graph or narration coverage is incoherent."""


_TOKEN_RE = re.compile(r"[a-z0-9]+(?::[a-z0-9]+)?(?:'[a-z0-9]+)?", re.IGNORECASE)


def normalize_tokens(value: Any) -> list[str]:
    text = (
        str(value or "")
        .lower()
        .replace("’", "'")
        .replace("—", " ")
        .replace("–", " ")
    )
    return _TOKEN_RE.findall(text)


def _required_text(record: dict[str, Any], key: str, label: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise StoryIntegrityError(f"{label} requires {key}.")
    return value.strip()


def _find_subsequence(haystack: list[str], needle: list[str], start: int) -> tuple[int, int] | None:
    if not needle:
        return None
    upper = len(haystack) - len(needle) + 1
    for index in range(max(0, start), upper):
        if haystack[index:index + len(needle)] == needle:
            return index, index + len(needle)
    return None


def validate_story_graph(manifest: dict[str, Any]) -> dict[str, Any]:
    graph = manifest.get("story_graph")
    if not isinstance(graph, dict):
        raise StoryIntegrityError("Manifest requires story_graph for story-first production.")

    version = _required_text(graph, "version", "story_graph")
    entities = graph.get("entities")
    beats = graph.get("beats")
    if not isinstance(entities, list) or not entities:
        raise StoryIntegrityError("story_graph.entities must be a non-empty list.")
    if not isinstance(beats, list) or not beats:
        raise StoryIntegrityError("story_graph.beats must be a non-empty list.")

    entity_ids: set[str] = set()
    for index, entity in enumerate(entities, start=1):
        if not isinstance(entity, dict):
            raise StoryIntegrityError(f"story_graph entity {index} must be an object.")
        entity_id = _required_text(entity, "entity_id", f"story_graph entity {index}")
        if entity_id in entity_ids:
            raise StoryIntegrityError(f"Duplicate story_graph entity_id: {entity_id}")
        entity_ids.add(entity_id)
        _required_text(entity, "canonical_name", f"story_graph entity {entity_id}")
        aliases = entity.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            raise StoryIntegrityError(f"story_graph entity {entity_id} requires aliases.")
        _required_text(entity, "continuity_mode", f"story_graph entity {entity_id}")

    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise StoryIntegrityError("Story graph cannot be validated without scenes.")
    scene_by_id = {str(scene.get("scene_id")): scene for scene in scenes if isinstance(scene, dict)}
    if len(scene_by_id) != len(scenes):
        raise StoryIntegrityError("Each scene must have a unique scene_id before story graph validation.")

    beat_scene_ids: list[str] = []
    previous_state: str | None = None
    beat_report: list[dict[str, Any]] = []
    for index, beat in enumerate(beats, start=1):
        if not isinstance(beat, dict):
            raise StoryIntegrityError(f"story_graph beat {index} must be an object.")
        scene_id = _required_text(beat, "scene_id", f"story_graph beat {index}")
        if scene_id in beat_scene_ids:
            raise StoryIntegrityError(f"Duplicate story_graph beat for scene: {scene_id}")
        if scene_id not in scene_by_id:
            raise StoryIntegrityError(f"story_graph beat {scene_id} has no matching scene.")
        beat_scene_ids.append(scene_id)
        for key in (
            "event",
            "state_before",
            "state_after",
            "causal_role",
            "emotion",
            "visual_motif",
        ):
            _required_text(beat, key, f"story_graph beat {scene_id}")
        refs = beat.get("entities")
        if not isinstance(refs, list) or not refs:
            raise StoryIntegrityError(f"story_graph beat {scene_id} requires entity references.")
        unknown = [str(item) for item in refs if str(item) not in entity_ids]
        if unknown:
            raise StoryIntegrityError(
                f"story_graph beat {scene_id} references unknown entities: {', '.join(unknown)}"
            )
        scene_excerpt = normalize_tokens(scene_by_id[scene_id].get("narration_excerpt"))
        beat_excerpt = beat.get("narration_excerpt")
        if beat_excerpt is not None and normalize_tokens(beat_excerpt) != scene_excerpt:
            raise StoryIntegrityError(
                f"story_graph beat {scene_id} narration_excerpt diverges from the scene contract."
            )
        state_before = str(beat["state_before"])
        if previous_state is not None and state_before != previous_state:
            if beat.get("continuity_bridge") is not True:
                raise StoryIntegrityError(
                    f"story_graph state discontinuity before {scene_id}: "
                    f"expected {previous_state!r}, got {state_before!r}."
                )
        previous_state = str(beat["state_after"])
        beat_report.append({
            "scene_id": scene_id,
            "event": beat["event"],
            "state_before": state_before,
            "state_after": beat["state_after"],
            "causal_role": beat["causal_role"],
            "emotion": beat["emotion"],
            "visual_motif": beat["visual_motif"],
            "entities": list(refs),
        })

    expected_scene_ids = [str(scene["scene_id"]) for scene in scenes]
    if beat_scene_ids != expected_scene_ids:
        raise StoryIntegrityError(
            "story_graph.beats must cover scenes in exact timeline order; "
            f"expected {expected_scene_ids}, got {beat_scene_ids}."
        )

    return {
        "status": "STORY_GRAPH_PASS",
        "version": version,
        "entity_count": len(entity_ids),
        "beat_count": len(beat_report),
        "beats": beat_report,
    }


def validate_sequence_continuity(
    manifest: dict[str, Any],
    story_graph_report: dict[str, Any],
) -> dict[str, Any]:
    beats = story_graph_report.get("beats") or []
    if not beats:
        raise StoryIntegrityError("Sequence continuity requires story graph beats.")
    entity_counts: dict[str, int] = {}
    adjacency: list[dict[str, Any]] = []
    for index, beat in enumerate(beats):
        current = set(str(item) for item in beat.get("entities", []))
        for entity_id in current:
            entity_counts[entity_id] = entity_counts.get(entity_id, 0) + 1
        if index:
            previous = set(str(item) for item in beats[index - 1].get("entities", []))
            shared = sorted(previous & current)
            adjacency.append({
                "from_scene": beats[index - 1]["scene_id"],
                "to_scene": beat["scene_id"],
                "shared_entities": shared,
                "linked_by_state": (
                    beats[index - 1].get("state_after") == beat.get("state_before")
                ),
                "status": "PASS" if shared or (
                    beats[index - 1].get("state_after") == beat.get("state_before")
                ) else "WEAK",
            })
    first_entities = set(str(item) for item in beats[0].get("entities", []))
    final_entities = set(str(item) for item in beats[-1].get("entities", []))
    final_recall = sorted(first_entities & final_entities)
    if not final_recall:
        raise StoryIntegrityError(
            "Final beat does not recall any opening story entity or motif."
        )
    recurring = sorted(entity_id for entity_id, count in entity_counts.items() if count >= 2)
    if not recurring:
        raise StoryIntegrityError("Story graph has no recurring entity/motif for continuity.")
    weak_links = [item for item in adjacency if item["status"] == "WEAK"]
    return {
        "status": "SEQUENCE_CONTINUITY_PASS",
        "scene_count": len(beats),
        "recurring_entities": recurring,
        "final_motif_recall": final_recall,
        "adjacency": adjacency,
        "weak_link_count": len(weak_links),
    }


def validate_narration_coverage(manifest: dict[str, Any], script_text: str) -> dict[str, Any]:
    script_tokens = normalize_tokens(script_text)
    if not script_tokens:
        raise StoryIntegrityError("Canonical script has no normalized tokens.")

    cursor = 0
    spans: list[dict[str, Any]] = []
    scenes = manifest.get("scenes") or []
    for scene in scenes:
        scene_id = _required_text(scene, "scene_id", "Scene")
        excerpt = _required_text(scene, "narration_excerpt", f"Scene {scene_id}")
        excerpt_tokens = normalize_tokens(excerpt)
        found = _find_subsequence(script_tokens, excerpt_tokens, cursor)
        if found is None:
            raise StoryIntegrityError(
                f"Scene {scene_id} narration_excerpt is missing, out of order, or duplicated "
                f"after script word {cursor}."
            )
        start, end = found
        if start != cursor:
            missing = " ".join(script_tokens[cursor:start])
            raise StoryIntegrityError(
                f"Narration coverage gap before {scene_id}: {missing!r}."
            )
        spans.append({
            "scene_id": scene_id,
            "word_start_index": start,
            "word_end_index": end,
            "word_count": end - start,
            "narration_excerpt": excerpt,
        })
        cursor = end

    if cursor != len(script_tokens):
        missing = " ".join(script_tokens[cursor:])
        raise StoryIntegrityError(f"Narration coverage gap after final scene: {missing!r}.")

    return {
        "status": "NARRATION_COVERAGE_PASS",
        "script_word_count": len(script_tokens),
        "covered_word_count": cursor,
        "scene_count": len(spans),
        "scenes": spans,
    }


def attach_audio_timestamps(report: dict[str, Any], alignment: dict[str, Any], script_text: str) -> dict[str, Any]:
    chunks = alignment.get("captions")
    if not isinstance(chunks, list) or not chunks:
        raise StoryIntegrityError("Alignment sidecar has no caption word timeline.")

    aligned: list[tuple[str, float, float]] = []
    for chunk in chunks:
        words = chunk.get("words") if isinstance(chunk, dict) else None
        if not isinstance(words, list):
            raise StoryIntegrityError("Alignment sidecar contains an invalid caption chunk.")
        for word in words:
            if not isinstance(word, dict):
                raise StoryIntegrityError("Alignment sidecar contains an invalid word record.")
            canonical = normalize_tokens(word.get("canonical"))
            if len(canonical) != 1:
                raise StoryIntegrityError(
                    "Alignment sidecar canonical words must map one-to-one for narration coverage."
                )
            start = word.get("start")
            end = word.get("end")
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end <= start:
                raise StoryIntegrityError("Alignment sidecar contains invalid word timestamps.")
            aligned.append((canonical[0], float(start), float(end)))

    script_tokens = normalize_tokens(script_text)
    aligned_tokens = [item[0] for item in aligned]
    if aligned_tokens != script_tokens:
        raise StoryIntegrityError(
            "Forced-alignment canonical words do not exactly cover the canonical script."
        )

    for scene in report["scenes"]:
        start = int(scene["word_start_index"])
        end = int(scene["word_end_index"])
        scene["audio_start"] = round(aligned[start][1], 3)
        scene["audio_end"] = round(aligned[end - 1][2], 3)
        scene["timing_source"] = "forced_alignment_sidecar"

    report["audio_duration_seconds"] = alignment.get("audio_duration_seconds")
    report["timing_status"] = "FORCED_ALIGNMENT_SCENE_TIMES_PASS"
    return report


def audit_manifest(manifest: dict[str, Any], script_text: str, alignment: dict[str, Any] | None = None) -> dict[str, Any]:
    story = validate_story_graph(manifest)
    sequence = validate_sequence_continuity(manifest, story)
    coverage = validate_narration_coverage(manifest, script_text)
    if alignment is not None:
        coverage = attach_audio_timestamps(coverage, alignment, script_text)
    return {
        "status": "STORY_INTELLIGENCE_PASS",
        "story_graph": story,
        "sequence_continuity": sequence,
        "narration_coverage": coverage,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--alignment", type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        base = args.manifest.resolve().parent
        script_path = (base / manifest["script"]["path"]).resolve()
        script_text = script_path.read_text(encoding="utf-8")
        alignment = None
        if args.alignment:
            alignment = json.loads(args.alignment.read_text(encoding="utf-8"))
        report = audit_manifest(manifest, script_text, alignment)
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.resolve().write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"STORY INTELLIGENCE BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
