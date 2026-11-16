"""Detect the face area in the footage and write a protected "faceZone" into edit.json.

Usage:  python3 scripts/face_zone.py <edit.json>
        (footage path is read from the spec; it is looked up inside public/)

How it works
- Samples ~1 frame per second, detects the face (OpenCV YuNet model bundled in scripts/models).
- Maps each face box into the OUTPUT frame (object-fit: cover crop + the strongest
  zoom the edit uses: slow push 1.05 x biggest punch-in).
- faceZone.top    = highest point of the face (minus hair margin)
- faceZone.bottom = lowest point of the chin (plus a beard/neck margin)
Captions and graphics are then only allowed BELOW faceZone.bottom (see the darija-video-edit-local skill).
"""
import json
import os
import subprocess
import sys
import tempfile

import cv2

spec_path = sys.argv[1]
spec = json.load(open(spec_path))
vertical = spec.get("orientation", "vertical") == "vertical"
W, H = (1080, 1920) if vertical else (1920, 1080)
src = os.path.join("public", spec["footage"]["src"])

frames = []
if spec["footage"]["kind"] == "image":
    frames.append(cv2.imread(src))
else:
    tmp = tempfile.mkdtemp()
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src, "-vf", "fps=1", f"{tmp}/%04d.jpg"], check=True)
    frames = [cv2.imread(os.path.join(tmp, f)) for f in sorted(os.listdir(tmp))]

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "face_detection_yunet_2023mar.onnx")
max_punch = max([p["scale"] for p in spec.get("punchIns", [])] + [1.0])
zooms = [1.0, 1.05 * max_punch]

top, bottom, found = 1.0, 0.0, 0
for img in frames:
    if img is None:
        continue
    sh, sw = img.shape[:2]
    det = cv2.FaceDetectorYN.create(MODEL, "", (sw, sh), 0.7)
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        continue
    x, y, w, h = max(faces[:, :4].tolist(), key=lambda f: f[2] * f[3])
    found += 1
    # Detector boxes cut the hair and stop at the chin: extend both ways.
    y0 = y - 0.35 * h  # hair
    y1 = y + 1.12 * h  # chin + beard
    s0 = max(W / sw, H / sh)
    off = (sh * s0 - H) / 2
    for k in zooms:
        for yy, is_top in ((y0, True), (y1, False)):
            out = H / 2 + ((yy * s0 - off) - H / 2) * k
            if is_top:
                top = min(top, out / H)
            else:
                bottom = max(bottom, out / H)

if not found:
    print("No face detected. Set faceZone manually in edit.json after checking a still.")
    sys.exit(1)

margin = 0.025
spec["faceZone"] = {"top": round(max(0.0, top - margin), 3), "bottom": round(min(1.0, bottom + margin), 3)}
json.dump(spec, open(spec_path, "w"), indent=2)
print(f"Face found in {found}/{len(frames)} frames. faceZone = {spec['faceZone']}")
if spec["faceZone"]["bottom"] > 0.62:
    print("WARNING: face reaches low in the frame; little room for captions. Consider reframing or smaller punch-ins.")
