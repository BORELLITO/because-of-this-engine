"""Verified FFmpeg mix execution receipts without changing the approved sound profile.

This adapter wraps a caller-supplied, already-approved local FFmpeg audio mix
argv, hashes real source and mixed PCM bytes, and independently replays the
same recipe. It is NOT the active V2.1 renderer or a publication authority.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

ALGORITHM = "verified-local-ffmpeg-mix-replay-v1"


class MixReceiptError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def decoded_pcm_sha256(path: Path) -> str:
    args = ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
            "-i", str(path), "-map", "0:a:0",
            "-ac", "1", "-ar", "48000", "-f", "s16le", "-"]
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sha = hashlib.sha256()
        size = 0
        while True:
            chunk = proc.stdout.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            sha.update(chunk)
        proc.stderr.read(65536)
        if proc.wait(timeout=40) or size < 192000:
            raise MixReceiptError("decoded audio missing or too short")
        return sha.hexdigest()
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MixReceiptError("FFmpeg PCM decoding failed") from exc


def _validate(command: list[str], sources: Mapping[str, Path], output: Path) -> None:
    if not isinstance(command, list) or len(command) < 5 or Path(command[0]).name != "ffmpeg":
        raise MixReceiptError("requires explicit FFmpeg argv")
    if not {"narration", "music"}.issubset(sources):
        raise MixReceiptError("narration/music roles required")
    if len({str(p.resolve()) for p in sources.values()}) != len(sources):
        raise MixReceiptError("input paths must be distinct")
    if any(not p.is_file() or p.stat().st_size < 100 for p in sources.values()):
        raise MixReceiptError("input source missing")
    if output.resolve() in {p.resolve() for p in sources.values()}:
        raise MixReceiptError("output may not overwrite inputs")
    if str(output) != command[-1]:
        raise MixReceiptError("output must be last FFmpeg argument")
    declared = [command[i + 1] for i, arg in enumerate(command[:-2])
                if arg == "-i"]
    if (len(declared) != len(sources) or
            set(os.path.realpath(v) for v in declared) !=
            {str(p.resolve()) for p in sources.values()}):
        raise MixReceiptError("FFmpeg -i inputs do not match bound stems")
    if any(v.startswith(("https:", "http:", "pipe:", "concat:", "lavfi:"))
           for v in declared):
        raise MixReceiptError("network and protocol inputs are not allowed")


def execute_with_receipt(episode_id: str, command: list[str],
                         sources: Mapping[str, Path], output: Path,
                         receipt: Path) -> dict[str, Any]:
    if not episode_id.strip():
        raise MixReceiptError("episode ID required")
    sources = {k: p.resolve() for k, p in sources.items()}
    output = output.resolve()
    receipt = receipt.resolve()
    _validate(command, sources, output)
    if output.exists() or receipt.exists():
        raise MixReceiptError("never overwrite completed output or receipt")
    before = {k: file_sha256(p) for k, p in sources.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as folder:
        temporary = Path(folder) / ("mixed" + output.suffix)
        try:
            result = subprocess.run([*command[:-1], str(temporary)],
                                    capture_output=True, timeout=180, check=True)
        except (OSError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired) as exc:
            raise MixReceiptError("real FFmpeg mix failed") from exc
        if not temporary.is_file() or temporary.stat().st_size < 1024:
            raise MixReceiptError("output audio was not generated")
        mixed_pcm = decoded_pcm_sha256(temporary)
        after = {k: file_sha256(p) for k, p in sources.items()}
        if before != after:
            raise MixReceiptError("source bytes changed during FFmpeg execution")
        os.replace(temporary, output)
    data = {
        "algorithm": ALGORITHM,
        "episode_id": episode_id,
        "state": "MIX_EXECUTED_VERIFIED_LOCAL_SOURCE_BYTES",
        "sources": [{"role": name, "path": str(path), "sha256": before[name]}
                    for name, path in sources.items()],
        "ffmpeg_argv": command,
        "ffmpeg_argv_sha256": hashlib.sha256(
            json.dumps(command, separators=(",", ":")).encode()).hexdigest(),
        "ffmpeg_stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        "output": {"path": str(output), "sha256": file_sha256(output),
                   "decoded_mono_48k_s16le_sha256": mixed_pcm,
                   "bytes": output.stat().st_size},
        "replay_verified": False,
        "master_video_verified": False,
        "publication_authorized": False,
        "limits": "FFmpeg invocation is proven; included -i inputs must be verified in the actual filtergraph and final master separately.",
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary_receipt = receipt.with_name(receipt.name + ".pending")
    try:
        temporary_receipt.write_text(json.dumps(data, indent=2) + "\n",
                                     encoding="utf-8")
        os.replace(temporary_receipt, receipt)
    except OSError as exc:
        temporary_receipt.unlink(missing_ok=True)
        raise MixReceiptError("receipt write failed") from exc
    return data


def verify_receipt(receipt: Path, *, replay: bool = True) -> dict[str, Any]:
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
        if data.get("algorithm") != ALGORITHM or data.get("state") != "MIX_EXECUTED_VERIFIED_LOCAL_SOURCE_BYTES":
            raise MixReceiptError("receipt schema is invalid")
        items = data["sources"]
        command = data["ffmpeg_argv"]
        output = Path(data["output"]["path"])
        sources = {item["role"]: Path(item["path"]) for item in items}
        if len(sources) != len(items):
            raise MixReceiptError("duplicate source roles")
        _validate(command, sources, output)
        digest = hashlib.sha256(json.dumps(command, separators=(",", ":")).encode()).hexdigest()
        if digest != data["ffmpeg_argv_sha256"]:
            raise MixReceiptError("FFmpeg argv attestation differs")
        for item in items:
            if file_sha256(Path(item["path"])) != item["sha256"]:
                raise MixReceiptError("source hash mismatch: " + item["role"])
        if file_sha256(output) != data["output"]["sha256"]:
            raise MixReceiptError("mixed output hash mismatch")
        mixed_pcm = decoded_pcm_sha256(output)
        if mixed_pcm != data["output"]["decoded_mono_48k_s16le_sha256"]:
            raise MixReceiptError("mixed audio PCM mismatch")
        if not replay:
            return {"status": "BLOCKED", "replay_verified": False,
                    "reason": "source hashes alone cannot prove reproducible mixing"}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / ("replay" + output.suffix)
            subprocess.run([*command[:-1], str(target)], capture_output=True,
                           timeout=180, check=True)
            if decoded_pcm_sha256(target) != mixed_pcm:
                raise MixReceiptError("replayed audio differs from original mix")
        return {"status": "PASS", "replay_verified": True,
                "sources_verified": len(sources),
                "output_sha256": data["output"]["sha256"],
                "decoded_pcm_sha256": mixed_pcm,
                "master_video_verified": False, "publication_authorized": False}
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, MixReceiptError) as exc:
        return {"status": "BLOCKED", "replay_verified": False,
                "errors": [str(exc)], "master_video_verified": False,
                "publication_authorized": False}
