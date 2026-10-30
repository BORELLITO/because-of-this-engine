#!/usr/bin/env python3
"""V7.2 experimental release identity gates, no unconditional PASS values."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from production.asset_reuse_brain import audit as audit_sources
from production.audio_reuse_brain import audit as audit_music

def audit_release_identities(manifest_path: Path) -> dict[str, Any]:
    path = manifest_path.resolve()
    root = path.parents[2]
    asset_registry = root / "episodes/asset-memory-registry.json"
    audio_registry = root / "episodes/audio-memory-registry.json"
    if not asset_registry.is_file() or not audio_registry.is_file():
        raise ValueError("Source and audio history ledgers must exist")
    sources = audit_sources(path, root, registry_path=asset_registry)
    music = audit_music(path, root, registry_path=audio_registry)
    if sources.get("status") != "ASSET_REUSE_PASS":
        raise ValueError(f"Global source history rejected preview: {sources.get('reason')}")
    if music.get("status") != "PASS":
        raise ValueError(f"Global music history rejected preview: {music.get('errors')}")
    return {
        "asset_reuse_gate": sources["status"],
        "audio_reuse_gate": music["status"],
        "registry_asset_count_checked": sources.get("candidate_asset_count"),
        "history_scanned_episode_count": sources.get("scanned_episode_count"),
        "historical_music_checked": music.get("historical_music_included"),
        "status": "IDENTITY_REGISTRIES_CHECKED",
        "license_provenance_independently_verified": False,
        "pixel_content_independently_verified": False,
    }
