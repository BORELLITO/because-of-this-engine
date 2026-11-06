#!/usr/bin/env python3
"""Recolor only the active-word karaoke transform in an existing ASS file."""

from __future__ import annotations

import argparse
from pathlib import Path


OLD_ASS_COLOR = "&H007777FF&"  # RGB #FF7777 (legacy pink)
ACTIVE_ASS_COLOR = "&H004444F0&"  # RGB #F04444 (brand red, still readable)
CAPTION_MARGIN_V = 650


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    if OLD_ASS_COLOR not in text and ACTIVE_ASS_COLOR not in text:
        raise SystemExit("No known karaoke active-word transform was found.")
    recolored = text.replace(OLD_ASS_COLOR, ACTIVE_ASS_COLOR)
    lines = []
    for line in recolored.splitlines(keepends=True):
        if line.startswith("Style: Default,"):
            fields = line.rstrip("\r\n").split(",")
            if len(fields) >= 3:
                fields[-2] = str(CAPTION_MARGIN_V)
                line = ",".join(fields) + ("\n" if line.endsWith("\n") else "")
        lines.append(line)
    recolored = "".join(lines)
    if ACTIVE_ASS_COLOR not in recolored:
        raise SystemExit("Karaoke recolor did not produce the expected active color.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(recolored, encoding="utf-8")
    print({"status": "KARAOKE_RECOLOR_PASS", "active_word_color": "#F04444", "output": str(args.output)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
