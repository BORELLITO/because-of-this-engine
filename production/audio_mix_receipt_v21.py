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
    if len(sources) > 24:
        raise MixReceiptError("too many audio stems for verified replay")
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
        # Counterfactual proof: every listed stem must measurably influence
        # the decoded output. A listed -i source that never reaches [out]
        # must not obtain an apparently valid mix receipt.
        contributions = []
        with tempfile.TemporaryDirectory() as folder:
            for role, original in sources.items():
                probe = subprocess.run([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(original)],
                    capture_output=True, text=True, timeout=25, check=True)
                seconds = float(probe.stdout.strip())
                if not 0 < seconds < 3600:
                    raise MixReceiptError("stem duration not independently verified: " + role)
                silent = Path(folder) / ("silence-" + str(len(contributions)) + ".wav")
                subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
                                "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                                "-t", str(seconds), "-c:a", "pcm_s16le", str(silent)],
                               capture_output=True, timeout=90, check=True)
                alternate = list(command)
                replaced = False
                for pos, value in enumerate(alternate[:-1]):
                    if value == "-i" and pos + 1 < len(alternate) and (
                            os.path.realpath(alternate[pos + 1]) == str(original.resolve())):
                        alternate[pos + 1] = str(silent)
                        replaced = True
                        break
                if not replaced:
                    raise MixReceiptError("stem not in FFmpeg input argv: " + role)
                counterfactual = Path(folder) / ("without-" + str(len(contributions)) + output.suffix)
                subprocess.run([*alternate[:-1], str(counterfactual)], capture_output=True,
                               timeout=180, check=True)
                if decoded_pcm_sha256(counterfactual) == mixed_pcm:
                    raise MixReceiptError("stem has no measured contribution to output mix: " + role)
                contributions.append(role)
        return {"status": "PASS", "replay_verified": True,
                "source_contributions_confirmed": contributions,
                "sources_verified": len(sources),
                "output_sha256": data["output"]["sha256"],
                "decoded_pcm_sha256": mixed_pcm,
                "master_video_verified": False, "publication_authorized": False}
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, MixReceiptError) as exc:
        return {"status": "BLOCKED", "replay_verified": False,
                "errors": [str(exc)], "master_video_verified": False,
                "publication_authorized": False}


def verify_master_binding(receipt: Path, master_video: Path) -> dict[str, Any]:
    """Read-only postflight gate: independently replay mix and match AAC master."""
    from production.audio_acoustic_fingerprint_v21 import compare, fingerprint
    result = verify_receipt(receipt, replay=True)
    if result["status"] != "PASS":
        return {"status": "BLOCKED", "reason": "mix receipt replay was not verified",
                "receipt_result": result, "publication_authorized": False}
    try:
        record = json.loads(receipt.read_text(encoding="utf-8"))
        master = master_video.resolve()
        if not master.is_file() or master.stat().st_size < 1024:
            raise MixReceiptError("final video master is not present")
        mix = Path(record["output"]["path"])
        similarity = compare(fingerprint(mix), fingerprint(master))
        if similarity["similarity"] < 0.94:
            raise MixReceiptError("master audio does not match verified mixed audio")
        return {"status": "PASS", "source_contributions_confirmed":
                result["source_contributions_confirmed"],
                "mix_replay_verified": True, "master_video_sha256": file_sha256(master),
                "acoustic_similarity": similarity["similarity"],
                "master_audio_bound": True, "publication_authorized": False,
                "scope": "POSTFLIGHT_AUDIO_PROVENANCE_ONLY"}
    except (OSError, ValueError, KeyError, TypeError, MixReceiptError) as exc:
        return {"status": "BLOCKED", "master_audio_bound": False,
                "errors": [str(exc)], "publication_authorized": False}
