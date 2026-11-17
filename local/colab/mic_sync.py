"""Replace a phone video's audio with a separately recorded mic file, synced automatically (offset + clock drift).

Library:  from mic_sync import sync_mic;  report = sync_mic(video_mp4, mic_file, out_mp4)
CLI:      python mic_sync.py <video.mp4> <mic.wav|m4a|mp3|...> <out.mp4>

How: both tracks are band-passed (voice, 300-3000 Hz) and compared at 8 kHz.
  1. global offset: FFT cross-correlation of the whole recordings (works whichever device started first)
  2. drift: the offset is measured again on ~20 s windows along the video; a straight-line fit gives offset + speed
     difference between the phone and PC clocks (typically 10-100 ppm = up to ~30 ms over 5 min)
  3. the mic track is trimmed/padded and time-stretched (atempo) onto the video timeline, 48 kHz stereo, same length
  4. verification: the offset is re-measured on the result; it must stay within 15 ms everywhere, else it stops
The video stream is copied (no re-encode).
"""
import json
import subprocess
import sys

import numpy as np

SR = 8000


def _pcm(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-af", "highpass=f=300,lowpass=f=3000", "-f", "f32le",
                        "-ar", str(sr), "-ac", "1", "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"cannot read audio from {path}: {r.stderr.decode()[-500:]}")
    x = np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)
    return x / (np.std(x) + 1e-9)


def _xcorr_lag(a, b, max_lag=None):
    """Lag L (samples) such that b[n + L] ~ a[n]; returns (L, peak strength = peak / median of |corr|)."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    c = np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)
    c = np.abs(np.concatenate([c[-(len(a) - 1):], c[:len(b)]]))  # lags -(len(a)-1) .. len(b)-1
    lags = np.arange(-(len(a) - 1), len(b))
    if max_lag is not None:
        keep = np.abs(lags) <= max_lag
        c, lags = c[keep], lags[keep]
    i = int(np.argmax(c))
    return int(lags[i]), float(c[i] / (np.median(c) + 1e-9))


def _local_offsets(v, m, a0, b, win=20.0, step=None):
    """Offset (s) of mic vs video at windows along the video, searching +-0.5 s around offset(t) = a0 + b*t."""
    step = step or win
    pts = []
    t = 5.0
    while t + win < len(v) / SR - 1:
        seg = v[int(t * SR):int((t + win) * SR)]
        guess = t + a0 + b * t
        lo = int((guess - 0.5) * SR)
        if lo < 0 or lo + len(seg) + SR > len(m):
            t += step
            continue
        ref = m[lo:lo + len(seg) + SR]
        lag, strength = _xcorr_lag(seg, ref, max_lag=len(ref))
        if strength > 6:
            pts.append((t, (lo + lag) / SR - t, strength))
        t += step
    return pts


def sync_mic(video, mic, out, verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    v, m = _pcm(video), _pcm(mic)
    lag, strength = _xcorr_lag(v, m)
    a0 = lag / SR  # mic time = video time + a0
    log(f"mic sync: global offset {a0:+.3f}s (mic {'started earlier' if a0 > 0 else 'started later'}), match strength {strength:.0f}")
    if strength < 8:
        raise RuntimeError("The mic recording does not match the video's sound (is it the same take?). Not replacing the audio.")
    pts = _local_offsets(v, m, a0, 0.0, win=10.0, step=8.0)
    b = 0.0
    if len(pts) >= 3:
        t_, off_ = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
        b, a0 = np.polyfit(t_, off_, 1)
        resid = off_ - (a0 + b * t_)
        good = np.abs(resid) < 0.01
        if good.sum() >= 3:
            b, a0 = np.polyfit(t_[good], off_[good], 1)
    if abs(b) > 1e-3:  # real phone/PC clock drift is < ~300 ppm: anything bigger means a different recording
        raise RuntimeError(f"implausible clock drift ({b * 1e6:+.0f} ppm): this audio is not from the same take")
    log(f"mic sync: offset {a0:+.4f}s, clock drift {b * 1e6:+.0f} ppm ({b * len(v) / SR * 1000:+.1f} ms over the video), "
        f"{len(pts)} check points")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout)
    # mic time tm = a0 + (1 + b) * t  ->  start the mic at a0 and play it (1+b) times faster
    pre = f"adelay={int(round(-a0 * 1000))}|{int(round(-a0 * 1000))}," if a0 < 0 else ""
    trim = f"atrim=start={a0:.5f},asetpts=PTS-STARTPTS," if a0 > 0 else ""
    tempo = f"atempo={1 + b:.8f}," if abs(b) > 2e-6 else ""
    af = f"aresample=48000,{trim}{pre}{tempo}apad,atrim=0:{dur:.5f},aformat=channel_layouts=stereo"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", mic, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                        "-af", af, "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", out], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("mic mux failed: " + r.stderr[-1500:])
    # verify on the result: the new track must line up with the phone's own sound everywhere
    new = _pcm(out)
    chk = _local_offsets(v, new, 0.0, 0.0, win=10.0, step=15.0)
    errs = [abs(p[1]) * 1000 for p in chk]
    worst = max(errs) if errs else None
    log(f"mic sync check: {len(chk)} points, worst error {worst:.1f} ms" if errs else "mic sync check: no check points (clip too short?)")
    if errs and worst > 15:
        raise RuntimeError(f"Sync check failed (worst error {worst:.0f} ms). Keeping the phone audio.")
    return {"offsetS": round(float(a0), 4), "driftPpm": round(float(b * 1e6), 1), "matchStrength": round(strength, 1),
            "checkPoints": len(chk), "worstErrorMs": None if worst is None else round(worst, 1)}


if __name__ == "__main__":
    print(json.dumps(sync_mic(*sys.argv[1:4]), indent=1))
