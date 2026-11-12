"""Fail-closed lock for the one active Because Of This runtime surface."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ACTIVE_VERSION = "2.1"
ACTIVE_ENTRYPOINT = "production/canonical_entrypoint.py"
ACTIVE_PROFILE = "because-of-this-v2.1-canonical-factual-gemini-charon-2026-11"

# These files remain in the repository only for audit/rollback evidence. They
# must never be imported by the active V2.1 runtime.
LEGACY_FILES = {
    "align_edge_captions.py",
    "cloud_tts.py",
    "microsoft_edge_tts.py",
    "piper_tts.py",
    "production_record_v7.py",
    "release_integrity_v72.py",
    "render_video_episode.py",
    "v7_contract.py",
    "v7_orchestrator.py",
    "v7_post_publication.py",
    "v7_singleton_guard.py",
    "visual_effects_v73.py",
}

LEGACY_MODULE_PREFIXES = (
    "production.align_edge_captions",
    "production.cloud_tts",
    "production.microsoft_edge_tts",
    "production.piper_tts",
    "production.production_record_v7",
    "production.release_integrity_v72",
    "production.render_video_episode",
    "production.v7_contract",
    "production.v7_orchestrator",
    "production.v7_post_publication",
    "production.v7_singleton_guard",
    "production.visual_effects_v73",
)


def _module_path(root: Path, module: str) -> Path | None:
    if not module.startswith("production."):
        return None
    relative = Path(*module.split("."))
    candidate = root / f"{relative}.py"
    if candidate.is_file():
        return candidate
    package_init = root / relative / "__init__.py"
    return package_init if package_init.is_file() else None


def _imports_from(path: Path, root: Path) -> list[Path]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return []
    imports: list[Path] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported = _module_path(root, alias.name)
                if imported is not None:
                    imports.append(imported)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                # Active modules use absolute production imports today; retain
                # relative resolution for future modules in the same package.
                base = path.parent
                for _ in range(max(0, node.level - 1)):
                    base = base.parent
                candidate = base / Path(*module.split(".")) if module else base
                candidate_py = candidate.with_suffix(".py")
                if candidate_py.is_file():
                    imports.append(candidate_py)
            else:
                imported = _module_path(root, module)
                if imported is not None:
                    imports.append(imported)
    return imports


def _active_module_paths(root: Path) -> list[Path]:
    """Return the import closure of the canonical entrypoint and its guards."""
    seeds = [
        root / ACTIVE_ENTRYPOINT,
        root / "production" / "v21_singleton_guard.py",
        root / "production" / "active_surface_lock_v21.py",
    ]
    pending = [path for path in seeds if path.is_file()]
    visited: set[Path] = set()
    ordered: list[Path] = []
    while pending:
        path = pending.pop(0).resolve()
        if path in visited:
            continue
        visited.add(path)
        ordered.append(path)
        pending.extend(_imports_from(path, root))
    return ordered


def _legacy_imports(root: Path) -> list[str]:
    failures: list[str] = []
    for path in _active_module_paths(root):
        if path.name in LEGACY_FILES:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            failures.append(f"active module unreadable:{path.name}:{exc}")
            continue
        for node in ast.walk(tree):
            imported = ""
            if isinstance(node, ast.Import):
                imported = next((alias.name for alias in node.names), "")
            elif isinstance(node, ast.ImportFrom):
                imported = node.module or ""
            if any(imported == prefix or imported.startswith(prefix + ".") for prefix in LEGACY_MODULE_PREFIXES):
                failures.append(f"active module imports retired runtime:{path.name}->{imported}")
    return failures


def audit(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    failures: list[str] = []
    policy_path = root / "production" / "active_engine_policy.json"
    readme_path = root / "README.md"

    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "ACTIVE_SURFACE_LOCK_BLOCKED", "failures": [f"policy unreadable:{exc}"]}

    if policy.get("active_engine_version") != ACTIVE_VERSION:
        failures.append("active engine version drifted from V2.1")
    if policy.get("active_engine_profile") != ACTIVE_PROFILE:
        failures.append("active engine profile drifted from canonical V2.1 Gemini/Charon")
    if policy.get("canonical_entrypoint") != ACTIVE_ENTRYPOINT:
        failures.append("canonical entrypoint drifted")
    if policy.get("voice_provider") != "gemini_tts":
        failures.append("active voice provider is not direct Gemini TTS")
    voice = policy.get("voice_policy") if isinstance(policy.get("voice_policy"), dict) else {}
    if voice.get("model") != "gemini-3.8-flash-tts" or voice.get("voice_name") != "Charon":
        failures.append("active voice identity drifted from Gemini/Charon")
    if voice.get("creative_claw_allowed") is not False:
        failures.append("Creative Claw is not explicitly forbidden")
    if policy.get("production_enablement") is not False:
        failures.append("production must remain fail-closed")
    if policy.get("publication_policy") != "manual_only":
        failures.append("publication must remain manual-only")
    if (policy.get("legacy_policy") or {}).get("active_runtime") != ACTIVE_ENTRYPOINT:
        failures.append("legacy policy does not point back to the canonical entrypoint")

    if not readme_path.is_file():
        failures.append("canonical README missing")
    else:
        readme = readme_path.read_text(encoding="utf-8")
        required = (
            "Motor Canônico V2.1",
            ACTIVE_ENTRYPOINT,
            "gemini-3.8-flash-tts",
            "Charon",
        )
        failures.extend(f"README missing canonical marker:{marker}" for marker in required if marker not in readme)
        forbidden_active_markers = (
            "V7.1 Piper Canonical Engine + Active V7.2",
            "Narration provider: local Piper neural TTS only",
            "Active V7.2 Reuse First",
        )
        failures.extend(
            f"README advertises retired active runtime:{marker}"
            for marker in forbidden_active_markers
            if marker in readme
        )

    for relative in (ACTIVE_ENTRYPOINT, "production/v21_singleton_guard.py"):
        if not (root / relative).is_file():
            failures.append(f"canonical runtime file missing:{relative}")

    entrypoint = root / ACTIVE_ENTRYPOINT
    if entrypoint.is_file():
        source = entrypoint.read_text(encoding="utf-8", errors="replace")
        if 'media_generation": "NOT_RUN"' not in source or 'publication": "MANUAL_ONLY_NOT_RUN"' not in source:
            failures.append("canonical entrypoint lost read-only fail-closed markers")

    failures.extend(_legacy_imports(root))

    return {
        "status": "ACTIVE_SURFACE_LOCK_PASS" if not failures else "ACTIVE_SURFACE_LOCK_BLOCKED",
        "active_engine_version": policy.get("active_engine_version"),
        "canonical_entrypoint": policy.get("canonical_entrypoint"),
        "legacy_import_failures": [x for x in failures if "retired runtime" in x],
        "failures": failures,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    result = audit(parser.parse_args().repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "ACTIVE_SURFACE_LOCK_PASS" else 1)
