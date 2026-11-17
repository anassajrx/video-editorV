"""Pull a Colab prep results folder from Google Drive into the engine (cloud session side).

Usage:
  python3 -I scripts/fetch_colab.py "<Drive folder link of results/<slug>>" <slug>

The folder must be shared "Anyone with the link" (share the parent 'video-editor/results' once; subfolders
inherit it). No Google token needed. Files land in public/videos/<slug>/raw/ (git-ignored):
  edit.mp4 (cut + soft grade + -14 LUFS), in.mp4, phrases.json, second.json, removals.json, segments.json,
  cut.mp4.cuts.json, transcript.txt, report.md, preview-720p.mp4
Then it checks the files and prints the report.
"""
import json
import os
import subprocess
import sys

if len(sys.argv) < 3:
    sys.exit(__doc__)
link, slug = sys.argv[1], sys.argv[2]
dst = os.path.join("public", "videos", slug, "raw")
os.makedirs(dst, exist_ok=True)
r = subprocess.run([sys.executable, "-m", "gdown", "--folder", link, "-O", dst, "--remaining-ok"], text=True)
if r.returncode != 0:
    sys.exit("gdown failed: is the folder shared as 'Anyone with the link'? (pip install gdown if missing)")

# gdown may create a sub-folder named after the Drive folder: flatten it
for root, _, files in os.walk(dst):
    if root == dst:
        continue
    for f in files:
        os.replace(os.path.join(root, f), os.path.join(dst, f))

need = ["edit.mp4", "phrases.json", "second.json", "removals.json", "segments.json", "cut.mp4.cuts.json"]
missing = [f for f in need if not os.path.exists(os.path.join(dst, f))]
if missing:
    sys.exit(f"Missing from the Drive folder: {missing}")
ph = json.load(open(os.path.join(dst, "phrases.json"), encoding="utf8"))
rem = json.load(open(os.path.join(dst, "removals.json"), encoding="utf8"))
print(f"OK: {len(ph['phrases'])} phrases, {len(rem)} auto removals -> {dst}")
rep = os.path.join(dst, "report.md")
if os.path.exists(rep):
    print(open(rep, encoding="utf8").read())
