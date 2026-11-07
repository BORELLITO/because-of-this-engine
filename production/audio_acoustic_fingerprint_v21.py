"""Read-only Chromaprint acoustic similarity gate for known historical music.

Compares actual decoded audio through FFmpeg's Chromaprint muxer. Robust for
gain, lossy re-encoding and excerpts. No claim of copyright clearance,
source separation, worldwide originality, or publication authorization.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import struct
import subprocess
import zlib
from pathlib import Path
from typing import Any

ALGORITHM = "ffmpeg-chromaprint-algo1-raw32-v1"
CATALOG_PATH = Path("episodes/audio-acoustic-fingerprints-v21.json")
MIN_FRAMES = 64
WINDOW_FRAMES = 96
REUSE_THRESHOLD = 0.88
REVIEW_THRESHOLD = 0.78
MAX_DECODE_SECONDS = 360


class FingerprintError(RuntimeError):
    pass


def fingerprint(path: Path, *, ffmpeg: str = "ffmpeg") -> list[int]:
    if not path.is_file() or not path.stat().st_size:
        raise FingerprintError("audio source missing or empty")
    argv = [ffmpeg, "-nostdin", "-hide_banner", "-v", "error", "-i", str(path),
            "-vn", "-t", str(MAX_DECODE_SECONDS), "-f", "chromaprint",
            "-algorithm", "1", "-fp_format", "raw", "-"]
    try:
        p = subprocess.run(argv, capture_output=True, timeout=90, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FingerprintError("Chromaprint decoder or execution failed") from exc
    raw = p.stdout
    if not raw or len(raw) % 4 or len(raw) > 4 * 4000:
        raise FingerprintError("invalid raw acoustic fingerprint")
    frames = list(struct.unpack("<%dI" % (len(raw) // 4), raw))
    if len(frames) < MIN_FRAMES:
        raise FingerprintError("too little audio for acoustic matching")
    return frames


def pack(frames: list[int]) -> dict[str, Any]:
    if not MIN_FRAMES <= len(frames) <= 4000:
        raise FingerprintError("invalid fingerprint frame count")
    raw = struct.pack("<%dI" % len(frames), *frames)
    return {"algorithm": ALGORITHM, "frame_count": len(frames),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "compressed_words_b64": base64.b64encode(zlib.compress(raw, 9)).decode("ascii")}


def unpack(data: dict[str, Any]) -> list[int]:
    if data.get("algorithm") != ALGORITHM:
        raise FingerprintError("fingerprint algorithm mismatch")
    try:
        count = data["frame_count"]
        if type(count) is not int or not MIN_FRAMES <= count <= 4000:
            raise FingerprintError("invalid fingerprint count")
        value = base64.b64decode(data["compressed_words_b64"], validate=True)
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(value, count * 4 + 1)
        if (len(raw) != count * 4 or not decompressor.eof or
                decompressor.unused_data or decompressor.unconsumed_tail):
            raise FingerprintError("untrusted fingerprint payload")
        if hashlib.sha256(raw).hexdigest() != data["raw_sha256"]:
            raise FingerprintError("fingerprint SHA mismatch")
        return list(struct.unpack("<%dI" % count, raw))
    except (KeyError, ValueError, zlib.error, struct.error) as exc:
        raise FingerprintError("unreadable fingerprint entry") from exc


def compare(first: list[int], second: list[int]) -> dict[str, Any]:
    if min(len(first), len(second)) < MIN_FRAMES:
        raise FingerprintError("comparison requires at least 64 frames")
    short, long = sorted((first, second), key=len)
    width = min(len(short), WINDOW_FRAMES)
    best = (0.0, 0, 0)
    windows = sorted({0, max(0, (len(short) - width) // 2), len(short) - width})
    for origin in windows:
        fragment = short[origin:origin + width]
        for offset in range(len(long) - width + 1):
            mismatch = sum((x ^ y).bit_count()
                           for x, y in zip(fragment, long[offset:offset + width]))
            score = 1 - mismatch / (32 * width)
            if score > best[0]:
                best = score, offset, origin
                if score == 1.0:
                    break
        if best[0] == 1.0:
            break
    return {"similarity": round(best[0], 5), "compared_frames": width,
            "long_offset_frames": best[1], "short_offset_frames": best[2],
            "classification": ("LIKELY_REUSE" if best[0] >= REUSE_THRESHOLD else
                               "REVIEW_REQUIRED" if best[0] >= REVIEW_THRESHOLD else
                               "NO_MATCH_IN_KNOWN_CATALOG")}


def review_file(path: Path, catalog_path: Path) -> dict[str, Any]:
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        if (catalog.get("algorithm") != ALGORITHM or
                not isinstance(catalog.get("sources"), list) or not catalog["sources"]):
            raise FingerprintError("acoustic catalog is unavailable or invalid")
        frames = fingerprint(path)
        results = []
        observed = set()
        for source in catalog["sources"]:
            identity = source["source_sha256"]
            if identity in observed or len(identity) != 64:
                raise FingerprintError("duplicate or invalid catalog source identity")
            observed.add(identity)
            result = compare(frames, unpack(source["fingerprint"]))
            results.append({"source_id": source["source_id"],
                            "source_sha256": identity, **result})
        results.sort(key=lambda r: -r["similarity"])
        best = results[0]
        return {"gate": "AUDIO_ACOUSTIC_REUSE_V21",
                "status": ("BLOCKED" if best["classification"] != "NO_MATCH_IN_KNOWN_CATALOG"
                           else "PASS"),
                "candidate_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "candidate_frames": len(frames), "best_matches": results[:5],
                "suspected_reuse": best["classification"] != "NO_MATCH_IN_KNOWN_CATALOG",
                "ready_for_render": False, "publication_authorized": False,
                "limitations": "Known-source similarity only; excludes external/unindexed music and source separation."}
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, FingerprintError) as exc:
        return {"gate": "AUDIO_ACOUSTIC_REUSE_V21", "status": "BLOCKED",
                "failures": [str(exc)], "ready_for_render": False,
                "publication_authorized": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    a = parser.parse_args()
    result = review_file(a.file, a.catalog)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
