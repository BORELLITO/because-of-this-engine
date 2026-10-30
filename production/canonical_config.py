#!/usr/bin/env python3
"""V7.1 canonical Piper TTS production profile for Because Of This.

This module is the only active configuration authority.  The former Gemini
profile is retained only in Git history/rollback documentation and is not
accepted for active production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

CANONICAL_PROFILE_ID = "because-of-this-v7-piper-tts-2026-10"
CANONICAL_ENGINE_VERSION = "7.1"
CANONICAL_SCHEMA_ID = "because-of-this://schemas/production-record/3.0.0"

CANONICAL_PROFILE: dict[str, Any] = {
    "fps": 60,
    "render": {
        "width": 1080,
        "height": 1920,
        "fps": 60,
        "duration_min_seconds": 60,
        "duration_max_seconds": 75,
    },
    "voice": {
        "provider": "piper_tts_local",
        "language": "en-US",
        "language_code": "en-US",
        "voice_name": "en_US-ryan-high",
        "voice": "en_US-ryan-high",
        "model_or_voice_type": "piper_neural_high",
        "ssml_gender": "MALE",
        "sample_rate_hz": 24000,
        "encoding": "LINEAR16",
        "speaking_rate": 0.68,
        "pitch": 0.0,
        "volume_gain_db": 0.0,
        "style": (
            "Grave American English narration. Controlled cinematic suspense, "
            "clear diction, restrained intensity, intimate consequence, never theatrical."
        ),
    },
    "brand": {
        "watermark_enabled": False,
        "watermark_text": "|B",
        "accent_color": "#E3262E",
        "logo_enabled": True,
        "logo_path": "brand/because-of-this-logo.png",
        "logo_width": 540,
        "logo_opacity": 0.82,
        "logo_margin": 54,
        "logo_top": 72,
        "logo_anchor": "center_top",
    },
    "music": {
        "volume": 0.12,
        "complete_track_reuse": "forbidden",
        "sidechain_enabled": True,
    },
    "captions": {
        "alignment_mode": "audio_final_forced_alignment",
        "alignment_source": "vosk_word_timestamps",
        "word_level_available": True,
        "max_lines": 2,
        "max_line_chars": 42,
        "target_cps": 20,
        "max_cps": 28,
        "end_tolerance_seconds": 0.1,
        "word_highlight_enabled": True,
        "word_highlight_mode": "timestamp_color_transform",
        "active_word_color": "#FF7777",
        "word_highlight_tolerance_ms": 35,
        "style": {
            "font_name": "Arial",
            "font_size": 48,
            "primary_color": "&H00FFFFFF&",
            "secondary_color": "&H00FFFFFF&",
            "outline_color": "&H00000000&",
            "back_color": "&H80000000&",
            "bold": 1,
            "italic": 0,
            "underline": 0,
            "strike_out": 0,
            "scale_x": 100,
            "scale_y": 100,
            "spacing": 0,
            "angle": 0,
            "border_style": 1,
            "outline": 3,
            "shadow": 1,
            "alignment": 2,
            "margin_l": 100,
            "margin_r": 100,
            "margin_v": 320,
            "encoding": 1,
        },
    },
    "color_grade": {
        "enabled": True,
        "preset": "investigative_noir_suspense",
        "brightness": -0.03,
        "contrast": 1.08,
        "saturation": 0.9,
        "gamma": 0.96,
        "vignette": True,
        "cinematic_suspense": {
            "enabled": True,
            "cool_shadows": 0.025,
            "warm_highlights": 0.01,
        },
    },
    "loop": {
        "enabled": True,
        "title": "BECAUSE OF THIS",
        "transition": "continuity_fade",
        "logo_source": "brand_logo_transparent",
        "logo_width": 820,
        "logo_anchor": "center_center",
        "outro_seconds": 1.2,
        "tail_fade_seconds": 0.55,
        "card_fade_in_seconds": 0.24,
        "card_fade_out_seconds": 0.36,
        "audio_fade_seconds": 0.6,
        "restart_safe": True,
    },
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


CANONICAL_PROFILE_FINGERPRINT = hashlib.sha256(_canonical_json(CANONICAL_PROFILE)).hexdigest()


def caption_ass_style_line(name: str = "Default") -> str:
    style = CANONICAL_PROFILE["captions"]["style"]
    fields = (
        name, style["font_name"], style["font_size"], style["primary_color"],
        style["secondary_color"], style["outline_color"], style["back_color"],
        style["bold"], style["italic"], style["underline"], style["strike_out"],
        style["scale_x"], style["scale_y"], style["spacing"], style["angle"],
        style["border_style"], style["outline"], style["shadow"], style["alignment"],
        style["margin_l"], style["margin_r"], style["margin_v"], style["encoding"],
    )
    return "Style: " + ",".join(str(value) for value in fields)


class CanonicalConfigError(ValueError):
    pass


def _differences(expected: Any, actual: Any, path: str = "") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        result: list[str] = []
        for key, value in expected.items():
            child = f"{path}.{key}" if path else key
            if key not in actual:
                result.append(f"{child}=<missing>")
            else:
                result.extend(_differences(value, actual[key], child))
        return result
    return [] if expected == actual else [f"{path}: expected {expected!r}, got {actual!r}"]


def canonical_settings(manifest: dict[str, Any]) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    for key in ("fps", "voice", "brand", "music", "captions", "color_grade", "loop", "render"):
        value = manifest.get(key)
        settings[key] = value if isinstance(value, (dict, int, float, str, bool)) else None
    return settings


def validate_canonical_manifest(manifest: dict[str, Any], *, source_label: str = "manifest") -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise CanonicalConfigError(f"{source_label} must be a JSON object.")

    # Archived V6 records remain readable for audit and rollback evidence, but
    # cannot enter the V7 production path.
    if manifest.get("lifecycle_status") == "ARCHIVED_HISTORICAL" and manifest.get("master_prompt_version") == "6.0":
        return {"status": "LEGACY_ARCHIVED_AUDIT_PASS", "profile_id": manifest.get("engine_profile", "legacy-v6")}

    if manifest.get("engine_profile") != CANONICAL_PROFILE_ID:
        raise CanonicalConfigError(f"{source_label} must declare engine_profile={CANONICAL_PROFILE_ID!r}.")
    if manifest.get("engine_profile_fingerprint") != CANONICAL_PROFILE_FINGERPRINT:
        raise CanonicalConfigError(f"{source_label} has a non-canonical profile fingerprint.")
    if manifest.get("master_prompt_version") != "7.1":
        raise CanonicalConfigError(f"{source_label} must declare master_prompt_version='7.1'.")
    if manifest.get("production_schema") != CANONICAL_SCHEMA_ID:
        raise CanonicalConfigError(f"{source_label} must declare production_schema={CANONICAL_SCHEMA_ID!r}.")

    differences = _differences(CANONICAL_PROFILE, canonical_settings(manifest))
    if differences:
        preview = "; ".join(differences[:8])
        suffix = f" (+{len(differences) - 8} more)" if len(differences) > 8 else ""
        raise CanonicalConfigError(f"{source_label} deviates from the V7.1 profile: {preview}{suffix}")
    return {
        "status": "CANONICAL_CONFIG_V7_PASS",
        "profile_id": CANONICAL_PROFILE_ID,
        "engine_version": CANONICAL_ENGINE_VERSION,
        "schema_id": CANONICAL_SCHEMA_ID,
        "profile_fingerprint": CANONICAL_PROFILE_FINGERPRINT,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = json.loads(args.manifest.read_text(encoding="utf-8"))
        print(json.dumps(validate_canonical_manifest(value, source_label=str(args.manifest)), ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, CanonicalConfigError) as exc:
        print(f"CANONICAL CONFIG BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
