# Workflow: Google Colab (GPU prep) → Claude Code cloud session (edit + render)

No laptop needed. Your phone or any browser is enough.

## Who does what

| Step | Where | Why there |
|---|---|---|
| Convert iPhone video (HEVC/rotation → H.264 30 fps) | **Colab** | mechanical |
| Silence cut | **Colab** | mechanical |
| Darija transcription (per segment + per phrase, word times) | **Colab (T4 GPU)** | GPU: minutes instead of ~1 h |
| English + French pass (foreign words in Latin) | **Colab (T4 GPU)** | GPU |
| Retake / false start / breath detection + cut | **Colab (automatic)** | first pass, editable |
| Soft grade + loudness -14 LUFS + 720p preview | **Colab** | mechanical |
| **Check the retakes Colab found (and the ones it missed)** | **Claude Code — required** | needs understanding of what you said |
| **Write the Darija captions** (real Darija, French/English in Latin, no mixed words) | **Claude Code — required** | Whisper is weak at Darija; needs judgement |
| **Storyboard, graphics, animation moments, music/SFX** | **Claude Code — required** | creative decisions, Purple Room style |
| **Face check (nothing over/above your face)** | **Claude Code — required** | your #1 rule |
| **Render the final video + checks + phone preview** | **Claude Code — required** | Remotion lives there |

## One-time setup (5 min)

1. In Google Drive create: `My Drive/video-editor/raw footage/` and `My Drive/video-editor/results/`.
2. Right-click `results` → **Share** → General access: **Anyone with the link** (Viewer). Do this once; every
   video folder inside inherits it.

## Every video

### A. Colab (~5–10 min for a 5-min clip)
1. Upload the clip to `My Drive/video-editor/raw footage/` (from your phone's Drive app is fine).
2. Open **colab.research.google.com** → New notebook → **Runtime → Change runtime type → T4 GPU** → Save.
3. Paste this in the cell, change `my-video` to a short name, press ▶:
   ```python
   from google.colab import drive; drive.mount('/content/drive')
   !wget -q -O colab_prep.py https://raw.githubusercontent.com/anassajrx/video-editorV/claude/hopeful-clarke-qhnr9z/local/colab/colab_prep.py
   !python colab_prep.py --slug my-video
   ```
   (Allow Drive access when asked. Options: `--video "IMG_1234.MOV"` for a specific clip, `--no-retakes` to only
   detect retakes without cutting them.)
4. When it prints **DONE**, open `My Drive/video-editor/results/my-video/`. You can already watch
   `preview-720p.mp4` (cut + graded + loudness) on your phone.
5. Copy the link of that `my-video` folder (Share → Copy link).

### B. Claude Code cloud session
Start a session on the repo `anassajrx/video-editorV` and send:
```
/darija-video-edit-local Colab prep is done. Results folder: <paste the Drive folder link>. Slug: my-video.
Fetch it with scripts/fetch_colab.py, check the retakes in removals.json against transcript.txt, write the captions,
make the storyboard, then the final video + 720p preview.
```
Add your **script** if you have it (better captions, faster), or **"one shot"** to skip the storyboard approval.

## What Colab writes to `results/<slug>/`

| File | What |
|---|---|
| `edit.mp4` | your video: silences + retakes + breaths removed, soft grade, -14 LUFS |
| `preview-720p.mp4` | small version for the phone |
| `transcript.txt` | every phrase: Arabic / English / French side by side, REMOVED marked |
| `removals.json` | what was cut and why (editable) |
| `phrases.json`, `second.json` | word timings (Darija / EN+FR) for the captions |
| `segments.json`, `cut.mp4.cuts.json` | exactly which parts were kept |
| `in.mp4` | the converted original (needed if Claude must redo a cut) |
| `report.md` | summary: lengths, removals, loudness, time taken |

## If something goes wrong in Colab
- **"No GPU" warning** → Runtime → Change runtime type → T4 GPU, then run again.
- **No T4 available** (busy hours) → try again later; it still runs on CPU but takes much longer.
- **"Darija LoRA failed to load"** → it falls back to plain Whisper large-v3-turbo; captions need more fixing but
  everything else works. Tell Claude Code.
- **Drive not mounted / file not found** → check the clip is in `video-editor/raw footage` (exact folder names).
