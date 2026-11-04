"""Read-only catalog coverage audit for all manifest snapshots and on-branch registry.

It reports scope honestly: it cannot infer unseen Drive assets, Git history,
pixel-level likeness or licensing truth. It never writes to production state.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from production.asset_reuse_brain import _all_manifests, source_asset_key


class InventoryAuditError(ValueError):
    pass


def inspect(root: Path) -> dict[str, Any]:
    root = root.resolve()
    ledger = root / "episodes" / "asset-memory-registry.json"
    if not ledger.is_file():
        raise InventoryAuditError("Historical asset registry missing")
    try:
        registry = json.loads(ledger.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise InventoryAuditError("Historical asset registry unreadable") from exc
    if registry.get("schema_version") != 1 or not isinstance(registry.get("assets"), list):
        raise InventoryAuditError("Historical asset registry schema invalid")
    registered = registry["assets"]
    record_keys = set()
    missing_registry_identity = 0
    missing_registry_visual_fingerprint = 0
    for item in registered:
        if not isinstance(item, dict):
            raise InventoryAuditError("Malformed asset registry entry")
        key = str(item.get("source_asset_key") or source_asset_key(item) or "").strip().lower()
        if not key:
            missing_registry_identity += 1
        else:
            record_keys.add(key)
        if not item.get("perceptual_hash"):
            missing_registry_visual_fingerprint += 1

    paths = _all_manifests(root)
    all_uses: list[dict[str, Any]] = []
    unidentifiable = []
    missing_declarations = []
    for path in paths:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InventoryAuditError(f"Unreadable manifest: {path}") from exc
        episode_id = str(manifest.get("video_id") or "").strip()
        if not episode_id:
            raise InventoryAuditError(f"Manifest video_id absent: {path}")
        for scene in manifest.get("scenes") or []:
            if not isinstance(scene, dict):
                continue
            asset = scene.get("asset")
            if not isinstance(asset, dict):
                continue
            key = source_asset_key(asset)
            ref = {"episode_id": episode_id, "scene_id": str(scene.get("scene_id") or ""),
                   "manifest": path.relative_to(root).as_posix(), "source_key": key}
            all_uses.append(ref)
            if not key:
                unidentifiable.append(ref)
            for field in ("source_page_url", "license", "sha256"):
                if not asset.get(field):
                    missing_declarations.append({**ref, "missing_field": field})

    source_users = defaultdict(set)
    for use in all_uses:
        if use["source_key"]:
            source_users[use["source_key"].lower()].add(use["episode_id"])
    used_keys = set(source_users)
    absent = sorted(used_keys - record_keys)
    cross_ep = sorted(
        [{"source_key": key, "episode_ids": sorted(ids)}
         for key, ids in source_users.items() if len(ids) > 1],
        key=lambda r: r["source_key"],
    )
    complete = (not absent and not unidentifiable and not missing_declarations
                and not missing_registry_identity and not missing_registry_visual_fingerprint)
    return {
        "schema_version": "1.1",
        "status": "LOCAL_METADATA_COVERAGE_PASS" if complete else "LOCAL_METADATA_COVERAGE_PARTIAL",
        "independent_licensing_verified": False,
        "drive_inventory_verified": False,
        "git_history_across_branches_verified": False,
        "media_similarity_verified": False,
        "manifest_count": len(paths),
        "manifest_asset_references": len(all_uses),
        "unique_source_keys": len(used_keys),
        "registry_entry_count": len(registered),
        "registry_unique_source_keys": len(record_keys),
        "sources_without_registry_entries": len(absent),
        "missing_source_key_examples": absent[:15],
        "manifest_assets_without_identity": len(unidentifiable),
        "manifest_missing_declaration_count": len(missing_declarations),
        "registry_missing_identity_count": missing_registry_identity,
        "registry_missing_perceptual_hash_count": missing_registry_visual_fingerprint,
        "cross_episode_source_aliases": cross_ep[:40],
        "cross_episode_source_alias_count": len(cross_ep),
        "notes": [
            "Draft/final snapshots with differing episode IDs may be the same narrative: review manually.",
            "Historical pilot reuse is evidence for the archive, not a license for future reuse.",
            "A catalog report cannot certify external rights, physical frames, historical Git refs or Drive completeness.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    report = inspect(args.root)
    serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized)
    return 0  # diagnostic PARTIAL is expected; never pretend READY


if __name__ == "__main__":
    raise SystemExit(main())
