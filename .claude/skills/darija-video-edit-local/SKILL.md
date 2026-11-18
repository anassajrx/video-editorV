---
name: darija-video-edit-local
description: Edit Anass's Moroccan Darija talking-head videos on THIS computer, in the "Purple Room" style, from a file in "raw footage/" to a finished vertical MP4 + Arabic SRT in "results/". Covers one-time setup, the full edit pipeline (silences, ALL retakes, loudness, soft grade, Darija captions with foreign words kept in their original language, Purple Room graphics, music/SFX, face rule, render) and every known pitfall. Use it whenever the user asks to edit a video in the "video editor" folder.
---

# Darija video edit — LOCAL machine, "Purple Room" style

You are running in the user's **video editor** folder on their own computer. Everything stays on this machine.
This file is the single source of truth: follow it in order and do not improvise around it.

```
video editor/                  <- your working directory (paths contain SPACES: always quote them)
├── references/                <- style references (storyboards, reference videos). Read-only.
├── raw footage/               <- the user drops raw clips here. Read-only: never edit or delete.
├── results/                   <- deliverables, one folder per video: results/<slug>/
├── engine/                    <- the editing engine (git clone of anassajrx/video-editorv). Created by setup.
└── .claude/skills/darija-video-edit-local/SKILL.md   <- this file
```

---

## 0. Non-negotiables (the user's rules)

1. **Nothing over or above the face.** Captions and graphics live below the chin. `check_face.py` must print PASS before
   anything is sent. (Full-screen animation moments have no face on screen, so they are allowed.)
2. **Every retake is removed.** Keep only the LAST complete take of every sentence. Remove false starts, stutters,
   lone fillers (euh, emm), breaths. If the user says "cut", "3awd" or "mn jdid", remove that word and the take before it.
3. **Never cut mid-word.** Every cut lands in a real energy valley (`cut_points.py`).
4. **Captions = what was actually said, in Darija, Arabic letters.** Never translate to MSA, never "correct" Darija.
5. **Foreign words stay in their ORIGINAL language and Latin letters**: `flight`, `website`, `freelance`, `hard code`,
   `la différence`, `la personnalisation`, `besoin spécifique`, `impossible`, `implémenter`, `logique`, `no code`.
   Brand/tool names Latin too (ChatGPT, Claude, GitHub). Arabic prefixes are a separate word: `الـ website`, `فالـ cloud`.
6. **Style = Purple Room (section 6).** No orange, no blue, no cut-out of the background, no Cairo font.
7. **Gates:** send the **storyboard image** (section 6.4) and wait for "ok" before rendering, unless the user says
   "one shot". Always look at stills yourself and run the face check, even in one-shot mode.
8. **Keep the user informed:** one line of status (step, %, ETA) whenever a step runs more than a minute.
9. **Time budget:** a 1-minute clip should take ~20–25 min end to end (~12–15 min if the user gives the script).
   If any step fails twice, stop, use the best result you have, flag it in the report, and move on.

---

## 1. One-time setup (first run only, ~15 min; skip if `engine/` exists and `engine/node_modules` exists)

### 1.1 Tools (Windows)
Claude Code on Windows runs its shell commands in **Git Bash**, so the bash commands in this file work as written.
Check each tool, install only what is missing (`winget` may open a Windows permission prompt: tell the user to click Yes):

| Tool | Check | Install |
|---|---|---|
| Git for Windows (+ Git Bash) | `git --version` | `winget install --id Git.Git -e` |
| Node.js 22 LTS | `node -v` (needs 20.19+ / 22.13+) | `winget install --id OpenJS.NodeJS.LTS -e` |
| Python 3.12 | `py -3.12 --version` | `winget install --id Python.Python.3.12 -e` |
| FFmpeg (+ ffprobe) | `ffmpeg -version` | `winget install --id Gyan.FFmpeg -e` |

After installing, the PATH only updates in NEW terminals: ask the user to close and reopen the terminal and restart
`claude` in the `video editor` folder, then continue. Use `python` from the venv (never the Microsoft Store `python`).

### 1.2 Engine
```bash
git clone https://github.com/anassajrx/video-editorV.git engine   # public repo: no GitHub login needed
cd engine
npm ci
py -3.12 -m venv .venv && source .venv/Scripts/activate  # activate again in every new shell: source .venv/Scripts/activate
python -m pip install -U pip && pip install -r requirements.txt
npx tsc --noEmit
```
- In this file, `python3` means the venv's `python` on Windows: always `source .venv/Scripts/activate` first.
- First run downloads models: faster-whisper `large-v2` (~3 GB, `~/.cache/huggingface`) and whisper.cpp `large-v3`
  (~3 GB, `engine/.whisper/`, binary `.whisper/main.exe`). Needs ~12 GB free disk. Warm them up once:
  `npm run transcribe -- public/videos/brand-demo/<any short clip or 10 s test file> /tmp/t.json --lang=ar`
  (or the first real video does it).
- Remotion downloads its own headless Chrome on the first render (~150 MB).
- Update the engine at the start of every session: `git -C engine pull --no-edit` (merges updates with your local commits; if it reports a conflict, keep the local version of `src/videos/` and the remote version of everything else).
- The master copy of THIS skill and the style references live in the engine. After every pull, refresh them:
  `cp engine/.claude/skills/darija-video-edit-local/SKILL.md .claude/skills/darija-video-edit-local/SKILL.md`
  and `cp engine/local/style/* references/`. If the user edits this skill locally, copy it back into the engine and
  commit it locally, so a pull never overwrites it silently.
- Keep the `video editor` folder OUT of OneDrive-synced folders if possible (sync locks files during renders).

### 1.3 Purple Room components (only if missing)
Check `engine/src/components/purple/`. If it does not exist, the engine predates this style: build the pieces in
section 6.3 first, register them in `src/brand/types.ts` + `EditTemplate.tsx`, run `npx tsc --noEmit`, render one still of
each, commit `purple-room: components` locally (do NOT push: this PC is not logged in to GitHub). This is a one-time job (~45 min).

---

## 1.4 Cloud + Colab workflow (the default since 2026-11-17)
The user works from a **Claude Code cloud session** + **Google Colab (T4 GPU)**, no laptop. Full guide:
`local/COLAB-WORKFLOW.md`. Colab runs `local/colab/colab_prep.py` (convert, silence cut, Darija transcription with
`anaszil/whisper-large-v3-turbo-darija`, EN/FR pass, automatic retakes, soft grade, loudness, 720p preview) and writes
to `My Drive/video-editor/results/<slug>/`. In the cloud session:
1. `pip install gdown` if missing, then `python3 -I scripts/fetch_colab.py "<Drive folder link>" <slug>`
   (files land in `public/videos/<slug>/raw/`; `in.mp4` + `cut.mp4.cuts.json` = Colab's, keep them).
2. Read `transcript.txt` (AR / EN / FR per phrase, REMOVED marked) and **review `removals.json`**: Colab only finds
   near-identical repeats; add missed retakes/false starts, delete wrong ones. If you change anything, rebuild with
   `build_cut.py` + `render-segments.mjs` from `in.mp4`, then §5.1 + §5.2. Otherwise use Colab's `edit.mp4` as is.
   Colab now runs the notebook `local/colab/video_prep_and_background.ipynb` (Part A = `colab_prep.py`, Part B =
   optional background swap with MatAnyone 2, graded after the swap). Read `meta.json` first: `orientation`
   (vertical 1080x1920 or horizontal 1920x1080) sets `edit.json` `orientation`; `backgroundSwapped` tells whether
   `edit.mp4` already has the new room. If you re-cut from `in.mp4` after a swap, the swap is lost: tell the user to
   re-run Part B instead.
3. Skip §2–§5 and the transcription in §7.1: go straight to captions (§7.2–7.3, pin Latin-only pages with `@start-end`
   from `second.json`), graphics, QA, render (§8–§9). Deliver the MP4 + a 720p preview (≤ 30 MB, for the phone).

## 1.5 Workflow v2: Claude picks the retakes (notebook `local/colab/video_prep_v2.ipynb`, the default)
Colab never cuts retakes any more: choosing the best take needs understanding. `meta.json` says which options the user
ticked (`omniFlash`, `backgroundSwapRequested`) and the `stage`.
- **"retakes for <slug>" + folder link** (stage `waiting-for-claude-retakes`):
  1. `python3 -I scripts/fetch_colab.py "<link>" <slug>` (Part A output: in.mp4, phrases.json, second.json, removals.json =
     Colab's candidates only, cut.mp4.cuts.json, transcript.txt).
  2. Read `transcript.txt` (AR/EN/FR per phrase) like §4.2: keep the last COMPLETE take of each sentence, drop false starts,
     restarts, "3awd/mn jdid", rephrases; check cut points with `cut_points.py` (§4.3). Write `removals.json`, run
     `build_cut.py ... --phrases=` → `segments.json`.
  3. **If `omniFlash` or `backgroundSwapRequested`**: upload `segments.json` as **`final_cut.json`** into the SAME Drive
     folder with the Google Drive connector (`create_file`, `parentId` = the folder id from the link, `textContent` = the
     JSON, `contentMimeType` "application/json", `disableConversionToGoogleType` true). If the connector can't write there,
     send the file to the user to drop in. Tell the user: run Part B (and Omni, then Part C), then say "finish <slug>".
     Show the removal table (ORIGINAL clip times + reason) and flag best-guess decisions.
  4. **Neither option**: do the cut here (`render-segments.mjs` from in.mp4 → §5.1 loudness → §5.2 soft grade → edit.mp4)
     and continue straight to captions/graphics/render (no more Colab).
- **"finish <slug>" + folder link** (stage `ready-for-claude`): fetch again (now `edit.mp4` = final length, Omni + new
  background if chosen, graded, -14 LUFS; `segments.json` = the final cut). Do NOT re-cut: retake changes now mean
  re-running Colab Part B/C. Then captions (§7, timed with phrases.json + segments.json), graphics, `fetch_sfx.py` +
  `auto_sfx.py`, face check, render, final limiter, 720p preview, `.srt`.
- **Separate mic audio** (user records with a PC mic, Windows Sound Recorder .m4a, next to the phone video):
  Colab Part A (`MIC_AUDIO = "auto"` or a file name) syncs it automatically (`local/colab/mic_sync.py`: offset by
  cross-correlation + clock drift fit, verified ≤15 ms everywhere, wrong/older recordings rejected) and REPLACES the phone
  audio before anything else, so transcription, cuts and loudness all use the mic. `meta.json` → `micAudio` reports it.
- Omni clips are split at existing cuts (≤15 s); `colab_finish.py join` conforms them to exact frames and puts the
  original voice back; it refuses to save if the frame count changes (captions would drift).

## 2. Intake (per video)

1. Find the clip in `"raw footage/"` (newest file unless the user names one). Pick a short kebab-case **slug** from the
   topic (e.g. `code-vs-nocode`).
2. Inspect it:
   ```bash
   ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate:stream_side_data=rotation -of compact "raw footage/<file>"
   ```
   iPhone `.MOV` = HEVC with `rotation=90`: ffprobe says 1920x1080 but it is really vertical. Grab a frame and LOOK:
   `ffmpeg -ss 5 -i "raw footage/<file>" -frames:v 1 -vf scale=360:-1 results/<slug>/frame.jpg`
3. Copy (never move) into the engine and convert to constant-30fps H.264 (fixes HEVC, rotation, VFR):
   ```bash
   mkdir -p engine/public/videos/<slug>/raw "results/<slug>"
   ffmpeg -i "raw footage/<file>" -map 0:v:0 -map 0:a:0 -vf "fps=30,format=yuv420p" -c:v libx264 -preset veryfast \
     -crf 16 -c:a aac -b:a 192k -ar 48000 engine/public/videos/<slug>/raw/in.mp4
   ```
4. From here on, work inside `engine/` (`cd engine`). `R=public/videos/<slug>/raw`.

## 3. Silence cut

```bash
npm run cut -- $R/in.mp4 $R/cut.mp4 --noise=-38dB --min=0.3 --pad=0.1
```
- Quiet phone audio (≈ -28 LUFS): `-38dB` works. Loud/close-mic audio (≈ -15 LUFS) with room noise: **ffmpeg's
  silencedetect can find NO pauses at all** (it uses sample peaks). If it reports "Kept 1 segments", measure 20 ms RMS
  in Python instead: runs below -32 dB lasting ≥ 0.3 s are pauses; keep 0.08 s padding; write
  `$R/cut.mp4.cuts.json` as `{"input":..., "cuts":[{"sourceStart":s,"sourceEnd":e,"outStartMs":o}, ...]}`.

## 4. Retakes (the step that failed on video 1)

### 4.1 Transcribe per segment and per phrase — never whole-file
```bash
python3 -I scripts/darija/transcribe_phrases.py $R/in.mp4 $R/cut.mp4.cuts.json $R/phrases.json
```
A whole-file transcript merges repeated sentences into one copy, so retakes become invisible.

### 4.2 Decide
- Two lines saying (almost) the same thing → retake: remove the first, keep the last complete one.
- A line that stops and restarts → false start. A rephrase with no pause → still a retake (cut at the closure dip).
- `JUNK` segments (0.2–0.5 s, "اشتركوا في القناة", "شكرا", empty) are breaths/noise: remove (`--phrases` does it).
- A loud wordless stretch may hold words Whisper skipped: check it before cutting.

### 4.3 Cut points, build, render from the original
```bash
python3 -I scripts/darija/cut_points.py $R/in.mp4 <t1> <t2> ...        # valley ≤ -45 dB, else closure dip ≈ -37 dB
# write $R/removals.json: [{"s":0.0,"e":3.3,"reason":"retake: first '...'"}]  ([] if none)
python3 -I scripts/darija/build_cut.py $R/cut.mp4.cuts.json $R/removals.json $R/segments.json --phrases=$R/phrases.json
node scripts/render-segments.mjs $R/in.mp4 $R/segments.json $R/edit-raw.mp4
```
### 4.4 Verify: re-transcribe the start, the end and each retake spot of `edit-raw.mp4`; every line must appear once.

## 5. Loudness, then the soft grade

### 5.1 Loudness: -14 LUFS ± 0.3, true peak ≤ -1 dBTP (two-pass + oversampled limiter)
```bash
J=$(ffmpeg -hide_banner -i $R/edit-raw.mp4 -af loudnorm=I=-14:TP=-1:LRA=7:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
M=$(echo "$J" | python3 -c "import json,sys;d=json.load(sys.stdin);print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
ffmpeg -y -i $R/edit-raw.mp4 -af "loudnorm=I=-13.5:TP=-1.5:LRA=7:$M,aresample=192000,alimiter=limit=0.7:attack=1:release=50:level=false,aresample=48000" -c:v copy -c:a aac -b:a 192k $R/edit-loud.mp4
ffmpeg -hide_banner -i $R/edit-loud.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2
```
If I is off, nudge loudnorm `I` (e.g. -12.4 or -12) and the limiter (0.7 → 0.83) and rerun. Two tries max.

### 5.2 Soft grade (approved 2026-11-16: "softer"; NOT the strong v4 grade)
```bash
ffmpeg -y -i $R/edit-loud.mp4 -vf "hqdn3d=2:2:3:3,curves=all='0/0 0.25/0.22 0.6/0.61 1/0.98',eq=saturation=1.05,colorbalance=rs=0.02:bs=0.05:bm=0.02,unsharp=5:5:0.3,vignette=PI/7" \
  -c:v libx264 -preset medium -crf 16 -c:a copy -movflags +faststart $R/edit.mp4
```
Reference: `references/grade-compare.jpg` (middle = this grade). Keep the real room. Never cut the person out.

## 6. The "Purple Room" style

Reference storyboard: `references/purple-room-storyboard.png` (approved 2026-11-16). Read it before planning.

### 6.1 Tokens
- Plum `#120A1F` (full-screen backgrounds, radial to `#2A1A4A` in the centre) · Violet `#8B5CF6` (highlight pill, bars,
  cursor) · Lilac `#C4B5FD` (secondary text, numbers) · White `#F5F3FF` · Muted `#9A8FB5` · Dim violet `#3B2A63`/`#4A3A6B`.
- **Arabic font: Alexandria** (600 body, 800 highlight) — NOT Cairo. Latin: Inter Tight 500/800. UI labels: JetBrains
  Mono. Big numbers/chapters: Instrument Serif italic. Fonts are bundled in `public/fonts` (Alexandria from
  `@fontsource/alexandria`, OFL).
- No orange, no blue, no glow, no gradient blobs, no emoji, no icon pop-ups every few seconds.

### 6.2 Grammar (how every video is built)
- **Most of the time it is the user, in his real room, graded.** Slow push-ins (1.00→1.08 over ~3 s) instead of jumpy
  punch-ins.
- **Captions**: two calm lines under the chin, Alexandria 600 white with a soft shadow, max 4 words per line; the ONE
  key word per page sits in a **violet pill** (white text, 7 px radius) that wipes in right-to-left (0.3 s).
  Foreign words in Inter Tight. Second line at 60 % opacity.
- **Under-chin graphics** (frosted plum cards: `rgba(29,18,51,.82)`, 1 px lilac border at 25 %, 12 px radius):
  comment card, chapter chip ("01 الثمن"), gap bars, pinned reply. One at a time, held ≥ 1.5 s.
- **Full-screen animation moments** (3 s each, ~1 per 12–15 s of video, never more than 4 per minute) for the key
  ideas. Captions move to the TOP in these (no face on screen). One object per frame, centred, lots of space.
- **Chapters**: "01 / 02…" — chip under the chin, or a soft blur (0→6→0 px over 0.9 s) + serif "02" under the chin.
- **Colour story**: the dead-end moment (a problem, "impossible", "ma khdamch") drains the shot to B&W (0.4 s) with a
  violet strike-through on the word + 0.5 s of music silence; colour returns on the solution.
- **Loop**: if the video opens on a question/comment, close on the pinned answer.
- **Motion**: ease-in-out only, 0.5–0.9 s, no bounce/springs, objects carry over between scenes (a number becomes a bar,
  an object comes back changed). Sounds come from the object (keys, ticks, a slider), no whooshes on everything.
- **End**: last caption on the user, then a short plum end card only if the user wants one.

### 6.3 Components (in `engine/src/components/purple/`; build once, see 1.3)
| Component | What it draws | Used for |
|---|---|---|
| `PurpleCaptions` | 2-line Alexandria captions + violet pill wipe | every face shot |
| `FrostedCard` | the frosted under-chin card shell | base for the 4 below |
| `CommentCard` | avatar dot + comment text + like counter ticking | hooks that start from a question |
| `ChapterChip` | serif number + Arabic label | "01 الثمن" |
| `GapBars` | two labelled bars, second grows past the first | comparisons (price, speed, time) |
| `PinnedReply` | comment + "PINNED" reply sliding in under it | closing the loop |
| `ChapterBlur` | blur 0→6→0 on footage + serif number | "النقطة الأخرى" |
| `BWStrike` | B&W range on footage + word with violet strike-through | the dead end |
| `MomentBlocks` | blocks falling into a phone outline | building / no-code / apps |
| `MomentCounter` | rolling number → big value + serif unit | money, %, counts |
| `MomentSlider` | one big slider + serif label writing itself | settings / customisation / choice |
| `MomentCode` | one line of code typing, violet cursor | the "it's code" / solution beat |
| `PlumEndCard` | serif line + handle | optional ending |
New moments for new topics follow the same rules: one object, plum background, captions at the top, 3 s, eased.

### 6.4 Storyboard gate (the user likes to approve the look first)
Make ONE image: a 4-column grid of 9:16 panels (one per scene), each with the real frame (graded) or the moment drawn
in HTML, time, what is said, the motion note; plus the palette. Build it as HTML with the bundled fonts and screenshot it
with Playwright (`npx playwright screenshot` or a 10-line script) at deviceScaleFactor 2 into
`results/<slug>/storyboard.png`. Send it and wait for "ok" (skip in one-shot mode).

## 7. Captions

1. **Second opinion — ONE command, skip it if the user gave a script:**
   ```bash
   python3 -I scripts/darija/second_opinion.py $R/in.mp4 $R/phrases.json $R/second.json
   ```
   It prints, per phrase, the Arabic pass next to a French pass (recovers the French/English words), then one
   whisper.cpp large-v3 run on the whole clip. **That is the whole transcription budget.** Never write ad-hoc loops,
   never run whisper.cpp on short clips (it reloads a 3 GB model each call), never use `-ss … -to` (use `-t`),
   whisper.cpp's binary is `.whisper/main`.
2. Rebuild what was really said. Whisper drifts into MSA ("يستطيع", "سيكون") and mishears Darija ("فحل شات جيب بيتي" =
   "بحال ChatGPT", "بانويالمو" = "manuellement", "هاد دي في غونسيال" = "la différence"). Darija spellings: كنقول، بزاف،
   دابا، واش، علاش، ديال، غادي، حيت، شي، هادشي.
3. Write `src/videos/<slug>/pages.txt` (format in `scripts/darija/align_captions.py`, full example: `scripts/darija/pages.example.txt`; max 4 words/page, ONE accent per
   page — the pill word — foreign words Latin, `@start-end` source-second overrides where Whisper is off), then:
   ```bash
   python3 -I scripts/darija/align_captions.py src/videos/<slug>/pages.txt $R/phrases.json $R/segments.json \
     src/videos/<slug>/edit.json src/videos/<slug>/<slug>.srt
   ```
   Read every printed line; add `@` ranges where nothing matched. Flag best-guess lines in the report.

## 8. edit.json, face zone, music, SFX

- `footage.src = videos/<slug>/raw/edit.mp4`, vertical 1080x1920, register the slug in `src/Root.tsx`.
- `python3 scripts/face_zone.py src/videos/<slug>/edit.json` (re-run when push-ins change). A "face reaches low"
  warning is normal for chest-up framing: captions go at the chest, cards under them.
- **Music**: low lo-fi bed, volume 0.2–0.25 (≈ 12 dB under the voice), fade in 0.8 s / out 1.5 s, cut to silence for the
  B&W beat. Sources in order: Epidemic Sound connector (check download rights first: previews are NEVER allowed),
  vidIQ `vidiq_generate_music` (if connected), or a royalty-free file the user puts in `references/music/`.
  Reusable bed (vidIQ-generated, licensed): `public/music/lofi-bed.m4a` → set `music.src` to `music/lofi-bed.m4a`. Never unlicensed music.
- **SFX**: `python3 scripts/make_sfx.py public/videos/<slug>/sfx`; soft tick on cards (0.3), type under code (0.3),
  chime on the result (0.3). Never two within 0.4 s.

## 9. QA, render, deliver

```bash
npx tsc --noEmit
python3 scripts/check_face.py <slug>                         # must print PASS
# stills: one per graphic/moment at its start + 0.9 s, contact sheet, LOOK at it (Arabic joined & in order, nothing cut off)
npx remotion still <slug> out/<slug>/s<N>.png --frame=<F> --scale=0.3
npm run final -- <slug> out/<slug>-final.mp4                 # local machines are usually fast enough in one go
# music + SFX can push the peak to 0 dBTP: always limit the final (video copied, not re-encoded)
ffmpeg -y -i out/<slug>-final.mp4 -c:v copy -af "aresample=192000,alimiter=limit=0.82:attack=1:release=50:level=false,aresample=48000" \
  -c:a aac -b:a 192k -movflags +faststart "../results/<slug>/<slug>.mp4"
ffmpeg -hide_banner -i "../results/<slug>/<slug>.mp4" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2
cp src/videos/<slug>/<slug>.srt "../results/<slug>/"
```
Verify: 1080x1920, 30 fps, -14 LUFS ± 0.3, peak ≤ -1. Then write `results/<slug>/report.md`:
original → final length, the removal table (from build_cut.py: timestamps in the ORIGINAL clip + reason), best-guess
caption lines, anything skipped. Tell the user the paths. Commit the edit (never raw/ or out/) in `engine/`:
`git add src/videos/<slug> src/Root.tsx && git commit -m "<slug>: final edit"` (local commit only, never push).

---

## 10. Every problem hit so far, and the fix

| # | Problem | Fix |
|---|---|---|
| 1 | iPhone HEVC with rotation looked horizontal | Read rotation, look at a frame, transcode to H.264 CFR30 (§2) |
| 2 | Silence-cut filter graph ran out of memory | `render-segments.mjs` (segment by segment, concat demuxer) |
| 3 | whisper.cpp large-v3 looped on long audio; models drift into MSA | per-phrase faster-whisper, no conditioning; rebuild the Darija from context |
| 4 | A Darija `--prompt` leaked into short clips' transcripts | never prompt short clips |
| 5 | faster-whisper crashed on `av.open(... metadata_errors)` | audio decoded with ffmpeg to numpy (already in the scripts) |
| 6 | **Retakes missed** (whole-file transcript merged repeats) | per-segment/per-phrase transcription + verify (§4) |
| 7 | Breath/noise segments survived ("اشتركوا في القناة" hallucinations) | remove JUNK segments (§4.2) |
| 8 | Cut landed on a word onset / retake with no pause | `cut_points.py`, closure dip, 8 ms fades |
| 9 | loudnorm overshot to +0.6 dBTP; final peaked at 0.0 after music | two-pass + oversampled limiter (§5.1) and a final limiter (§9) |
| 10 | Caption pages landed on removed noise | time captions from phrase words + `@` overrides (§7) |
| 11 | A script was run twice and read its own output | always rebuild from original data |
| 12 | Epidemic Sound downloads FORBIDDEN | tell the user, use another licensed source, never previews |
| 13 | silencedetect found no pauses on loud audio with room noise | RMS pause detection (§3) |
| 14 | 16 min lost on an improvised 3rd transcription | fixed budget: `transcribe_phrases.py` + `second_opinion.py` only (§7) |
| 15 | Background cut-out (MediaPipe) looked jagged at the body edges; user rejected it | keep the real room + soft grade (§5.2) |
| 16 | User rejected: Cairo font, orange, blue, a heavy/busy layout, the strong grade | Purple Room tokens, Alexandria, one object per frame, soft grade (§6) |
| 17 | User kept asking "where are we" | one-line status with ETA for every step > 1 min |
| 19 | Windows: `python3` / Store python, PATH not refreshed after installs | venv `python`, reopen the terminal after winget |
| 18 | Paths with spaces ("raw footage", "video editor") broke shell commands | always quote paths |

## 11. Learned rules (add new ones here, with the date)
- 2026-11-18: Screenshots are never static. Use `momentShot` with a timeline synced to the spoken words: `keys`
  (camera keyframes t/zoom/fx/fy, eased; a tall image with `imgAspect` < `aspect` scrolls), `highlights` (spotlight
  dims the rest + violet glow + label), `cursor` (moves, clicks, ripple), `scan` (QR scan line -> "✓ verified"),
  `chips` (+XP pop-ups), `instant` for a screen on the very first frame. Positions = fractions of the IMAGE: make a
  10% grid overlay of each screenshot first to read coordinates. Keep text readable: a portrait screenshot goes in a
  wider frame that scrolls (aspect ~1.0-1.3) instead of a narrow box; never zoom so far a logo/title gets cut.
- 2026-11-18: Progma's live demo (academy.progma.ai/demo) can be captured with Playwright (viewport 1600x900,
  deviceScaleFactor 2, `fullPage`); close the "réservé aux élèves" pop-up with "Continuer la visite". The long
  Communauté feed, cropped to the post column, makes a great scrolling moment.
- 2026-11-18: Epidemic Sound search works but downloads are FORBIDDEN on this account (no licence): never use the
  low-quality previews instead. Sound library = Mixkit via `fetch_sfx.py` (35 sounds incl. mouse-click, zoom-in,
  zoom-move, blip-tech, scan-sweep, verify-ok, xp-coin, unlock, hit-intro); `auto_sfx.py` places them from the
  momentShot timeline and adds very soft swishes (0.09) on face push-ins.
- 2026-11-17: Never a caption word mixing Latin and Arabic letters (`editيتو`, `نpostي`): the browser scrambles it.
  Write the Darija spelling (`مونطيتو`, `نبوسطي`) or split into separate words. `align_captions.py` refuses them.
- 2026-11-17: Every step must work for BOTH vertical (9:16) and horizontal (16:9, YouTube) videos. Set `orientation`
  from Colab's `meta.json`. Purple components scale by the SHORT side; in 16:9 captions are ONE line, cards sit under
  them (width relative to the short side), full-screen moments are laid out from the centre (`useVY`). Vertical output is
  unchanged (pixel-identical). Still check stills + `check_face.py` for every horizontal video.
- 2026-11-17: Sound effects = free Mixkit library + automatic placement. Every session: `python3 -I scripts/fetch_sfx.py`
  (downloads 26 cleaned WAVs into `public/sfx/lib/`, git-ignored: the Mixkit licence forbids redistributing the files,
  and the repo is public). After the overlays are final: `python3 -I scripts/auto_sfx.py src/videos/<slug>/edit.json`
  (the sound comes from the object: coins on the counter, keys under code, page turn on chapters, deep hit + error tone at
  the B&W dead end, chimes on results; volumes 0.15-0.45; hand-placed sounds are kept). Re-run it whenever overlays
  move. Never commit `public/sfx/lib/`.
- 2026-11-17: Heavy AI work (transcription) on Google Colab GPU; editing/rendering in the Claude Code cloud session
  (§1.4). Always also deliver a 720p preview ≤ 30 MB for the phone.
- 2026-11-14: Nothing over or above the face, ever.
- 2026-11-15: Foreign words stay in their original language (Latin letters) in Darija captions.
- 2026-11-15: ALL retakes removed; per-phrase transcription; junk segments cut.
- 2026-11-16: Style = Purple Room; Alexandria; soft grade; calm, minimal, creative; the user on screen most of the time
  with a few full-screen animation moments; never cut the background out.
- 2026-11-16 (Windows setup): Smart App Control blocks Git's `libcurl-4.dll` (no clone/pull/push over HTTPS) and the
  venv's `pip.exe`. The engine came from a ZIP and has a LOCAL git repo only: skip `git pull`/push, use
  `python -m pip`. Python reads JSON as cp1252 on Windows: always run scripts with `python -I -X utf8 ...`
  (`-I` ignores PYTHONUTF8). Purple components are built: `src/components/purple/`, `style: "purple"` in edit.json.
  check_face.py skips full-screen moments (momentBlocks/Counter/Slider/Code, endCard).
