"""Colab Part C helpers: join the Omni Flash clips, and finish (soft grade -> edit.mp4). Vertical or horizontal.

  python colab_finish.py join   --slug my-video [--root ...]
      reads results/<slug>/omni/omni_plan.json + omni/from_omni/clip_XX.* (any video format Omni gives back)
      each clip is conformed to the original size / 30 fps / EXACT frame count (trimmed, or last frame held), joined,
      and YOUR ORIGINAL VOICE from edit_cut.mp4 is put back (Omni regenerates the audio).
      A missing clip falls back to the original one (so you can edit only some clips).
      -> results/<slug>/edit_omni.mp4
  python colab_finish.py finish --slug my-video --input <path> [--swapped] [--omni]
      soft grade (approved 2026-11-16) on the video, audio copied (already -14 LUFS) -> results/<slug>/edit.mp4,
      720p preview, meta.json + report.md updated. This edit.mp4 is what Claude Code animates.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

T0 = time.time()
p = argparse.ArgumentParser()
p.add_argument("mode", choices=["join", "finish"])
p.add_argument("--slug", required=True)
p.add_argument("--root", default="/content/drive/MyDrive/video-editor")
p.add_argument("--work", default="/content/work_finish")
p.add_argument("--input", default="")
p.add_argument("--swapped", action="store_true")
p.add_argument("--omni", action="store_true")
args = p.parse_args()
RES = os.path.join(args.root, "results", args.slug)
W = args.work
os.makedirs(W, exist_ok=True)
log = lambda m: print(f"[{time.time() - T0:5.0f}s] {m}", flush=True)  # noqa: E731
GRADE = ("hqdn3d=2:2:3:3,curves=all='0/0 0.25/0.22 0.6/0.61 1/0.98',eq=saturation=1.05,"
         "colorbalance=rs=0.02:bs=0.05:bm=0.02,unsharp=5:5:0.3,vignette=PI/7")


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{r.stderr[-3000:]}")
    return r


def frames_of(path):
    return int(sh(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                   "-of", "csv=p=0", path]).stdout.strip())


if args.mode == "join":
    plan = json.load(open(os.path.join(RES, "omni", "omni_plan.json")))
    w, h, fps = plan["width"], plan["height"], plan["fps"]
    src_dir, orig_dir = os.path.join(RES, "omni", "from_omni"), os.path.join(RES, "omni", "to_omni")
    lst, used = [], 0
    for c in plan["clips"]:
        got = [f for f in glob.glob(os.path.join(src_dir, c["name"] + ".*")) if not f.endswith(".json")]
        src = got[0] if got else os.path.join(orig_dir, c["name"] + ".mp4")
        used += bool(got)
        if not got:
            log(f"!! {c['name']}: no Omni version in from_omni/, using the original clip")
        dst = os.path.join(W, c["name"] + ".mp4")
        n = c["frames"]
        # conform: fill the original frame (no black bars), 30 fps, exactly n frames (hold the last frame if short)
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},fps={fps},"
              f"tpad=stop_mode=clone:stop_duration=2,format=yuv420p")
        sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-an", "-vf", vf, "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "15", dst])
        got_n = frames_of(dst)
        if got_n != n:
            raise SystemExit(f"{c['name']}: {got_n} frames instead of {n}")
        lst.append(f"file '{dst}'")
    # join frame by frame through one encoder: every frame of every clip, in order (a concat by timestamps can
    # drop frames at the seams -> captions would drift)
    vid = os.path.join(W, "video.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{w}x{h}", "-r", str(fps),
                            "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-pix_fmt", "yuv420p", vid],
                           stdin=subprocess.PIPE)
    for line in lst:
        clip = line[len("file '"):-1]
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", clip, "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"], stdout=subprocess.PIPE)
        while True:
            buf = dec.stdout.read(1 << 22)
            if not buf:
                break
            enc.stdin.write(buf)
        dec.wait()
    enc.stdin.close()
    if enc.wait() != 0:
        raise SystemExit("joining the clips failed")
    out = os.path.join(W, "edit_omni.mp4")
    sh(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", os.path.join(RES, "edit_cut.mp4"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-c:a", "copy", "-movflags", "+faststart", out])  # no -shortest: the voice track can be ~0.1 s shorter
    a, b = frames_of(out), frames_of(os.path.join(RES, "edit_cut.mp4"))
    if a != b:
        raise SystemExit(f"Joined video has {a} frames, edit_cut.mp4 has {b}: not saving (captions would drift).")
    shutil.copy(out, os.path.join(RES, "edit_omni.mp4"))
    log(f"edit_omni.mp4: {used}/{len(plan['clips'])} clips from Omni Flash, {a} frames = edit_cut.mp4, original voice")
    sys.exit(0)

# ---- finish ----
src = args.input or os.path.join(RES, "edit_cut.mp4")
graded = os.path.join(W, "edit.mp4")
sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", GRADE + ",format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "copy", "-movflags", "+faststart", graded])
cut_frames = frames_of(os.path.join(RES, "edit_cut.mp4"))
if frames_of(graded) != cut_frames:
    raise SystemExit("Frame count differs from edit_cut.mp4: not saving.")
shutil.copy(graded, os.path.join(RES, "edit.mp4"))
short720 = "scale='if(gt(iw,ih),-2,720)':'if(gt(iw,ih),720,-2)'"
sh(["ffmpeg", "-v", "error", "-y", "-i", graded, "-vf", short720, "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1100k", "-maxrate", "1300k",
    "-bufsize", "2600k", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", os.path.join(RES, "preview-720p.mp4")])
eb = sh(["ffmpeg", "-hide_banner", "-i", graded, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", eb)[-1])
dur = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", graded]).stdout)
mp = os.path.join(RES, "meta.json")
meta = json.load(open(mp)) if os.path.exists(mp) else {}
meta.update({"graded": True, "retakesApplied": True, "finalCutBy": "Claude (final_cut.json)", "omniFlash": args.omni,
             "backgroundSwapped": args.swapped, "finalDurationS": round(dur, 3), "lufs": lufs, "stage": "ready-for-claude"})
json.dump(meta, open(mp, "w"), indent=1)
with open(os.path.join(RES, "report.md"), "a", encoding="utf8") as f:
    f.write(f"\n## Final video for Claude (workflow v2)\n- Final cut from `final_cut.json`, {dur:.1f} s, {lufs:.1f} LUFS, soft grade\n"
            f"- Omni Flash: {'yes' if args.omni else 'no'} · background swap: {'yes' if args.swapped else 'no'}\n")
log(f"edit.mp4 ready: {dur:.1f}s, {lufs:.1f} LUFS, graded (Omni: {args.omni}, background: {args.swapped})")
