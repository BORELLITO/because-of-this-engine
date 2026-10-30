#!/usr/bin/env python3
"""Cinematic Dread V1 — opt-in per-scene atmosphere direction.

Additive to the currently locked Charon/Gemini engine. No voice generation,
external API, unlicensed imagery, authored on-screen text or model replacement.
The human director must approve the appearance before activation in a final.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

PROFILE = "cinematic_dread_v1"
LEVELS = {
    1: {"name": "unease", "brightness": -0.026, "contrast": 1.09, "saturation": 0.87, "gamma": 0.98, "cool": 0.037, "grain": 2, "vignette": "PI/5.3", "music_gain": 0.84},
    2: {"name": "suspicion", "brightness": -0.032, "contrast": 1.12, "saturation": 0.83, "gamma": 0.98, "cool": 0.047, "grain": 3, "vignette": "PI/5.0", "music_gain": 0.92},
    3: {"name": "dread", "brightness": -0.043, "contrast": 1.16, "saturation": 0.78, "gamma": 0.98, "cool": 0.059, "grain": 4, "vignette": "PI/4.8", "music_gain": 1.04},
    4: {"name": "impact", "brightness": -0.052, "contrast": 1.19, "saturation": 0.74, "gamma": 0.99, "cool": 0.068, "grain": 4, "vignette": "PI/4.6", "music_gain": 1.12},
}
BEATS = {
    "hook": 1, "setup": 1, "normality": 1, "introduction": 1,
    "contradiction": 2, "suspicion": 2, "discovery": 2, "recognition": 2,
    "escalation": 3, "threat": 3, "decision": 3, "threshold": 3,
    "reveal": 4, "climax": 4, "twist": 4, "impact": 4,
    "consequence": 3, "aftermath": 2, "ending": 2, "outro": 2,
}
ALLOWED_SCENE_KEYS = {"intensity", "reason"}
ALLOWED_PLAN_KEYS = {"enabled", "profile", "director_review", "scene_overrides"}


class AtmosphereError(ValueError):
    pass


def _positive_finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise AtmosphereError(f"{label} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise AtmosphereError(f"{label} must be finite and positive")
    return number


def _level_override(value: Any, label: str) -> int:
    if type(value) is not int or value not in LEVELS:
        raise AtmosphereError(f"{label} must be an integer in 1..4")
    return value


def scene_level(scene: dict[str, Any], index: int, count: int, overrides: dict[str, Any]) -> tuple[int, str]:
    key = str(scene.get("scene_id") or "")
    if not key:
        raise AtmosphereError("Every atmosphere scene requires a scene_id")
    if key in overrides:
        override = overrides[key]
        if not isinstance(override, dict) or set(override) - ALLOWED_SCENE_KEYS or "intensity" not in override:
            raise AtmosphereError(f"{key}: scene override must have intensity and optional reason")
        level = _level_override(override["intensity"], f"{key}.intensity")
        reason = str(override.get("reason") or "").strip()
        if not reason:
            raise AtmosphereError(f"{key}: a scene override requires a narrative reason")
        return level, reason
    beat = str(scene.get("story_beat") or "").lower().strip().replace(" ", "_")
    for name, level in BEATS.items():
        if name in beat:
            return level, f"narrative beat: {beat}"
    # Story-led fallback. Never pretend to infer an emotion from clip pixels.
    phase = index / max(1, count - 1)
    return (1 if phase < 0.18 else 2 if phase < 0.5 else 3 if phase < 0.85 else 2), "temporal fallback; requires director review"


def plan(manifest: dict[str, Any]) -> dict[str, Any]:
    settings = manifest.get("atmosphere")
    if settings is None:
        return {"enabled": False, "profile": None, "scenes": []}
    if not isinstance(settings, dict) or set(settings) - ALLOWED_PLAN_KEYS:
        raise AtmosphereError("atmosphere contains unsupported keys")
    if settings.get("enabled") is not True:
        if settings.get("enabled") is not False:
            raise AtmosphereError("atmosphere.enabled must be a boolean")
        return {"enabled": False, "profile": None, "scenes": []}
    if settings.get("profile") != PROFILE:
        raise AtmosphereError(f"Only profile {PROFILE} is supported")
    if settings.get("director_review") not in {"PENDING", "APPROVED"}:
        raise AtmosphereError("atmosphere.director_review must be PENDING or APPROVED")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise AtmosphereError("Atmosphere requires nonempty manifest scenes")
    overrides = settings.get("scene_overrides", {})
    if not isinstance(overrides, dict):
        raise AtmosphereError("atmosphere.scene_overrides must be a map")
    ids = [s.get("scene_id") if isinstance(s, dict) else None for s in scenes]
    if len(set(ids)) != len(ids) or not all(isinstance(k, str) and k for k in ids):
        raise AtmosphereError("Atmosphere needs unique valid scene IDs")
    unknown = set(overrides) - set(ids)
    if unknown:
        raise AtmosphereError(f"Unknown atmosphere scene overrides: {sorted(unknown)}")
    resolved = []
    for i, scene in enumerate(scenes):
        level, reason = scene_level(scene, i, len(scenes), overrides)
        resolved.append({"scene_id": scene["scene_id"], "story_beat": scene.get("story_beat"),
                         "intensity": level, "mood": LEVELS[level]["name"], "reason": reason,
                         "palette": "cold teal/green shadows; existing light sources retained",
                         "visual_evidence_rule": "Never synthesize new objects, faces, fog, red lights, signs or editorial text"})
    return {"enabled": True, "profile": PROFILE, "director_review": settings["director_review"],
            "scenes": resolved, "music_strategy": "scene-sensitive original bed gain, under existing vocal sidechain",
            "source_clip_mutation": "color and texture only; no synthetic objects",
            "human_final_approval_required": True}


def grade_for_scene(base: dict[str, Any], scene: dict[str, Any], direction: dict[str, Any]) -> dict[str, Any]:
    if not direction.get("enabled"):
        return base
    item = next((x for x in direction["scenes"] if x["scene_id"] == scene.get("scene_id")), None)
    if item is None:
        raise AtmosphereError(f"Missing direction for scene {scene.get('scene_id')}")
    level = LEVELS[item["intensity"]]
    result = copy.deepcopy(base)
    if result.get("enabled") is not True:
        raise AtmosphereError("Dread grade cannot override a disabled canonical grade")
    for key in ("brightness", "contrast", "saturation", "gamma"):
        result[key] = level[key]
    result["vignette"] = True
    motion = dict(result.get("cinematic_suspense") or {})
    motion.update({"enabled": True, "cool_shadows": level["cool"],
                   "warm_highlights": 0.004, "motion_strength": 0.021,
                   "push_in": 0.034})
    result["cinematic_suspense"] = motion
    result["_dread_grain_strength"] = level["grain"]
    result["_dread_vignette_angle"] = level["vignette"]
    result["_dread_level"] = item["intensity"]
    return result


def timeline(direction: dict[str, Any], scenes: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    if not direction.get("enabled"):
        return []
    duration = _positive_finite(duration, "narration duration")
    by_id = {s["scene_id"]: s for s in direction["scenes"]}
    raw = [_positive_finite(s.get("duration"), "scene duration") for s in scenes]
    # The renderer reserves the following scene's transition from the current
    # scene's duration. Follow the SAME clock, not the untrimmed source sum.
    kept = []
    for index, seconds in enumerate(raw):
        overlap = 0.0
        if index < len(scenes) - 1:
            next_transition = scenes[index + 1].get("transition") or {}
            if not isinstance(next_transition, dict):
                raise AtmosphereError("Malformed scene transition")
            if str(next_transition.get("type", "crossfade")) != "hard_cut":
                raw_overlap = next_transition.get("duration", 0.25)
                if isinstance(raw_overlap, bool) or not isinstance(raw_overlap, (float, int)):
                    raise AtmosphereError("Invalid scene transition duration")
                overlap = max(float(raw_overlap), 1 / 60)
            if overlap >= seconds:
                raise AtmosphereError("Scene transition consumes the scene")
        kept.append(seconds - overlap)
    total = sum(kept)
    if total <= 0:
        raise AtmosphereError("Empty scene timeline")
    # Small final rescaling is bounded to the actual audio master duration.
    t = 0.0
    result = []
    for scene, seconds in zip(scenes, kept):
        end = min(duration, t + duration * (seconds / total))
        level = by_id[scene["scene_id"]]["intensity"]
        result.append({"scene_id": scene["scene_id"], "start": round(t, 3),
                       "end": round(end, 3), "intensity": level,
                       "music_gain": LEVELS[level]["music_gain"]})
        t = end
    result[-1]["end"] = round(duration, 3)
    return result


def music_filter(timing: list[dict[str, Any]]) -> str:
    if not timing:
        return ""
    # escaped commas matter inside ffmpeg filter_complex parsing. Frames are
    # evaluated over the licensed bed, before canonical voice ducking.
    expr = f"{timing[-1]['music_gain']:.3f}"
    for item in reversed(timing[:-1]):
        expr = f"if(lt(t\\,{item['end']:.3f})\\,{item['music_gain']:.3f}\\,{expr})"
    return "volume='" + expr + "':eval=frame"


def sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = plan(manifest)
        if not result["enabled"]:
            raise AtmosphereError("No opt-in cinematic atmosphere is enabled in the manifest")
        result["manifest_sha256"] = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        print(json.dumps({"status": "ATMOSPHERE_DIRECTION_PLANNED", "scenes": len(result["scenes"]),
                          "director_review": result["director_review"]}))
        return 0
    except (AtmosphereError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print("ATMOSPHERE_DIRECTION_BLOCKED: " + str(exc))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
