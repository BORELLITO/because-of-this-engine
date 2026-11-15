"""Single source of truth for the active Because Of This V2.1 visual composition.

This contract is intentionally separate from the archived V7 manifest helpers.
It prevents a legacy logo/caption layout from silently re-entering the active
preview route.
"""

from __future__ import annotations

from pathlib import Path


ACTIVE_PROFILE = "because-of-this-v2.1-canonical-factual-gemini-charon-2026-11"
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 60

# In-video watermark: the transparent original wordmark, not recreated text.
LOGO_ASSET = "brand/because-of-this-wordmark-transparent.png"
LOGO_SHA256 = "5c062475dd174b5b314f53ae9e9f7be64ad534ae529c791ea8668265cc5dc33b"
LOGO_ANCHOR = "center_upper"
LOGO_WIDTH = 360
LOGO_Y = 190
IN_VIDEO_LOGO_OPACITY = 0.90

# Caption contract: centered lower-third, forced word timestamps only.
CAPTION_ALIGNMENT = 2
CAPTION_MARGIN_L = 100
CAPTION_MARGIN_R = 100
CAPTION_MARGIN_V = 650
CAPTION_MAX_LINES = 2
CAPTION_MAX_LINE_CHARS = 42
ACTIVE_WORD_COLOR = "#F04444"

# Branded outro contract.
OUTRO_ANCHOR = "center_center"
OUTRO_LOGO_WIDTH = 620
OUTRO_SECONDS = 5.5
OUTRO_TRANSITION = "brand_background_to_black"


def expected_contract() -> dict[str, object]:
    return {
        "profile": ACTIVE_PROFILE,
        "video": {"width": VIDEO_WIDTH, "height": VIDEO_HEIGHT, "fps": VIDEO_FPS},
        "logo": {
            "asset": LOGO_ASSET,
            "sha256": LOGO_SHA256,
            "anchor": LOGO_ANCHOR,
            "width": LOGO_WIDTH,
            "y": LOGO_Y,
            "opacity": IN_VIDEO_LOGO_OPACITY,
        },
        "captions": {
            "alignment": CAPTION_ALIGNMENT,
            "margin_l": CAPTION_MARGIN_L,
            "margin_r": CAPTION_MARGIN_R,
            "margin_v": CAPTION_MARGIN_V,
            "max_lines": CAPTION_MAX_LINES,
            "max_line_chars": CAPTION_MAX_LINE_CHARS,
            "active_word_color": ACTIVE_WORD_COLOR,
        },
        "outro": {
            "anchor": OUTRO_ANCHOR,
            "logo_width": OUTRO_LOGO_WIDTH,
            "seconds": OUTRO_SECONDS,
            "transition": OUTRO_TRANSITION,
        },
    }


def validate_logo_path(path: Path, *, sha256: str) -> None:
    if path.name != Path(LOGO_ASSET).name:
        raise ValueError(
            "Active V2.1 preview requires the original transparent wordmark: "
            + LOGO_ASSET
        )
    if sha256.lower() != LOGO_SHA256:
        raise ValueError("Logo hash does not match the canonical original PNG.")


def reject_legacy_layout(values: dict[str, object]) -> None:
    """Fail closed when a legacy V7 layout is presented as active V2.1."""
    legacy_markers = {
        "logo_y": 72,
        "logo_width": 540,
        "logo_opacity": 0.82,
        "caption_margin_v": 320,
        "outro_logo_width": 820,
    }
    for key, legacy_value in legacy_markers.items():
        if values.get(key) == legacy_value:
            raise ValueError(f"Legacy visual layout marker is forbidden in V2.1: {key}={legacy_value}")


def validate_caption_ass(path: Path) -> None:
    """Validate the burned-in ASS layout before FFmpeg touches the picture."""
    text = path.read_text(encoding="utf-8")
    style_lines = [line for line in text.splitlines() if line.startswith("Style: Default,")]
    if len(style_lines) != 1:
        raise ValueError("Active V2.1 captions require exactly one Default ASS style.")
    fields = style_lines[0].split(",")
    # ASS fields: alignment=18, margin_l=19, margin_r=20, margin_v=21.
    expected = {
        18: str(CAPTION_ALIGNMENT),
        19: str(CAPTION_MARGIN_L),
        20: str(CAPTION_MARGIN_R),
        21: str(CAPTION_MARGIN_V),
    }
    for index, value in expected.items():
        if len(fields) <= index or fields[index] != value:
            actual = fields[index] if len(fields) > index else "<missing>"
            raise ValueError(
                f"Caption ASS layout drift at field {index}: expected {value}, got {actual}"
            )
    if "&H004444F0&" not in text:
        raise ValueError("Caption ASS is missing the canonical active-word red #F04444 transform.")
    if "—" in text or "–" in text:
        raise ValueError("Caption ASS contains a forbidden em dash or en dash.")
