"""Automatic QA: proves nothing is drawn over or above the face.

Usage:  python3 scripts/check_face.py <slug>

Renders the edit with qa=true (footage replaced by pure black, so only captions and
graphics are visible) at low resolution, samples 10 frames per second, and checks
that every pixel from the top of the frame down to faceZone.bottom stays black.
Exit code 1 + a list of timestamps if anything enters the face zone.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import cv2
import numpy as np

slug = sys.argv[1]
spec = json.load(open(f"src/videos/{slug}/edit.json", encoding="utf-8"))
fz = spec.get("faceZone")
if not fz:
    print("No faceZone in edit.json. Run: python3 scripts/face_zone.py src/videos/%s/edit.json" % slug)
    sys.exit(1)

tmp = tempfile.mkdtemp()
props = os.path.join(tmp, "props.json")
json.dump({"spec": spec, "qa": True}, open(props, "w", encoding="utf-8"), ensure_ascii=False)
video = os.path.join(tmp, "qa.mp4")
subprocess.run(
    [shutil.which("npx") or "npx", "remotion", "render", slug, video, f"--props={props}", "--scale=0.25", "--muted", "--crf=30", "--log=error"],
    check=True,
)
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video, "-vf", "fps=10", f"{tmp}/%05d.png"], check=True)

# Full-screen animation moments have no face on screen (skill rule 1): they and the captions on top of them are allowed.
FULL = {"momentBlocks", "momentCounter", "momentSlider", "momentCode", "momentFlow", "endCard", "ctaEndCard"}
free = [(o["startMs"] / 1000, o["endMs"] / 1000) for o in spec.get("overlays", []) if o.get("type") in FULL]

bad = []
for f in sorted(x for x in os.listdir(tmp) if x.endswith(".png")):
    img = cv2.imread(os.path.join(tmp, f), cv2.IMREAD_GRAYSCALE)
    h = img.shape[0]
    band = img[: int(h * float(os.environ.get("QA_BAND", fz["bottom"]))), :]
    # >40 luminance = real text/graphic (ignores compression noise and faint glow haze)
    t = (int(f.split(".")[0]) - 1) / 10
    if any(a - 0.05 <= t <= b + 0.35 for a, b in free):
        continue
    if (band > 40).sum() > 3:
        bad.append(t)

if bad:
    print(f"FAIL: something is drawn over/above the face at {len(bad)} sampled moments:")
    print("  " + ", ".join(f"{t:.1f}s" for t in bad[:40]))
    sys.exit(1)
print(f"PASS: nothing drawn in the face zone (0% -> {fz['bottom']*100:.1f}% of frame height).")
