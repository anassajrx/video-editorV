---
name: darija-video-edit
description: End-to-end runbook for editing a Moroccan Darija talking-head video in this repo, from a Google Drive link to a finished vertical MP4 with Darija captions, all retakes removed, icon pop-ups, music and SFX, plus an Arabic SRT. It lists every problem hit on the first video (ai-agent, Nov 2026) and the fix, so they are never repeated. Use it whenever the user gives a Darija video to edit, together with edit-skill, DESIGN.md and CLAUDE.md.
---

# Darija video edit: the full runbook

Built from the first real edit (`ai-agent`, 2:47 raw → 1:41 final, 3 rounds). Follow it in order.
It works **with** `edit-skill` (brand, roles, graphics) and `CLAUDE.md` (repo rules). Where this file
is more specific, this file wins.

---

## 0. Non-negotiables (the user's rules)

1. **Nothing over or above the face**, captions included. `check_face.py` must print PASS before anything is sent.
2. **Every retake is removed.** Keep only the LAST complete take of every sentence. Remove false starts,
   stutters ("ana ana…"), lone fillers (euh, emm), and if the user says "cut", "3awd" or "mn jdid", remove that word and
   the take before it. *(Round 2 of the first video was only about missed retakes. See §4.)*
3. **Never cut mid-word.** Every cut lands in a real energy valley (see §4.3).
4. **Captions = what was actually said, in Darija.** Never translate to Modern Standard Arabic, never "correct" Darija.
5. **Foreign words stay in their ORIGINAL language.** *(Rule added 2026-11-15.)* When the user speaks English or French inside the
   Darija, keep that word in English/French, in Latin letters, exactly as said. Do **not** write it in Arabic letters.
   - Darija words → Arabic letters: كنقول، بزاف، دابا، واش، علاش، ديال، غادي، حيت، شي، هادشي
   - English/French words → Latin, original spelling: `flight`, `booking`, `website`, `click by click`, `task`, `prompt`,
     `instructions`, `mindset`, `workflow`, `process`, `cloud`, `chatbot`, `copy paste`, `PC`, `les résultats`, `manuellement`
   - Brand/tool names → Latin as always: `AI`, `AI Agent`, `ChatGPT`, `Excel`, `GitHub`, `Claude`
   - Darija prefixes/articles glued to a foreign word are written as a separate small Arabic word before it:
     `الـ website`, `فالـ cloud`, `ديال الـ workflow`, `بـ click وحدة`. Do not glue Arabic and Latin into one token.
   - Whisper usually writes these words in Arabic letters (فلايت، البوكينغ، الويبسايت…). Convert them back to the original word.
   - When unsure whether a word was French or English, write what it sounds like (`résultats` vs `results`).
6. **Approval gates**: CLAUDE.md asks for plan → stills → draft approval. When the user says "one shot / no approvals",
   skip the gates but still look at the stills yourself, still run `check_face.py`, and still report everything.
7. Keep the user informed: they ask "where are we" often. Give one line of status (step, %, ETA) whenever a long job runs.

---

## 1. Setup (once per session, ~5 min)

```bash
cd <repo>                       # the repo is anassajrx/video-editorv; attach it with add_repo if missing
npm ci                          # Remotion + whisper.cpp wrapper
pip install -r requirements.txt # opencv-python-headless, numpy, faster-whisper
```
- `faster-whisper` downloads `large-v2` (~3 GB) from Hugging Face on first use (cached afterwards).
- If the repo was cloned shallow, set the upstream once, or the stop hook keeps saying "no remote branch":
  ```bash
  git config --add remote.origin.fetch '+refs/heads/<branch>:refs/remotes/origin/<branch>'
  git push -u origin <branch> && git branch -u origin/<branch>
  ```

## 2. Get the footage (Google Drive, large file)

The Drive connector stops at 10 MB. Use the Drive API with the user's token:
1. File ID = the part after `/d/` in the link. `get_file_metadata` (connector) gives name + size.
2. A plain `curl` to `www.googleapis.com` returns **401**: call `request_credential` for host `www.googleapis.com`
   (bearer) so the user pastes a Google access token into the secure form. Never ask for it in chat.
3. Download in the background, then check it:
   ```bash
   mkdir -p public/videos/<slug>/raw
   curl -sS -L -o public/videos/<slug>/raw/IMG.MOV "https://www.googleapis.com/drive/v3/files/<ID>?alt=media&supportsAllDrives=true"
   ffprobe -v error -show_entries stream=codec_name,width,height:stream_side_data=rotation -of compact public/videos/<slug>/raw/IMG.MOV
   ```
4. **iPhone .MOV files are HEVC with `rotation=90`**: 1920x1080 in ffprobe but really VERTICAL. Use vertical 1080x1920.
   Grab a frame (`ffmpeg -ss 20 -i … -frames:v 1 x.jpg`) and look at it to confirm the orientation and the face position.
5. Convert to a constant-30fps H.264 intermediate first (HEVC + rotation + variable frame rate break the later steps):
   ```bash
   ffmpeg -i public/videos/<slug>/raw/IMG.MOV -map 0:v:0 -map 0:a:0 -vf "fps=30,format=yuv420p" \
     -c:v libx264 -preset veryfast -crf 16 -threads 4 -c:a aac -b:a 192k -ar 48000 public/videos/<slug>/raw/in.mp4
   ```
   (`raw/` is git-ignored; keep every big media file inside it.)

## 3. Silence cut

```bash
npm run cut -- public/videos/<slug>/raw/in.mp4 public/videos/<slug>/raw/cut.mp4 --noise=-38dB --min=0.3 --pad=0.1
```
- Phone audio is quiet (raw was -28 LUFS), so `-38dB` works better than the default `-35dB`.
- Output: `cut.mp4` + `cut.mp4.cuts.json` (kept segments in source seconds). Everything later uses `cuts.json` + `in.mp4`.

## 4. Find and remove ALL retakes (the step that failed in round 1)

### 4.1 Transcribe per segment and per phrase, never whole-file
```bash
python3 -I scripts/darija/transcribe_phrases.py public/videos/<slug>/raw/in.mp4 \
  public/videos/<slug>/raw/cut.mp4.cuts.json public/videos/<slug>/raw/phrases.json
```
~6–8 min for 2–3 min of speech. It prints every segment and every phrase on its own line.

> **Transcription budget (rule added after video 2, which lost ~16 min to improvised whisper.cpp runs):**
> exactly TWO commands, nothing else: `transcribe_phrases.py` (this step) and `second_opinion.py` (§6.1).
> Total ≈ 15 min per minute of speech. Do not write ad-hoc transcription loops, never run whisper.cpp on short
> clips (it reloads the 3 GB model every call), never pass `-to` after an input `-ss` in ffmpeg (it becomes an
> absolute time and the clip runs to the end). If the text is still unclear after both, write your best guess,
> flag it in the report, and move on. **If the user sent a script, skip `second_opinion.py` entirely.**
**Why:** a whole-file Whisper transcript merges a repeated sentence into one copy, so retakes are invisible.
On the first video the hook, the flight sentence and the outro were each said twice, and none showed in the
whole-file transcript.

### 4.2 Read the list and decide
- Two lines that say (almost) the same thing → **retake**: remove the first, keep the last complete one.
- A line that stops halfway and restarts → **false start**.
- Segments flagged `JUNK` (0.2–0.4 s, text "اشتركوا في القناة", "شكرا" or empty) are breaths, mouth noises, "euh":
  Whisper hallucinates those texts on non-speech. Remove them all (`--phrases` in build_cut does it).
- A wordless stretch that is LOUD (≈ speech level, -28 dB) can hold words Whisper skipped: transcribe it on its own
  before deciding. A quiet one (≤ -43 dB) is a breath: cut it.
- A rephrase with no pause before it (e.g. "غادي يكون محتوى…" then "غادي تكون واحد السيري…") is still a retake: cut it
  at the consonant closure between the two takes (see 4.3).

### 4.3 Check every cut point (never mid-word)
```bash
python3 -I scripts/darija/cut_points.py public/videos/<slug>/raw/in.mp4 59.98 63.72 154.40 158.02
```
- Prefer a valley ≤ -45 dB. Whisper word boundaries are off by ±0.1–0.3 s: trust the energy, not the word times.
- No valley at all (continuous speech ≈ -30 dB) → find the short closure dip (≈ -37 dB) at the word boundary.
- If the cut lands on a rising edge (onset of the next word), move it 30–50 ms earlier into the quiet.

### 4.4 Build the cut and render it from the ORIGINAL (one encode generation)
Write `public/videos/<slug>/raw/removals.json` (`[{"s":0.0,"e":3.30,"reason":"retake: first '…'"}, …]`, source seconds), then:
```bash
python3 -I scripts/darija/build_cut.py public/videos/<slug>/raw/cut.mp4.cuts.json public/videos/<slug>/raw/removals.json \
  public/videos/<slug>/raw/segments.json --phrases=public/videos/<slug>/raw/phrases.json
node scripts/render-segments.mjs public/videos/<slug>/raw/in.mp4 public/videos/<slug>/raw/segments.json public/videos/<slug>/raw/edit-raw.mp4
```
`render-segments.mjs` encodes each segment on its own (low memory), snaps cuts to whole frames (audio stays in sync after
dozens of cuts) and adds 8 ms audio fades (no clicks). Keep the printed removal table for the final report.

### 4.5 Verify
Transcribe the start, the end and every retake spot of `edit-raw.mp4` again (short windows) and confirm each line is said
**once**. Only then continue.

## 5. Loudness: -14 LUFS, true peak ≤ -1 dBTP (two-pass + limiter)

Plain loudnorm overshot to +0.6 dBTP on this footage. This chain landed at -14.1 LUFS / -2.9 dBTP:
```bash
cd public/videos/<slug>/raw
J=$(ffmpeg -hide_banner -i edit-raw.mp4 -af loudnorm=I=-14:TP=-1:LRA=7:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
M=$(echo "$J" | python3 -c "import json,sys;d=json.load(sys.stdin);print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
ffmpeg -y -i edit-raw.mp4 -af "loudnorm=I=-13.5:TP=-1.5:LRA=7:$M,aresample=192000,alimiter=limit=0.7:attack=1:release=50:level=false,aresample=48000" \
  -c:v copy -c:a aac -b:a 192k -movflags +faststart edit.mp4
ffmpeg -hide_banner -i edit.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2   # verify
```
If I lands outside -14 ± 0.3, nudge the loudnorm `I` (±0.4) and run it again.

## 6. Captions (Darija + original-language foreign words)

0. Get the second opinion, ONE command (skip it if the user gave a script):
   ```bash
   python3 -I scripts/darija/second_opinion.py public/videos/<slug>/raw/in.mp4 \
     public/videos/<slug>/raw/phrases.json public/videos/<slug>/raw/second.json
   ```
   It prints, per phrase, the Arabic pass next to a French pass (recovers application, plateforme, personnalisation,
   impossible…), then one whisper.cpp large-v3 run over the whole clip (best for sentence meaning and numbers).
   Those three views are all you get: write the captions from them.
1. Read the phrase list (§4.1) for the kept takes. Whisper is weak at Darija: large-v2 output is often MSA-flavoured
   ("يستطيع", "سيكون هناك") or misheard ("فحل شات جيب بيتي" = "بحال ChatGPT", "بانويالمو" = "manuellement",
   "الهزولتة" = "les résultats", "سيري" = "série"). Rebuild what was really said from context.
2. Write `src/videos/<slug>/pages.txt`: one caption page per line, max 4 words, in spoken order (format in the header of
   `scripts/darija/align_captions.py`; example: `src/videos/ai-agent/pages.txt`).
   - Roles: most words `d`; fillers (و، ف، ل، اللي، هو، ديال، راه، غير، الـ) `s`; ONE accent per page: `h` hero,
     `g` signal (tech word), `e` ember (money/numbers/results), `r` error (problems).
   - Page breaks at natural phrase ends, no punctuation at the end of pages.
   - Foreign words in their original language (§0.5).
3. Align and write captions + SRT:
   ```bash
   python3 -I scripts/darija/align_captions.py src/videos/<slug>/pages.txt public/videos/<slug>/raw/phrases.json \
     public/videos/<slug>/raw/segments.json src/videos/<slug>/edit.json src/videos/<slug>/<slug>.srt
   ```
   It prints each page next to what Whisper heard. Where nothing matched or the match is wrong (it happens on fast or
   hallucinated stretches, and on the final "باي"), add `@start-end` (source seconds, from the phrase list) to that line
   and run it again.
4. Never time captions from a whole-file transcript: it drifts by up to a second and pages land on removed noise.

## 7. edit.json, punch-ins, face zone

- `footage.src` = `videos/<slug>/raw/edit.mp4`, `orientation` from §2, `durationMs` written by align_captions.
- Punch-ins on the jump cuts: alternate 1.0 ↔ 1.06, at most one every 1.5 s, none in the last second.
- Register the slug in `src/Root.tsx`, then:
  ```bash
  python3 scripts/face_zone.py src/videos/<slug>/edit.json   # writes faceZone; re-run when punch-ins change
  npx tsc --noEmit
  ```
  A "face reaches low" warning is normal for chest-up phone framing: captions go at the chest, graphics under them.

## 8. Pop-ups, music, SFX (round 3, "creative but not noisy")

- **Pop-ups**: about one every 4–5 s, never two at once, each held ≥ 1.5 s, matched to the words:
  - `icon` overlay (glass circle + line icon + short Latin mono label). Icons: bot, laptop, plane, cursor, check, ticket,
    chat, table, workflow, phone, cloud, eye, bell, sparkles (`src/components/Icons.tsx`, Lucide-based). Alternate
    `x` 0.32 / 0.5 / 0.68 for rhythm.
  - `card` for the key concepts (e.g. "AI Agent", "Ask → Do", the end card), `terminal` for "it executes" moments.
  - Card and icon text is Latin (the Inter/JetBrains fonts have no Arabic glyphs).
  - Space under the captions is limited (≈ faceZone.bottom + 0.15 … 0.94): icons, 2-line terminals and 1-line cards fit;
    profile and timeline do not.
- **SFX**: `python3 scripts/make_sfx.py public/videos/<slug>/sfx` makes original whoosh/pop/click/chime/type sounds.
  Whoosh on cards (0.3), pop on icons (0.35), click on every spoken "click" (0.45), chime on success/result words (0.35),
  type under terminals (0.3). Never two within 0.4 s.
- **Music** (in this order):
  1. Epidemic Sound connector. **Check download permission first**: on the first video every `DownloadRecording` /
     `DownloadSoundEffect` returned `FORBIDDEN` (the account had no download rights). Search works even then.
     If downloads fail, tell the user and move on. **Never use the `lqmp3Url` previews** (unlicensed).
  2. vidIQ `vidiq_generate_music` (25 credits, original royalty-free WAV). The prompt that worked: "Instrumental chill lo-fi
     tech background music, hopeful and smooth, soft electric piano chords, warm sub bass, gentle dusty hip hop drums with
     light hi-hats, subtle airy synth pad, … around 90 BPM, sits quietly under a voice-over". Poll `vidiq_job_poll`.
  3. Prepare it: `ffmpeg -i music.wav -af "afade=t=in:d=1.5,afade=t=out:st=<len-3.5>:d=3.5,loudnorm=I=-16:TP=-1.5" -ar 48000 -c:a aac bed.m4a`
     → `"music": {"src": "videos/<slug>/music/bed.m4a", "volume": 0.25, "fadeInMs": 800, "fadeOutMs": 1500}` (≈ 12 dB under the voice).
- Run `check_face.py` again with the overlays in place, and look at a contact sheet of every graphic (one still per overlay, ~0.9 s after it starts).

## 9. QA, render, deliver

```bash
python3 scripts/check_face.py <slug>                 # must print PASS (~2 min)
# contact sheet: one frame every ~4–5 s, look for disconnected/reversed Arabic, word order, text cut at the edges, face overlap
for s in $(seq 1 4 100); do npx remotion still <slug> out/<slug>/cs/$(printf %03d $s).png --frame=$((s*30+15)) --scale=0.25 --log=error; done
ffmpeg -pattern_type glob -i 'out/<slug>/cs/*.png' -vf tile=9x3 -frames:v 1 out/<slug>/contact.png
# render in parts of 1200 frames (~4 min each), then join without re-encoding
for a in 0 1200 2400; do npx remotion render <slug> out/<slug>/part-$a.mp4 --frames=$a-<min(a+1199,N-1)> --crf=18 --concurrency=75% --audio-codec=aac --log=error; done
printf "file 'part-0.mp4'\nfile 'part-1200.mp4'\nfile 'part-2400.mp4'\n" > out/<slug>/parts.txt
ffmpeg -f concat -safe 0 -i out/<slug>/parts.txt -c copy -movflags +faststart out/<slug>-final.mp4
```
Verify the final: 1080x1920, 30 fps, duration, -14 LUFS ± 0.3, true peak ≤ -1 dBTP. Then deliver:
- the MP4 + the `.srt` (send both with SendUserFile),
- original length → final length,
- the removal table (from build_cut.py: timestamps in the ORIGINAL clip + reason: silence / retake / false start / breath),
- caption lines that are best guesses (so the user can correct them),
- commit `edit.json`, `pages.txt`, `.srt`, removals and code (never `raw/` or `out/`) with `<slug>: final edit` /
  `<slug>: round N notes`, and push.

---

## 10. Problems hit on the first video, and the fix

| # | Problem | Fix |
|---|---|---|
| 1 | Drive connector caps downloads at 10 MB; API curl gave 401 | Drive API + `request_credential` for `www.googleapis.com` (§2) |
| 2 | iPhone HEVC with rotation looked horizontal | Read `rotation` side data, look at a frame, use vertical; transcode to H.264 CFR 30 (§2) |
| 3 | `npm run cut` was killed (out of memory): trim+concat graph decoded the clip once per segment | `render-segments.mjs` encodes segment by segment and joins with the concat demuxer (§3) |
| 4 | whisper.cpp large-v3 looped: the same sentence repeated for the whole second half | `--max-context 0` helps a little; switch to faster-whisper large-v2 (`transcribe_fw.py`, `transcribe_phrases.py`) |
| 5 | large-v3 and large-v2 drift into MSA ("يستطيع فعلها من خلال…") | Short pieces, no conditioning; rebuild the Darija from context; never caption MSA |
| 6 | A Darija `--prompt` LEAKED into short clips (the prompt text came back as the transcript) | No prompt on short clips |
| 7 | faster-whisper crashed (`av.open() got an unexpected keyword argument 'metadata_errors'`) | Decode audio with ffmpeg to float32 and pass the numpy array (already in the scripts) |
| 8 | A whole-file re-transcription silently stopped at 52 s | Don't rely on one whole-file pass; per-phrase transcription covers everything |
| 9 | **Retakes missed in round 1** (whole-file transcript merged repeats) | Per-segment + per-phrase transcription, verify the final cut (§4) |
| 10 | 17 tiny breath/noise segments survived the silence cut ("اشتركوا في القناة" hallucinations) | Remove junk segments (§4.2) |
| 11 | A cut point landed on a word onset; one retake had no pause at all | `cut_points.py` energy check; closure dip; 8 ms fades (§4.3) |
| 12 | loudnorm overshot true peak to +0.6 dBTP | Two-pass loudnorm + oversampled limiter (§5) |
| 13 | Caption pages landed on removed noise (whole-file timings were up to 1 s off) | Time captions from phrase word timestamps + `@` overrides (§6) |
| 14 | A remap script was run twice and read its own output as input | Always rebuild from the committed/original data (`git checkout` the file first), never chain re-runs |
| 15 | Epidemic Sound downloads FORBIDDEN | Tell the user; vidIQ music; self-made SFX; never previews (§8) |
| 16 | Stop hook: "no remote branch" although pushed | Shallow clone has no refspec for the branch: add it and set the upstream (§1) |
| 17 | The user kept asking "where are we" during long steps | Send a one-line status with an ETA whenever a step runs more than a minute |
| 18 | (video 2) `npm run cut` kept everything: room noise peaks stopped `silencedetect` from finding any pause, even at -30 dB | Measure 20 ms RMS in Python, take runs < -32 dB that last ≥ 0.3 s, pad 0.08 s, write `cut.mp4.cuts.json` yourself |
| 19 | (video 2) The final render peaked at 0.0 dBTP once music + SFX were mixed over the voice | After the render, run `alimiter=limit=0.82` (oversampled, `-c:v copy`) on the final and check ebur128 again |
| 20 | (video 2) Footage uploaded straight into the chat (no Drive link), and the saved Google token had expired | Use the upload path (`/root/.claude/uploads/...`) directly; tokens last ~1 h, so request a fresh one only when Drive is needed |
| 21 | (video 2) ~16 min lost on a THIRD, improvised transcription: whisper.cpp per short clip (model reload each call, 180 s timeouts), `-ss … -to` made clips run to the end, float times broke the shell loop, wrong binary name (`.whisper/main`, not `whisper-cli`) | Fixed budget: `transcribe_phrases.py` + `second_opinion.py` only (§4.1, §6.0); best guesses get flagged, not re-transcribed |

## 11. Timing reference (4 vCPU cloud session, 2:47 raw clip)
Download 320 MB ~1 min · transcode ~2.5 min · silence cut ~2 min · phrase transcription ~7 min · segment render ~2 min ·
loudness ~1 min · face check ~2 min · contact sheet ~2 min · final render ~11 min (3 parts) · vidIQ music ~1 min.
