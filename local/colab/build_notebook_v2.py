"""Builds local/colab/video_prep_v2.ipynb from the tested v1 notebook (background-swap cells) + the v2 steps.
Run from the repo root:  python3 local/colab/build_notebook_v2.py
"""
import json

V1 = "local/colab/video_prep_and_background.ipynb"
OUT = "local/colab/video_prep_v2.ipynb"
RAW = "https://raw.githubusercontent.com/anassajrx/video-editorV/claude/hopeful-clarke-qhnr9z/local/colab"
v1 = {c["id"]: "".join(c["source"]) for c in json.load(open(V1))["cells"]}


def code(cid, s):
    return {"cell_type": "code", "id": cid, "metadata": {"cellView": "form"}, "execution_count": None, "outputs": [],
            "source": s.strip("\n").splitlines(True)}


def md(cid, s):
    return {"cell_type": "markdown", "id": cid, "metadata": {}, "source": s.strip("\n").splitlines(True)}


intro = md("intro", """
# Video prep v2 — Colab ⇄ Claude Code (retakes by Claude, optional Omni Flash + background swap)

Works for **vertical (9:16)** and **horizontal (16:9)** videos. Runtime → Change runtime type → **T4 GPU**.
Drive: put the clip in `My Drive/video-editor/raw footage/`; share `My Drive/video-editor/results/` once as
*Anyone with the link*.

| # | Who | What |
|---|---|---|
| 1 | You | upload the phone clip (+ the mic .m4a if you used one), set **Step 0**, run **Part A** (silences + breaths removed, transcription, list of possible retakes — nothing cut yet) |
| 2 | **Claude Code** | send it the `results/<slug>` link: *"retakes for <slug>"* → Claude picks the best takes and writes `final_cut.json` into that folder |
| 3 | You | run **Part B** (final cut; with `OMNI_FLASH`: ≤15 s clips in `omni/to_omni/`) |
| 4 | You (only with Omni) | edit each clip in Omni Flash, save them in `omni/from_omni/` with the SAME names (`clip_01.mp4` …) |
| 5 | You | run **Part C** (joins Omni clips + your original voice → background swap if ticked → soft grade → `edit.mp4`) |
| 6 | **Claude Code** | *"finish <slug>"* → captions, Purple Room graphics, sounds, face check, render |

No Omni and no background? Skip Parts B and C: after step 2 Claude does everything.
Models: Darija `anaszil/whisper-large-v3-turbo-darija` · EN/FR `openai/whisper-large-v3-turbo` · cut-out MatAnyone 2
(non-commercial licence) + BiRefNet-portrait + LaMa.
""")

settings = code("settings", """
#@title Step 0 · Settings (run this first, every time you open the notebook)
SLUG = "my-video"  #@param {type:"string"}
#@markdown **Exact file names** in `video-editor/raw footage/` (copy them from Drive, extension included).
#@markdown Video (e.g. `IMG_1234.MOV`). Empty = the newest video there.
VIDEO_NAME = ""  #@param {type:"string"}
ROOT = "/content/drive/MyDrive/video-editor"  #@param {type:"string"}
#@markdown Mic recording to use INSTEAD of the phone audio (e.g. `Recording (12).m4a`). Synced automatically
#@markdown (offset + clock drift). Empty = keep the phone audio · `auto` = find the matching recording by itself.
MIC_AUDIO = ""  #@param {type:"string"}

#@markdown ---
#@markdown **Options**
#@markdown Change your clothes etc. in Omni Flash (exports ≤15 s clips after the final cut).
OMNI_FLASH = False  #@param {type:"boolean"}
OMNI_MAX_SECONDS = 15  #@param {type:"number"}
#@markdown Replace the background (MatAnyone 2), after Omni if both are ticked.
CHANGE_BACKGROUND = False  #@param {type:"boolean"}
#@markdown Your AI background image (empty = `results/<slug>/background.png`). Tick if you're still in that image.
BACKGROUND_IMAGE = ""  #@param {type:"string"}
BACKGROUND_HAS_ME = True  #@param {type:"boolean"}
MATTING_SIZE = 1080  #@param [720, 1080] {type:"raw"}
COLOR_MATCH = 0.25  #@param {type:"slider", min:0, max:1, step:0.05}
LIGHT_WRAP = 0.35  #@param {type:"slider", min:0, max:1, step:0.05}
BACKGROUND_BLUR = 1.5  #@param {type:"slider", min:0, max:8, step:0.5}
GRAIN = 1.0  #@param {type:"slider", min:0, max:2, step:0.1}
EDGE_TIGHTEN = 0.0  #@param {type:"slider", min:0, max:0.3, step:0.02}

import os
RES = f"{ROOT}/results/{SLUG}"
if not BACKGROUND_IMAGE:
    BACKGROUND_IMAGE = f"{RES}/background.png"
OUTPUT_SIZE = "1080p"
print("Settings saved. Results folder:", RES)
""")

part_a = code("partA", f"""
#@title Part A · Prep: convert, silences + breaths, transcription (Darija + EN/FR), retake CANDIDATES (≈12–18 min / 5 min of video)
import subprocess, time, json, os
t0 = time.time()
if not subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True).stdout.strip():
    raise SystemExit("No GPU. Runtime → Change runtime type → T4 GPU → Save, then run Step 0 and this cell again.")
from google.colab import drive
drive.mount("/content/drive")
!wget -q -O /content/colab_prep.py {RAW}/colab_prep.py
!wget -q -O /content/mic_sync.py {RAW}/mic_sync.py
flags = f'--slug "{{SLUG}}" --root "{{ROOT}}" --no-retakes --no-grade'
if VIDEO_NAME: flags += f' --video "{{VIDEO_NAME}}"'
if MIC_AUDIO.strip(): flags += f' --mic "{{MIC_AUDIO.strip()}}"'
!cd /content && python colab_prep.py {{flags}}
assert os.path.exists(f"{{RES}}/phrases.json"), "Part A did not finish: read the error above (or send it to Claude)."
meta = json.load(open(f"{{RES}}/meta.json")); meta.update({{"omniFlash": OMNI_FLASH, "backgroundSwapRequested": CHANGE_BACKGROUND, "stage": "waiting-for-claude-retakes"}})
json.dump(meta, open(f"{{RES}}/meta.json", "w"), indent=1)
print(f"\\nPart A done in {{(time.time() - t0) / 60:.1f}} min · {{meta['width']}}x{{meta['height']}} {{meta['orientation']}}")
print(f'''
NEXT → Claude Code: send the link of the folder results/{{SLUG}} with: "retakes for {{SLUG}}"
       Claude writes final_cut.json into that folder.''')
if OMNI_FLASH or CHANGE_BACKGROUND:
    print("       Then come back here and run Part B.")
else:
    print("       No Omni / no background: Claude does the rest, you're done with Colab.")
""")

part_b = code("partB", f"""
#@title Part B · Final cut from Claude's final_cut.json (+ Omni Flash clips) (≈3–5 min)
import os, subprocess
from google.colab import drive
drive.mount("/content/drive")
assert os.path.exists(f"{{RES}}/final_cut.json"), "final_cut.json is not in the folder yet: ask Claude Code for the retakes first."
!wget -q -O /content/colab_cut.py {RAW}/colab_cut.py
flags = f'--slug "{{SLUG}}" --root "{{ROOT}}"' + (f" --omni --omni-max {{OMNI_MAX_SECONDS}}" if OMNI_FLASH else "")
!cd /content && python colab_cut.py {{flags}}
if OMNI_FLASH:
    print(f'''
NEXT → Omni Flash: edit each clip in {{RES}}/omni/to_omni/ (clip_01.mp4, clip_02.mp4, …).
       Save every result in {{RES}}/omni/from_omni/ with the SAME name (clip_01.mp4 …).
       Any clip you don't edit keeps the original. Then run Part C.''')
else:
    print("NEXT → run Part C" + (" (background swap + grade)." if CHANGE_BACKGROUND else " (grade)."))
""")

part_c1 = code("partC1", f"""
#@title Part C1 · Join the Omni Flash clips (only if OMNI_FLASH) + choose the video for the next steps
import os
from google.colab import drive
drive.mount("/content/drive")
!wget -q -O /content/colab_finish.py {RAW}/colab_finish.py
if OMNI_FLASH:
    !cd /content && python colab_finish.py join --slug "{{SLUG}}" --root "{{ROOT}}"
    SWAP_INPUT = f"{{RES}}/edit_omni.mp4"
else:
    SWAP_INPUT = f"{{RES}}/edit_cut.mp4"
assert os.path.exists(SWAP_INPUT), f"Missing {{SWAP_INPUT}} (run Part B first)."
print("Video for the next step:", SWAP_INPUT)
if CHANGE_BACKGROUND:
    import subprocess, json
    meta = json.load(open(f"{{RES}}/meta.json"))
    frame = f"{{RES}}/frame_for_image_ai.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", SWAP_INPUT, "-frames:v", "1", frame], check=True)
    print(f'''Background swap: give {{frame}} to your image AI ("keep the person exactly the same, replace only the background
with [room], same framing, same size {{meta['width']}}x{{meta['height']}}, photorealistic"), save it as {{BACKGROUND_IMAGE}},
then run C2 → C2e. (Without the swap, jump to C3.)''')
""")

swap_md = md("swapmd", """
## Part C2 · Background swap (only if `CHANGE_BACKGROUND`) — run C2 → C2e top to bottom
The cut-out (C2d) is the slow step (~20–40 min for ~3.5 min of video at 1080, about half at 720).
""")
b1 = v1["b1"].replace("#@title B1 · Setup for the background swap (about 1–2 minutes)", "#@title C2 · Setup for the background swap (about 1–2 minutes)")
b2 = v1["b2"].replace("#@title B2 · Helpers (just run this cell)", "#@title C2b · Helpers (just run this cell)")
b3 = v1["b3"].replace("#@title B3 · Load the cut video from Part A", "#@title C2c · Load the video (Omni result or final cut)").replace(
    'src = Path(RES) / "edit.mp4"\nassert src.exists(), f"Can\'t find {src}. Run Part A first."',
    'src = Path(SWAP_INPUT)\nassert src.exists(), f"Can\'t find {src}. Run C1 first."')
assert "Path(SWAP_INPUT)" in b3
b4 = v1["b4"].replace("#@title B4 · Prepare the background", "#@title C2d · Prepare the background")
b4b = v1["b4b"].replace("#@title B4b · Cut you out", "#@title C2d2 · Cut you out")
b5 = v1["b5"].replace("#@title B5 · Put you in the new room", "#@title C2e · Put you in the new room")

part_c3 = code("partC3", """
#@title Part C3 · Soft grade → final edit.mp4 for Claude (≈2–4 min)
import os, shutil
from pathlib import Path
from google.colab import drive
drive.mount("/content/drive")
swapped = bool(CHANGE_BACKGROUND and "out_path" in globals() and Path(str(out_path)).exists())
final_input = str(out_path) if swapped else SWAP_INPUT
if swapped:
    shutil.copy(compare, f"{RES}/compare-background.mp4")
flags = f'--slug "{SLUG}" --root "{ROOT}" --input "{final_input}"' + (" --swapped" if swapped else "") + (" --omni" if OMNI_FLASH else "")
!cd /content && python colab_finish.py finish {flags}
print(f'''
DONE → watch {RES}/preview-720p.mp4 on your phone, then Claude Code: "finish {SLUG}" (same folder link).''')
""")

cells = [intro, settings, part_a, md("bmd", "## Part B · after Claude wrote `final_cut.json`"), part_b,
         md("cmd", "## Part C · after Omni Flash (or right after Part B if you don't use Omni)"), part_c1,
         swap_md, code("c2", b1), code("c2b", b2), code("c2c", b3), code("c2d", b4), code("c2d2", b4b), code("c2e", b5), part_c3]
nb = {"nbformat": 4, "nbformat_minor": 5,
      "metadata": {"colab": {"provenance": [], "gpuType": "T4"}, "accelerator": "GPU",
                   "kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}},
      "cells": cells}
json.dump(nb, open(OUT, "w"), ensure_ascii=False, indent=1)
print(OUT, len(cells), "cells")
