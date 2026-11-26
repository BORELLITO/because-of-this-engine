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
LOGO_SHA256 = "5c062475dd174b5b314f53ea9e9f7be64ad534ae529c791ea8668265cc5dc33b"
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

# Compatibility aliases kept for existing V2.1 tests and reporting imports.
IN_VIDEO_LOGO_WIDTH = LOGO_WIDTH
IN_VIDEO_LOGO_Y = LOGO_Y


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


# Search-intake policy: the reference MP4 may define sequence only.  A source
# with inherited/burned overlays must never enter the active visual candidate
# pool as if it were a clean clip.  Missing pixel evidence remains review-only.
_SOURCE_BLOCK_FLAGS = (
    "text_overlay_present",
    "authored_graphics_present",
    "compositor_layers_disclosed",
    "overlay_present",
    "burned_in_overlay",
    "burned_in_text",
    "logo_burned_in",
    "captions_burned_in",
    "reference_overlay_inherited",
)
_ALLOWED_EMBEDDED_TEXT_STATUSES = {"NONE", "NATURAL_SOURCE_ONLY"}
_REFERENCE_OVERLAY_POLICIES = {
    "INHERIT",
    "INHERIT_REFERENCE",
    "BURNED_IN",
    "RENDER_WITH_REFERENCE_OVERLAY",
}


def visual_source_gate(candidate: dict[str, object]) -> dict[str, object]:
    """Apply the locked clean-source policy at search intake.

    Search providers may return metadata without pixel evidence.  That is not
    approval: it remains REVIEW_REQUIRED until the clean-source evidence is
    present.  Explicit overlay or inherited-reference signals are rejected
    immediately so the sample MP4 cannot contaminate the active candidate pool.
    """
    evidence = candidate.get("visual_evidence")
    evidence_map = evidence if isinstance(evidence, dict) else {}
    pixel_qc = evidence_map.get("pixel_qc")
    if not isinstance(pixel_qc, dict):
        pixel_qc = candidate.get("pixel_qc")
    if not isinstance(pixel_qc, dict):
        pixel_qc = {}

    reasons: list[str] = []
    for key in _SOURCE_BLOCK_FLAGS:
        if candidate.get(key) is True or pixel_qc.get(key) is True:
            reasons.append(f"{key}=true")
    embedded_text_status = str(
        pixel_qc.get("embedded_text_status")
        or candidate.get("embedded_text_status")
        or ""
    ).strip().upper()
    if embedded_text_status and embedded_text_status not in _ALLOWED_EMBEDDED_TEXT_STATUSES:
        reasons.append(f"embedded_text_status={embedded_text_status}")
    external_branding = str(
        pixel_qc.get("external_branding")
        or candidate.get("external_branding")
        or ""
    ).strip().upper()
    if external_branding and external_branding not in {"NONE", "NATURAL_SOURCE_ONLY"}:
        reasons.append(f"external_branding={external_branding}")
    overlay_policy = str(
        candidate.get("reference_overlay_policy")
        or candidate.get("overlay_policy")
        or ""
    ).strip().upper()
    if overlay_policy in _REFERENCE_OVERLAY_POLICIES:
        reasons.append(f"reference_overlay_policy={overlay_policy}")
    if candidate.get("clean_source") is False:
        reasons.append("clean_source=false")

    evidence_complete = all(
        key in pixel_qc
        for key in (
            "text_overlay_present",
            "authored_graphics_present",
            "compositor_layers_disclosed",
            "embedded_text_status",
        )
    )
    if reasons:
        status = "BLOCKED"
    elif evidence_complete:
        status = "PASS"
    else:
        status = "REVIEW_REQUIRED"
    return {
        "status": status,
        "policy": "CLIP_SEQUENCE_ONLY",
        "clean_source_required": True,
        "evidence_present": bool(pixel_qc),
        "evidence_complete": evidence_complete,
        "reasons": reasons,
    }
