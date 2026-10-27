#!/usr/bin/env python3
"""Canonical, fail-closed profile for the Because Of This video engine.

The profile is deliberately centralized.  Episode manifests may contain
episode-specific editorial data, but the production identity, timing, voice,
caption, branding and outro settings must match this profile exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

CANONICAL_PROFILE_ID = "because-of-this-v2-locked-2026-10"
CANONICAL_ENGINE_VERSION = "2.0"

CANONICAL_PROFILE: dict[str, Any] = {
    "fps": 25,
    "voice": {
        "provider": "gemini",
        "model": "gemini-3.8-flash-tts",
        "voice": "Charon",
        "language": "en-US",
        "style": (
            "Clear American English, crisp diction, moderate pace, restrained suspense. "
            "Pronounce numbers as spoken English words with clear word boundaries; preserve every word exactly."
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
    },
    "music": {
        "volume": 0.12,
    },
    "captions": {
        "alignment_mode": "forced_alignment",
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
        "outro_seconds": 1.2,
        "tail_fade_seconds": 0.55,
        "card_fade_in_seconds": 0.24,
        "card_fade_out_seconds": 0.36,
        "audio_fade_seconds": 0.6,
        "restart_safe": True,
    },
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


CANONICAL_PROFILE_FINGERPRINT = hashlib.sha256(_canonical_json(CANONICAL_PROFILE)).hexdigest()


class CanonicalConfigError(ValueError):
    """Raised when a manifest attempts to bypass the locked engine profile."""


def canonical_settings(manifest: dict[str, Any]) -> dict[str, Any]:
    """Extract only settings controlled by the locked production profile."""
    voice = manifest.get("voice") if isinstance(manifest.get("voice"), dict) else {}
    brand = manifest.get("brand") if isinstance(manifest.get("brand"), dict) else {}
    music = manifest.get("music") if isinstance(manifest.get("music"), dict) else {}
    captions = manifest.get("captions") if isinstance(manifest.get("captions"), dict) else {}
    grade = manifest.get("color_grade") if isinstance(manifest.get("color_grade"), dict) else {}
    suspense = grade.get("cinematic_suspense") if isinstance(grade.get("cinematic_suspense"), dict) else {}
    loop = manifest.get("loop") if isinstance(manifest.get("loop"), dict) else {}

    return {
        "fps": manifest.get("fps"),
        "voice": {key: voice.get(key) for key in CANONICAL_PROFILE["voice"]},
        "brand": {key: brand.get(key) for key in CANONICAL_PROFILE["brand"]},
        "music": {"volume": music.get("volume")},
        "captions": {key: captions.get(key) for key in CANONICAL_PROFILE["captions"]},
        "color_grade": {
            key: grade.get(key)
            for key in ("enabled", "preset", "brightness", "contrast", "saturation", "gamma", "vignette")
        }
        | {"cinematic_suspense": {key: suspense.get(key) for key in CANONICAL_PROFILE["color_grade"]["cinematic_suspense"]}},
        "loop": {key: loop.get(key) for key in CANONICAL_PROFILE["loop"]},
    }


def _differences(expected: Any, actual: Any, path: str = "") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        differences: list[str] = []
        for key in expected:
            child = f"{path}.{key}" if path else key
            if key not in actual:
                differences.append(f"{child}=<missing>")
            else:
                differences.extend(_differences(expected[key], actual[key], child))
        return differences
    if expected != actual:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []


def validate_canonical_manifest(
    manifest: dict[str, Any],
    *,
    source_label: str = "manifest",
) -> dict[str, Any]:
    """Validate a manifest against the single canonical engine profile."""
    if not isinstance(manifest, dict):
        raise CanonicalConfigError(f"{source_label} must be a JSON object.")

    profile = manifest.get("engine_profile")
    if profile != CANONICAL_PROFILE_ID:
        raise CanonicalConfigError(
            f"{source_label} must declare engine_profile={CANONICAL_PROFILE_ID!r}; "
            f"got {profile!r}. Legacy or missing profiles are blocked."
        )
    declared_fingerprint = manifest.get("engine_profile_fingerprint")
    if declared_fingerprint != CANONICAL_PROFILE_FINGERPRINT:
        raise CanonicalConfigError(
            f"{source_label} must declare the exact canonical profile fingerprint; "
            f"got {declared_fingerprint!r}."
        )

    differences = _differences(CANONICAL_PROFILE, canonical_settings(manifest))
    if differences:
        preview = "; ".join(differences[:8])
        suffix = f" (+{len(differences) - 8} more)" if len(differences) > 8 else ""
        raise CanonicalConfigError(f"{source_label} deviates from the locked profile: {preview}{suffix}")

    return {
        "status": "CANONICAL_CONFIG_PASS",
        "profile_id": CANONICAL_PROFILE_ID,
        "engine_version": CANONICAL_ENGINE_VERSION,
        "profile_fingerprint": CANONICAL_PROFILE_FINGERPRINT,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest_path = args.manifest.resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report = validate_canonical_manifest(manifest, source_label=str(manifest_path))
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, CanonicalConfigError) as exc:
        print(f"CANONICAL CONFIG BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
