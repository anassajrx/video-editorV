# Workflow: Google Colab (GPU prep) ⇄ Claude Code cloud session (edit + render)

> **v2 (recommended): `local/colab/video_prep_v2.ipynb`** — Claude picks the retakes; optional Omni Flash (≤15 s clips,
> split at existing cuts) and background swap. Open it:
> https://colab.research.google.com/github/anassajrx/video-editorV/blob/claude/hopeful-clarke-qhnr9z/local/colab/video_prep_v2.ipynb
>
> | Options | Trips |
> |---|---|
> | none | Colab Part A → Claude ("retakes for <slug>", Claude then finishes everything) |
> | background only | Part A → Claude (retakes) → Part B + C → Claude ("finish <slug>") |
> | Omni (± background) | Part A → Claude (retakes) → Part B → Omni Flash → Part C → Claude ("finish <slug>") |
>
> The section below describes v1 (`video_prep_and_background.ipynb`, Colab cuts retakes automatically), kept as is.

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

### A. Colab (the notebook)
1. Upload the clip to `My Drive/video-editor/raw footage/` (from your phone's Drive app is fine). Vertical (9:16) or
   horizontal (16:9) both work: the orientation is detected automatically.
2. Open the notebook directly from GitHub:
   **https://colab.research.google.com/github/anassajrx/video-editorV/blob/claude/hopeful-clarke-qhnr9z/local/colab/video_prep_and_background.ipynb**
   → File → *Save a copy in Drive* (once) → Runtime → Change runtime type → **T4 GPU** → Save.
3. **Step 0**: set `SLUG` (short name), tick/untick `CHANGE_BACKGROUND`. Run Step 0, then **Part A**.
4. Background swap only: give `results/<slug>/frame_for_image_ai.png` to your image AI, save its result as
   `results/<slug>/background.png`, then run **Part B** (B1 → B6, top to bottom).
5. Watch `preview-720p.mp4` (and `compare-background.mp4`) on your phone. Copy the link of the `results/<slug>` folder.

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
| `meta.json` | size, **orientation** (vertical/horizontal), durations, loudness, whether the background was swapped |
| `edit.mp4` | your video: silences + retakes + breaths removed, (new background,) soft grade, -14 LUFS |
| `edit_original_background.mp4`, `compare-background.mp4`, `background_files/` | only with the background swap |
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
