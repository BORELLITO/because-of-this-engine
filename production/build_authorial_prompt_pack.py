#!/usr/bin/env python3
"""Build reusable authorial image prompts for Because of This."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_STYLE = ROOT / "authorial-style-because-of-this-v1.json"


class ManifestError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Could not read JSON manifest: {path}") from exc
    if not isinstance(value, dict):
        raise ManifestError(f"Manifest must be an object: {path}")
    return value


def _required(scene: dict[str, Any], key: str) -> str:
    value = scene.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"Scene {scene.get('scene_id', '?')} is missing '{key}'.")
    return value.strip()


def build_scene_prompt(style: dict[str, Any], scene: dict[str, Any]) -> dict[str, str]:
    scene_id = _required(scene, "scene_id")
    beat = _required(scene, "beat")
    subject = _required(scene, "subject")
    action = _required(scene, "action")
    setting = _required(scene, "setting")
    mood = _required(scene, "mood")
    camera = str(scene.get("camera", "clear editorial framing")).strip()

    palette = ", ".join(style["palette"]["base"] + style["palette"]["accent"])
    character = "; ".join(style["visual_character"])
    prompt = (
        f"Original vertical 9:16 image for the Because of This channel. "
        f"Premium cinematic editorial cartoon with realistic proportions; {character}. "
        f"Visual beat: {beat}. Primary subject: {subject}. "
        f"Action or physical relationship: {action}. Setting: {setting}. "
        f"Mood: {mood}. Camera: {camera}. "
        f"Palette: {palette}. "
        f"Lighting: {style['lighting']['default']}. "
        f"Composition: {style['composition']['subject_rule']}; {style['composition']['depth']}; "
        f"leave clean negative space for captions. "
        f"Use subtle painted texture and atmospheric depth. "
        "Make the scene legible without captions. No text, labels, logos or watermarks."
    )
    return {
        "scene_id": scene_id,
        "prompt": prompt,
        "negative_prompt": style["negative_prompt"],
    }


def build_pack(manifest: dict[str, Any], style: dict[str, Any]) -> dict[str, Any]:
    video_id = manifest.get("video_id")
    topic = manifest.get("topic")
    scenes = manifest.get("scenes")
    if not isinstance(video_id, str) or not video_id.strip():
        raise ManifestError("Manifest requires a non-empty video_id.")
    if not isinstance(topic, str) or not topic.strip():
        raise ManifestError("Manifest requires a non-empty topic.")
    if not isinstance(scenes, list) or not scenes:
        raise ManifestError("Manifest requires at least one scene.")

    prompts = [build_scene_prompt(style, scene) for scene in scenes]
    return {
        "schema_version": "1.0",
        "video_id": video_id.strip(),
        "topic": topic.strip(),
        "visual_style_id": style["style_id"],
        "provider_mode": "authorial-generative",
        "human_review_required": True,
        "caption_layer": "external-edit-layer",
        "reference_policy": style["render_policy"]["reference_policy"],
        "scenes": prompts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a cartoon-cinematic prompt pack.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = _read_json(args.manifest)
    style = _read_json(args.style)
    if style.get("style_id") != "because-of-this-cinematic-cartoon-v1":
        raise ManifestError("Unexpected visual style identifier.")
    result = build_pack(manifest, style)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
