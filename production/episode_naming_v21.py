"""V2.1 display naming contract for numbered Because Of This episodes."""
from __future__ import annotations

import re
from typing import Any

EPISODE_ID = re.compile(r"^episode-(\d+)$")
DISPLAY_NAME = re.compile(r"^(\d{2}) - (.+)$")


def validate_episode_naming(record: dict[str, Any]) -> dict[str, Any]:
    """Validate NN - VIDEO TITLE without changing the immutable technical ID.

    Legacy/synthetic records that do not carry naming fields are left untouched.
    Once a record supplies a title/display name, the numbered convention is
    enforced and mismatches are blocking.
    """
    raw_title = str(record.get("video_title") or "").strip()
    display_name = str(record.get("display_name") or record.get("episode_name") or "").strip()
    if not raw_title and not display_name:
        return {
            "gate": "EPISODE_NAMING",
            "status": "PASS",
            "mode": "NOT_APPLICABLE_LEGACY_OR_SYNTHETIC",
            "failures": [],
        }

    failures: list[str] = []
    episode_id = str(record.get("episode_id") or "").strip()
    match = EPISODE_ID.fullmatch(episode_id)
    if not match:
        failures.append("episode_id must match episode-NNN")
    if not raw_title:
        failures.append("video_title is required when display naming is enabled")
    if not display_name:
        failures.append("display_name or episode_name is required")
    parsed = DISPLAY_NAME.fullmatch(display_name)
    if not parsed:
        failures.append("display name must match NN - VIDEO TITLE")
    elif match:
        expected_number = f"{int(match.group(1)):02d}"
        if parsed.group(1) != expected_number:
            failures.append("display name number does not match episode_id")
    if raw_title and display_name and display_name != f"{parsed.group(1) if parsed else '00'} - {raw_title}":
        failures.append("display name title does not match video_title")
    return {
        "gate": "EPISODE_NAMING",
        "status": "PASS" if not failures else "BLOCKED",
        "mode": "NUMBERED_VIDEO_TITLE",
        "episode_id": episode_id,
        "video_title": raw_title,
        "display_name": display_name,
        "failures": sorted(set(failures)),
    }
