"""Audit source identities across *all fetched Git remote branch snapshots*.

Read-only. Never checks out old branches, downloads media, calls external APIs,
retires drafts, changes licenses, merges code, renders or synthesizes speech.
A source in a draft is classified as RESERVED_UNKNOWN, never auto-consumed.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from production.asset_reuse_brain import source_asset_key

MANIFEST_PATH = re.compile(r"^episodes/[^/]+/(?:manifest|preview-manifest)\.json$")
STATUSES = ("FINAL_APPROVED", "ARCHIVED_HISTORICAL", "OTHER")
MAX_MANIFEST_SIZE = 4 * 1024 * 1024


class GitHistoryAuditError(RuntimeError):
    pass


def _git(root: Path, *args: str) -> bytes:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, timeout=45,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitHistoryAuditError(f"Git history read failed: {args[:2]}: {exc}") from exc
    return proc.stdout


def _remote_refs(root: Path) -> list[str]:
    raw = _git(root, "for-each-ref", "--format=%(refname)", "refs/remotes/origin/")
    refs = sorted(set(raw.decode("utf-8").splitlines()))
    refs = [r for r in refs if r != "refs/remotes/origin/HEAD"]
    if not refs:
        raise GitHistoryAuditError("No fetched origin branch refs. Fetch all remote heads first.")
    return refs


def _get_local_sources(root: Path) -> set[str]:
    sources: set[str] = set()
    episodes = root / "episodes"
    for path in sorted(episodes.glob("*/manifest.json")) + sorted(episodes.glob("*/preview-manifest.json")):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise GitHistoryAuditError(f"Local manifest unreadable: {path}") from exc
        for scene in manifest.get("scenes") or []:
            if isinstance(scene, dict) and isinstance(scene.get("asset"), dict):
                key = source_asset_key(scene["asset"])
                if key:
                    sources.add(key.lower())
    return sources


def audit(root: Path, *, refs: list[str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    refs = _remote_refs(root) if refs is None else list(dict.fromkeys(refs))
    if not refs:
        raise GitHistoryAuditError("At least one branch ref required")
    local = _get_local_sources(root)

    cache: dict[str, dict[str, Any] | None] = {}
    source_states: dict[str, set[str]] = defaultdict(set)
    source_episodes: dict[str, set[str]] = defaultdict(set)
    source_branches: dict[str, set[str]] = defaultdict(set)
    broken: list[dict[str, str]] = []
    parsed_snapshots = 0
    manifest_occurrences = 0

    for ref in refs:
        lines = _git(root, "ls-tree", "-r", "-z", ref, "--", "episodes/").split(b"\0")
        for raw in lines:
            if not raw or b"\t" not in raw:
                continue
            meta, rel = raw.split(b"\t", 1)
            path = rel.decode("utf-8", errors="replace")
            if not MANIFEST_PATH.fullmatch(path):
                continue
            parts = meta.decode("ascii", errors="replace").split()
            if len(parts) < 3 or parts[1] != "blob":
                continue
            sha = parts[2]
            manifest_occurrences += 1
            if sha not in cache:
                try:
                    size = int(_git(root, "cat-file", "-s", sha).strip())
                    if not 0 < size <= MAX_MANIFEST_SIZE:
                        raise ValueError(f"file size {size} not in safe bounds")
                    value = json.loads(_git(root, "cat-file", "-p", sha))
                    if not isinstance(value, dict):
                        raise ValueError("manifest is not a JSON object")
                    cache[sha] = value
                    parsed_snapshots += 1
                except (GitHistoryAuditError, ValueError, UnicodeError) as exc:
                    broken.append({"blob": sha[:12], "path": path, "error": str(exc)[:130]})
                    cache[sha] = None
            manifest = cache[sha]
            if manifest is None:
                continue
            episode = str(manifest.get("video_id") or "").strip()
            if not episode:
                broken.append({"blob": sha[:12], "path": path, "error": "missing video_id"})
                continue
            lifecycle = str(manifest.get("lifecycle_status") or "OTHER").strip().upper()
            if lifecycle not in STATUSES:
                lifecycle = "OTHER"
            for scene in manifest.get("scenes") or []:
                if not isinstance(scene, dict) or not isinstance(scene.get("asset"), dict):
                    continue
                key = source_asset_key(scene["asset"])
                if not key:
                    continue
                key = key.lower()
                source_states[key].add(lifecycle)
                source_episodes[key].add(episode)
                source_branches[key].add(ref)

    historical = set(source_states)
    extra = sorted(historical - local)
    missing_by_class = {"final_approved": 0, "archived_only": 0, "draft_or_other_only": 0}
    for key in extra:
        states = source_states[key]
        if "FINAL_APPROVED" in states:
            missing_by_class["final_approved"] += 1
        elif "ARCHIVED_HISTORICAL" in states:
            missing_by_class["archived_only"] += 1
        else:
            missing_by_class["draft_or_other_only"] += 1

    return {
        "schema_version": "1.1",
        "status": "HISTORY_METADATA_PARTIAL" if not broken else "HISTORY_SCAN_INCOMPLETE",
        "branch_ref_count": len(refs),
        "manifest_occurrences_across_refs": manifest_occurrences,
        "unique_manifest_blobs_parsed": parsed_snapshots,
        "malformed_snapshots": broken[:20],
        "malformed_snapshot_count": len(broken),
        "local_source_key_count": len(local),
        "git_history_unique_source_key_count": len(historical),
        "historical_sources_not_in_current_tree": len(extra),
        "historical_extra_by_lifecycle": missing_by_class,
        "historical_extra_examples": [
            {
                "source_key": key, "lifecycle_states": sorted(source_states[key]),
                "episode_ids": sorted(source_episodes[key])[:5],
                "branch_example": sorted(source_branches[key])[0],
                "classification": "EVIDENCE_ONLY_NEVER_AUTORETIRE",
            }
            for key in extra[:30]
        ],
        "source_identity_scope": "provider/source_url identities from fetched Git branch manifest blobs; no binary hashing",
        "git_references_complete_for_fetched_refs": not broken,
        "drive_inventory_verified": False,
        "copyright_or_license_verified": False,
        "published_usage_verified": False,
        "approval_to_use_in_new_video": False,
        "automatic_draft_retirement": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return int(result["status"] == "HISTORY_SCAN_INCOMPLETE")


if __name__ == "__main__":
    raise SystemExit(main())
