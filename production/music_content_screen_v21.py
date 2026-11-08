"""Read-only FFmpeg spectral triage of an original soundtrack (not a listening certification).

Separates source integrity and measurable features from subjective sounds.
Possible repeating siren sweeps / stingers / speech masking are flagged for
qualified audition; a negative signal *never* proves the absence of sirens,
vocals, rights violations or Content ID claims. No cloud audio model or API.
NumPy is imported only when source screening is actually invoked.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

SR = 11025
DECODER_TIMEOUT = 150

class SourceScreenError(RuntimeError):
    pass

def _sha(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()

def _decode(path: Path):
    import numpy as np
    try:
        proc = subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-i",
            str(path), "-vn", "-ar", str(SR), "-ac", "1",
            "-f", "f32le", "-"], capture_output=True, check=True,
            timeout=DECODER_TIMEOUT)
        samples = np.frombuffer(proc.stdout, dtype="<f4").copy()
        if len(samples) < SR * 4 or len(samples) > SR * 330:
            raise SourceScreenError("decoded source duration outside 4–330 seconds")
        if not np.all(np.isfinite(samples)):
            raise SourceScreenError("nonfinite PCM audio")
        return samples
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SourceScreenError("original audio FFmpeg decode failed") from exc

def analyze_samples(samples) -> dict[str, Any]:
    import numpy as np
    from scipy.signal import stft
    x = np.asarray(samples, dtype="float32")
    if len(x) < SR * 4 or not np.isfinite(x).all():
        raise SourceScreenError("audio must contain at least four seconds of real finite PCM")
    f, t, z = stft(x, fs=SR, nperseg=2048, noverlap=1536,
                   padded=False, boundary=None)
    band = abs(z[(f >= 380) & (f <= 1500)])
    freqs = f[(f >= 380) & (f <= 1500)]
    ridge = freqs[band.argmax(axis=0)]
    tonal = band.max(axis=0) / np.maximum(band.mean(axis=0), 1e-9)
    step = max(1, round(.5 / (t[1] - t[0])))
    width = max(2, round(2.0 / (t[1] - t[0])))
    suspicious = []
    for start in range(0, max(1, len(t) - width), step):
        sample = ridge[start:start+width]
        tone = tonal[start:start+width]
        if len(sample) < width:
            continue
        tonal_fraction = float(np.mean(tone > 7))
        freq_change = float(np.quantile(sample, .9) - np.quantile(sample, .1))
        smoothed = np.convolve(sample, np.ones(5)/5, mode="same")[3:-3]
        median_change = float(np.median(abs(np.diff(smoothed))))
        # This is only a heuristic for repeated glissando-like tonal energy.
        if tonal_fraction > .70 and freq_change > 230 and median_change < 80:
            suspicious.append((float(t[start]), freq_change))
    clusters: list[list[tuple[float, float]]] = []
    for entry in suspicious:
        if not clusters or entry[0] - clusters[-1][-1][0] > 3:
            clusters.append([entry])
        else:
            clusters[-1].append(entry)
    sweeps = [{
        "start_seconds": round(cluster[0][0], 2),
        "end_seconds": round(cluster[-1][0] + 2, 2),
        "max_peak_change_hz": round(max(k[1] for k in cluster), 1),
        "classification": "POSSIBLE_TONAL_SWEEP_MAY_BE_MUSIC_NOT_SIREN",
    } for cluster in clusters if len(cluster) >= 2]
    chunk = SR // 10
    bins = x[:len(x) // chunk * chunk].reshape(-1, chunk)
    rms = np.sqrt(np.mean(bins.astype("float64") ** 2, axis=1))
    floor = max(float(np.quantile(rms, .25)), 1e-6)
    stingers = []
    for i in range(15, len(rms)-15):
        local = float(np.median(rms[i-15:i+16]))
        if rms[i] > max(.006, 8*local, 8*floor):
            if not stingers or i / 10 - stingers[-1] > 1:
                stingers.append(round(i / 10, 1))
    return {
        "duration_seconds": round(len(x)/SR,3),
        "analysis_method": "FFMPEG_DECODE_STFT_BAND_380_1500HZ_PLUS_100MS_RMS",
        "siren_like_tonal_sweep_candidates": sweeps[:40],
        "abrupt_transient_candidates_seconds": stingers[:50],
        "rms_dbfs": round(20*math.log10(max(float(np.sqrt(np.mean(x.astype("float64")**2))),1e-9)),2),
        "source_peak_dbfs": round(20*math.log10(max(float(np.max(abs(x))),1e-9)),2),
        "status": "CANDIDATES_FOR_AUDITION" if sweeps or stingers else
                  "NO_HEURISTIC_CANDIDATES_HUMAN_AUDITION_STILL_REQUIRED",
        "absence_of_sirens_certified": False,
        "absence_of_vocals_certified": False,
        "no_content_id_claim_certified": False,
        "subjective_story_fit_certified": False,
    }

def _ratio_music_voice(music, voice) -> dict[str, Any]:
    """Conservative raw gain estimate, NOT a sidechain/postmix intelligibility test."""
    import numpy as np
    n = min(len(music), len(voice))
    window = SR // 4
    count = n // window
    if count < 4:
        raise SourceScreenError("not enough original voice for segment analysis")
    v = voice[:count*window].reshape(count, window)
    m = music[:count*window].reshape(count, window)
    vr = np.sqrt(np.mean(v.astype("float64")**2, axis=1))
    mr = .12 * np.sqrt(np.mean(m.astype("float64")**2, axis=1))
    active = vr > max(float(np.quantile(vr, .65)), .005)
    if not active.any():
        raise SourceScreenError("no measurable voice-active segments found")
    ratio = 20*np.log10((mr[active]+1e-9)/(vr[active]+1e-9))
    return {
        "method": "RAW_PCM_LEVEL_ESTIMATE_BEFORE_LOUDNORM_AND_SIDECHAIN",
        "original_voice_active_windows": int(active.sum()),
        "music_over_voice_median_db_pre_sidechain": round(float(np.median(ratio)),2),
        "music_within_12db_of_voice_fraction_pre_sidechain": round(float(np.mean(ratio>-12)),3),
        "comprehensibility_verified": False,
        "note": "Cannot certify voice clarity after gain normalization, ducking, mastering or AAC.",
    }

def screen(source: Path, expected_sha: str, *, voice: Path | None = None) -> dict[str, Any]:
    source = Path(source)
    actual = _sha(source)
    if actual != expected_sha:
        raise SourceScreenError("original licensed music bytes differ from pinned SHA-256")
    raw = _decode(source)
    result = analyze_samples(raw)
    result.update({
        "original_source_sha256": actual,
        "original_music_file_bytes": source.stat().st_size,
        "remote_api_requests": 0,
        "new_tts_requests": 0,
        "cost_usd": 0,
        "release_authorized": False,
        "publication_authorized": False,
    })
    if voice is not None:
        result["speech_masking_estimate"] = _ratio_music_voice(raw,_decode(Path(voice)))
    return result

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--music", type=Path, required=True)
    p.add_argument("--expected-sha256", type=str, required=True)
    p.add_argument("--approved-voice", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        result = screen(a.music,a.expected_sha256,voice=a.approved_voice)
    except (OSError, ValueError, SourceScreenError) as exc:
        result = {"status":"BLOCKED_INVALID_SOURCE","failure":str(exc),
                  "release_authorized":False,"publication_authorized":False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return 1 if result["status"] == "BLOCKED_INVALID_SOURCE" else 0

if __name__=="__main__":
    raise SystemExit(main())
