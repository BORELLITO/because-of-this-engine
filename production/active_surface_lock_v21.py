"""Fail-closed lock for the one active Because Of This runtime surface.

This guard prevents documentation, policy and entrypoint drift from making a
retired V7/Piper/Creative Claw path look executable again.
"""

from __future__ import annotations

import json
from pathlib import Path

ACTIVE_VERSION = "2.1"
ACTIVE_ENTRYPOINT = "production/canonical_entrypoint.py"
ACTIVE_PROFILE = "because-of-this-v2.1-canonical-factual-gemini-charon-2026-11"


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

    if not readme_path.is_file():
        failures.append("canonical README missing")
    else:
        readme = readme_path.read_text(encoding="utf-8")
        required = (
            "Motor Canônico V2.1",
            "production/canonical_entrypoint.py",
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

    for relative in ("production/canonical_entrypoint.py", "production/v21_singleton_guard.py"):
        if not (root / relative).is_file():
            failures.append(f"canonical runtime file missing:{relative}")

    return {
        "status": "ACTIVE_SURFACE_LOCK_PASS" if not failures else "ACTIVE_SURFACE_LOCK_BLOCKED",
        "active_engine_version": policy.get("active_engine_version"),
        "canonical_entrypoint": policy.get("canonical_entrypoint"),
        "failures": failures,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    result = audit(parser.parse_args().repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "ACTIVE_SURFACE_LOCK_PASS" else 1)
