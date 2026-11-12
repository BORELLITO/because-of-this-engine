"""Single caption-style authority for the active Because Of This V2.1 path."""

from __future__ import annotations

import json
from pathlib import Path


POLICY_PATH = Path(__file__).resolve().parent / "caption_policy_v21.json"


def load_policy() -> dict:
    value = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("project") != "Because Of This Stories":
        raise ValueError("caption policy is not scoped to Because Of This Stories")
    return value


def caption_ass_style_line(name: str = "Default", margin_v: int | None = None) -> str:
    policy = load_policy()
    layout = policy["layout"]
    resolved_margin_v = layout["margin_v"] if margin_v is None else int(margin_v)
    fields = (
        name, "Arial", 48, "&H00FFFFFF&", "&H00FFFFFF&", "&H00000000&",
        "&H80000000&", 1, 0, 0, 0, 100, 100, 0, 0, 1, 3, 1,
        layout["alignment"], layout["margin_l"], layout["margin_r"],
        resolved_margin_v, 1,
    )
    return "Style: " + ",".join(str(value) for value in fields)


def default_active_word_color() -> str:
    return str(load_policy()["alignment"]["active_word_color"])


def forbidden_caption_characters() -> tuple[str, ...]:
    return tuple(str(item) for item in load_policy()["forbidden_caption_characters"])


def validate_caption_text(text: str) -> None:
    forbidden = forbidden_caption_characters()
    found = sorted({character for character in forbidden if character in text})
    if found:
        raise ValueError(
            "caption contains forbidden dash character(s): " + ", ".join(repr(item) for item in found)
        )
