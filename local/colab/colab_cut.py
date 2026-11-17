"""Colab Part B: apply Claude's final cut (+ optional Omni Flash export). Vertical or horizontal.

Usage (inside the notebook, Drive mounted):
  python colab_cut.py --slug my-video [--root ...] [--omni] [--omni-max 15]

Reads   results/<slug>/in.mp4          (written by Part A)
        results/<slug>/final_cut.json  (written by Claude: [[start, end], ...] in SOURCE seconds of in.mp4)
Writes  results/<slug>/edit_cut.mp4    final length, -14 LUFS, NOT graded (the grade comes last, in Part C)
        results/<slug>/segments.json   the kept segments, frame-snapped (what captions are timed against)
        with --omni: results/<slug>/omni/to_omni/clip_01.mp4 ... (each <= --omni-max seconds) + omni/omni_plan.json
Omni clips are split AT EXISTING CUTS (jump cuts the viewer already sees), so the seams between edited clips hide
there. A single uninterrupted take longer than the limit is split at its quietest moment.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np

T0 = time.time()
p = argparse.ArgumentParser()
p.add_argument("--slug", required=True)
p.add_argument("--root", default="/content/drive/MyDrive/video-editor")
p.add_argument("--work", default="/content/work_cut")
p.add_argument("--omni", action="store_true")
p.add_argument("--omni-max", type=float, default=15.0)
args = p.parse_args()
RES = os.path.join(args.root, "results", args.slug)
W = args.work
FPS = 30
SR = 16000
os.makedirs(W, exist_ok=True)
log = lambda m: print(f"[{time.time() - T0:5.0f}s] {m}", flush=True)  # noqa: E731


def sh(cmd, text=True):
    r = subprocess.run(cmd, capture_output=True, text=text)
    if r.returncode != 0:
        err = r.stderr if text else r.stderr.decode("utf8", "replace")
        raise RuntimeError(f"{cmd[0]} failed:\n{err[-3000:]}")
    return r


cut_path = os.path.join(RES, "final_cut.json")
if not os.path.exists(cut_path):
    sys.exit(f"Missing {cut_path}: ask Claude Code for the retakes first (step 3 of the workflow).")
IN = os.path.join(W, "in.mp4")
shutil.copy(os.path.join(RES, "in.mp4"), IN)
cut = json.load(open(cut_path))
if isinstance(cut, dict):
    cut = cut["segments"]
snap = lambda t: round(t * FPS) / FPS  # noqa: E731
segs = [(snap(a), snap(b)) for a, b in cut if snap(b) - snap(a) >= 1 / FPS]
log(f"final cut: {len(segs)} segments, {sum(b - a for a, b in segs):.1f}s")

# ---- render the kept segments (same as render-segments.mjs: frame-snapped, 8 ms fades), no grade ----
parts = os.path.join(W, "parts")
shutil.rmtree(parts, ignore_errors=True)
os.makedirs(parts)
lst = []
for n, (a, b) in enumerate(segs):
    part = os.path.join(parts, f"p{n:04d}.mov")
    sh(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", IN, "-t", f"{b - a:.4f}", "-map", "0:v:0", "-map", "0:a:0",
        "-vf", f"fps={FPS},format=yuv420p", "-frames:v", str(round((b - a) * FPS)), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
        "-af", f"afade=t=in:d=0.008,afade=t=out:st={max(0, b - a - 0.008):.4f}:d=0.008", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", part])
    lst.append(f"file '{part}'")
open(os.path.join(parts, "list.txt"), "w").write("\n".join(lst))
RAWCUT = os.path.join(W, "cut-raw.mp4")
sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(parts, "list.txt"), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", RAWCUT])

# ---- loudness -14 LUFS / limiter (two-pass, nudged) ----
meas = sh(["ffmpeg", "-hide_banner", "-i", RAWCUT, "-af", "loudnorm=I=-14:TP=-1:LRA=7:print_format=json", "-f", "null", "-"]).stderr
J = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
M = f"measured_I={J['input_i']}:measured_TP={J['input_tp']}:measured_LRA={J['input_lra']}:measured_thresh={J['input_thresh']}:offset={J['target_offset']}"
OUT = os.path.join(W, "edit_cut.mp4")
target, lim = -13.5, 0.7
for _ in range(3):
    sh(["ffmpeg", "-v", "error", "-y", "-i", RAWCUT, "-af",
        f"loudnorm=I={target}:TP=-1.5:LRA=9:{M},aresample=192000,alimiter=limit={lim}:attack=1:release=50:level=false,aresample=48000",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT])
    eb = sh(["ffmpeg", "-hide_banner", "-i", OUT, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", eb)[-1])
    if abs(I + 14) <= 0.3:
        break
    target += (-14 - I)
    lim = min(0.85, lim + 0.06)
log(f"edit_cut.mp4: {I:.1f} LUFS")
shutil.copy(OUT, os.path.join(RES, "edit_cut.mp4"))
json.dump([[a, b] for a, b in segs], open(os.path.join(RES, "segments.json"), "w"))

# ---- Omni Flash export: <= omni-max seconds, split at existing cuts ----
if args.omni:
    # output-timeline boundaries of each kept segment
    t, bounds = 0.0, []
    for a, b in segs:
        bounds.append((t, t + (b - a)))
        t += b - a
    total = t
    pcm = sh(["ffmpeg", "-v", "error", "-i", OUT, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"], text=False).stdout
    A = np.frombuffer(pcm, dtype=np.float32)
    db = lambda s, e: 20 * np.log10(np.sqrt((A[int(s * SR):int(e * SR)] ** 2).mean()) + 1e-9)  # noqa: E731
    mx = args.omni_max - 0.2  # margin
    cuts_at = [0.0]
    for s, e in bounds:
        # close the current clip before this segment if adding it would exceed the limit
        if e - cuts_at[-1] > mx and s - cuts_at[-1] > 0.5:
            cuts_at.append(s)
        # a single segment still too long: split it at quiet points
        while e - cuts_at[-1] > mx:
            lo, hi = cuts_at[-1] + mx * 0.6, cuts_at[-1] + mx
            cand = np.arange(lo, hi, 0.02)
            q = min(cand, key=lambda x: db(x - 0.03, x + 0.03))
            cuts_at.append(round(q * FPS) / FPS)
    cuts_at.append(total)
    odir = os.path.join(RES, "omni", "to_omni")
    os.makedirs(odir, exist_ok=True)
    os.makedirs(os.path.join(RES, "omni", "from_omni"), exist_ok=True)
    plan = []
    for k, (a, b) in enumerate(zip(cuts_at, cuts_at[1:]), 1):
        name = f"clip_{k:02d}"
        frames = round((b - a) * FPS)
        dst = os.path.join(odir, f"{name}.mp4")
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", OUT, "-t", f"{b - a:.4f}", "-frames:v", str(frames),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", dst])
        plan.append({"name": name, "startS": round(a, 4), "endS": round(b, 4), "frames": frames})
    info = json.loads(sh(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-select_streams", "v:0", "-of", "json", OUT]).stdout)
    w, h = info["streams"][0]["width"], info["streams"][0]["height"]
    json.dump({"fps": FPS, "width": w, "height": h, "totalS": round(total, 4), "clips": plan},
              open(os.path.join(RES, "omni", "omni_plan.json"), "w"), indent=1)
    lens = [c["endS"] - c["startS"] for c in plan]
    log(f"Omni: {len(plan)} clips ({min(lens):.1f}-{max(lens):.1f}s) in results/{args.slug}/omni/to_omni/")
log(f"Part B done in {(time.time() - T0) / 60:.1f} min")
