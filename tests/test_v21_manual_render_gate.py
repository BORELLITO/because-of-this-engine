import json
from pathlib import Path

from production.render_v21_manual import validate_request


def test_manual_render_gate_is_blocked_by_candidate_policy(tmp_path: Path) -> None:
    record = {
        "production_enablement": False,
        "render_contract": {
            "width": 1080,
            "height": 1920,
            "fps": 60,
            "render_executed": False,
        },
    }
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "active_engine_version": "2.1",
                "canonical_entrypoint": "production/canonical_entrypoint.py",
                "manual_render_entrypoint": "production/render_v21_manual.py",
                "publication_policy": "manual_only",
                "production_enablement": False,
            }
        ),
        encoding="utf-8",
    )
    report = validate_request(
        record,
        repo_root=tmp_path,
        policy_path=policy,
    )
    assert report["status"] == "V21_MANUAL_RENDER_BLOCKED"
    assert report["render"] == "NOT_RUN"
    assert any("production_enablement=false" in item for item in report["failures"])


def test_manual_render_gate_requires_final_thumbnail_and_human_authorization(tmp_path: Path) -> None:
    record = {
        "production_enablement": True,
        "render_authorization": {"status": "PENDING"},
        "render_contract": {
            "width": 1080,
            "height": 1920,
            "fps": 60,
            "render_executed": False,
        },
    }
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "active_engine_version": "2.1",
                "canonical_entrypoint": "production/canonical_entrypoint.py",
                "manual_render_entrypoint": "production/render_v21_manual.py",
                "publication_policy": "manual_only",
                "production_enablement": True,
            }
        ),
        encoding="utf-8",
    )
    report = validate_request(record, repo_root=tmp_path, policy_path=policy)
    assert report["status"] == "V21_MANUAL_RENDER_BLOCKED"
    assert any("render_authorization" in item for item in report["failures"])
    assert any("thumbnail_manifest" in item for item in report["failures"])
