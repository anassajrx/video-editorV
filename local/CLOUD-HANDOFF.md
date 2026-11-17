# Handoff: continue the video-editing work in a Claude Code cloud session

Paste this whole file as the first message of the new cloud session, or tell it: "read `local/CLOUD-HANDOFF.md` first".
Written 2026-11-17, at the end of the first local session (Windows laptop).

---

## 0. Who / what

- The user films **Moroccan Darija talking-head videos** (vertical 1080x1920, 30 fps) mixing Darija with English and French words.
  Handle on GitHub: `anassajrx`. Repo: `anassajrx/video-editorV` (public). Videos are posted on Instagram/TikTok.
- The engine (this repo) = **Remotion** (React video) + Python/ffmpeg scripts. The **single source of truth** for how to
  edit is the skill `.claude/skills/darija-video-edit-local/SKILL.md`. **Read it completely before any edit.**
- The user wants to **stop depending on the laptop**: heavy AI work on **Google Colab (free T4 GPU)**, the rest in a
  **Claude Code cloud session**, files exchanged through **Google Drive links**.

## 1. User preferences (follow them)

- Answer in short, direct English; give a **one-line status with ETA** for anything > 1 min; they often ask "where are we".
- They work from their **phone** a lot: files over **30 MB cannot be sent to the phone** → also make a 720p preview
  (`-vf scale=720:1280 -b:v 1100k -maxrate 1300k -bufsize 2600k -b:a 96k`, ~25 MB for 3 min).
- **Style = Purple Room** (skill §6). They explicitly chose it over a green "terminal/glitch" brief. No emoji on screen.
- Retakes: **keep the best take, usually the LAST one**. Remove false starts, fillers, "Thank you / اشتركوا في القناة"
  hallucinations on breaths.
- Captions = what was actually said, Darija in Arabic letters, **foreign words in Latin letters**. Never translate.
- **Never write a word that mixes Latin and Arabic letters** (`editيتو`, `نpostي`, `كنuploadيه`): the browser scrambles
  them. Use the Darija spelling (`مونطيتو`, `نبوسطي`, `كنأبلوديه`, `كنشيكي`, `نكونيكطي`) or split into separate words
  (`الـ` / `boom`). The caption script check: no token may contain both `[A-Za-z]` and `[؀-ۿ]`.
- Nothing over or above the face, ever (`check_face.py` must PASS).
- They do **not** want to push from the laptop. Pushing from the cloud session is fine if they agree.
- Never paste access tokens in chat; Drive files shared "anyone with the link" download without any token.

## 2. ⚠️ The repo on GitHub is BEHIND the laptop

The laptop's Windows "Smart App Control" blocks Git over HTTPS, so **nothing below was pushed**. The laptop engine
(`video editor/engine/`, local git) has 2 commits on top of the GitHub ZIP (branch `claude-hopeful-clarke-qhnr9z`):

1. `purple-room: components` — Alexandria font (600/800 arabic) replacing Cairo; Purple tokens in `src/brand/theme.ts`;
   `src/components/purple/` (PurpleCaptions, FrostedCard, CommentCard, ChapterChip, GapBars, PinnedReply,
   ChapterBlur, BWStrike, MomentBlocks, MomentCounter, MomentSlider, MomentCode, PlumEndCard); wired in
   `src/brand/types.ts` (`style: "purple"`, PurpleOverlay union) and `src/EditTemplate.tsx`; `purple-demo` composition;
   `check_face.py` Windows-safe + skips full-screen moments.
2. `comeback: final edit` — new pieces `Cards2.tsx` (FileStack, ProgressCard, CreditRows), `MomentFlow`, `CtaEndCard`,
   a `clip` overlay (muted full-frame video, e.g. a pre-reversed rewind; hidden in QA); **bottom-origin push-ins** for
   purple (`transformOrigin: 50% 100%`, opening scale applies from frame 0); captions move to the TOP **only while** a
   full-screen moment is on screen; purple caption band 0.10; Colab scripts in `local/`; `scripts/progress-server.mjs`;
   `transcribe_phrases.py --fast` + UTF-8 output; `src/videos/comeback/` (edit.json, pages.txt, comeback.srt).
   A later local edit (not yet committed when this was written) rewrote the mixed-script caption words.

**First job in the cloud:** get that code into the repo. Ask the user which way:
- (a) they zip `video editor/engine/` (without `node_modules`, `.venv`, `.whisper`, `out`, `public/videos/*/raw`) and
  put it on Drive → you download it, compare with the repo, commit on a new branch, push (with their OK); or
- (b) they run `git bundle create engine.bundle --all` on the laptop, put the bundle on Drive → you `git fetch` from it.
  (b) keeps the exact history; prefer it.

## 3. The target workflow (laptop-free)

```
Phone/Drive ──► Colab (GPU): transcription (+ later: silence cut, retakes, loudness, grade)
                  │  writes to Drive: phrases.json, cut.mp4.cuts.json, second.json (+ later edit.mp4)
                  ▼
Claude Code cloud session: download from Drive links → captions → graphics → QA → render → upload result / send preview
```

### 3.1 Colab part (scripts in `local/`, already tested on the comeback video)

| Script | Runs on | Does | Output (in that account's Drive) |
|---|---|---|---|
| `colab_transcribe.py` | Colab account 1, T4 GPU | Drive-link download, same silence cut as `cut-silences.mjs` (-38 dB, 0.3 s, pad 0.1), per-segment + per-phrase transcription with **`anaszil/whisper-large-v3-turbo-darija`** (LoRA on `openai/whisper-large-v3-turbo`, word timestamps) | `MyDrive/darija-transcripts/video_<id8>/phrases.json`, `cut.mp4.cuts.json`, `transcript.txt` |
| `colab_second_pass_standalone.py` | Colab account 2 at the same time | same phrase boundaries, plain large-v3-turbo forced **English** then **French** → foreign words in Latin | `second.json` (`[{seg,s,e,en,fr}]`), `second.txt` |
| `colab_second_pass.py` | same notebook as cell 2 | same EN/FR pass reusing cell 1's memory | `second.json` |

Known Colab gotchas: set Runtime → T4 GPU; the Darija LoRA needs `peft`, and Colab's old `torchao` makes peft refuse
to load → the script uninstalls torchao and asks for **Runtime → Restart session**, then run again (expected once).
The Darija model writes English/French words in Arabic letters → that is why the EN/FR pass exists.
Speed: whole 5:39 clip in a few minutes on Colab vs ~60 min on the laptop CPU (Ryzen 5 4500U, no NVIDIA).

How the user hands results over: a **Drive folder link** shared "anyone with the link". Download with
`pip install gdown` then `python -m gdown --folder "<link>" -O <dir>` (worked). Single files: `gdown --id <ID>` or
`https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t` with curl.

### 3.2 Claude Code cloud part (per video)

1. `npm ci`; Python venv + `pip install -r requirements.txt` (skip faster-whisper models: transcription is on Colab).
2. Download the raw video from the user's Drive link into `public/videos/<slug>/raw/` → convert to H.264 CFR30
   (skill §2). Download the Colab folder → put `phrases.json`, `cut.mp4.cuts.json`, `second.json` in the same raw dir.
   **Use Colab's `cut.mp4.cuts.json`** (phrase times match it), not a fresh local cut.
3. Read `transcript.txt` + `second.json` side by side (AR / EN / FR per phrase) to find retakes → `removals.json`
   → `build_cut.py ... --phrases=` → `render-segments.mjs` → loudness (§5.1) → soft grade (§5.2) → `edit.mp4`.
4. Captions: write `src/videos/<slug>/pages.txt` (≤4 words/page, one `/h` pill per page, Latin words in Latin, NO
   mixed-script tokens) → `align_captions.py`. Latin-only pages rarely match the Darija transcript: **pin them with
   `@start-end` source seconds taken from `second.json`** (that took matching from bad to all-in-order).
   `align_captions.py` overwrites edit.json: save overlays/punchIns/monoRanges/music/sfx/faceZone/durationMs before
   and restore them after (or improve the script to preserve them).
5. Graphics in `edit.json` (`style: "purple"`), music `music/lofi-bed.m4a` at 0.22, SFX from `scripts/make_sfx.py`
   (synthesised, license-free).
6. Face zone: `face_zone.py` assumes center zoom; for purple bottom-origin push-ins compute
   `bottom = 1 - (1 - worst_chin) * min_scale` + margin, set it by hand, then `check_face.py <slug>` → must PASS.
7. Stills at each graphic → contact sheet → look → send. Render: `npx remotion render <slug> out/<slug>-final.mp4
   --crf=18 --concurrency=100% --audio-codec=aac` → final limiter (§9) → verify 1080x1920, 30 fps, -14 LUFS ±0.3,
   peak ≤ -1 → 720p preview for the phone → hand back (Drive upload needs the user's help or a connector; otherwise
   tell them where the file is).
8. Commit `src/videos/<slug>` + Root.tsx; push only with the user's OK.

Python on Windows needed `-I -X utf8`; in a Linux cloud session plain `python3` is fine (scripts now open files as
UTF-8 where it mattered, but keep `-X utf8` to be safe).

## 4. The comeback video (done, for reference)

- Source: Drive file `1y6cVwmcM_sPH-4NZ0zSG4ODpXuX9dKo7` ("Claude video  back .MOV", 5:39, iPhone HEVC, rotated).
- Colab results folder: `https://drive.google.com/drive/folders/1xVocOca8oudWQ3AHLkmw7BQeibt_jzcO`.
- Final: 2:59 (14 retake/filler removals), Purple Room, 122 caption pages, 12 graphics incl. 4 full-screen moments
  ("many hours of editing", footage→prompt→video, `claude.edit(video);`, "Comment EDIT" end card), rewind clip +
  "cut/captions/music ··· Claude" credits at the twist, B&W stretch on the editing-pain part, -13.8 LUFS.
- User decisions: "1 minute of video takes me **many hours**" (not 6h); **keep the whole ending** (Anthropic did it,
  follow me for IT/ERP/coding, "this time I'm back, bye").
- Best-guess caption lines still to confirm with the user: "سوايع", "هاد الـ boom ديال Claude", the twist line
  "حتى هاد الفيديو كامل مونطيتو بـ Claude Code", "اللي درت فهاد الفيديو", "دابا كاين many content".
- Post caption text: `output/caption.txt` on the laptop (also in the user's message history).

## 5. Open to-dos (agreed with the user, in this order)

1. **Get the laptop code into the repo** (§2).
2. **All-in-one Colab prep script**: convert → silence cut → transcription (Darija + EN/FR) → automatic retake
   detection (similar consecutive phrases → keep the last; output an editable `removals.json` with reasons) → loudness
   → soft grade → upload `edit.mp4` + `phrases.json` + `segments.json` + `second.json` + `removals.json` to Drive.
   Then the cloud session only does captions, graphics and render. Test it on the comeback raw video.
3. **Faster render**: (a) move `public/videos/*/raw/` out of `public/` (Remotion copies the whole public dir — 1.2 GB,
   ~2 min — before every render and every still); (b) render **overlays only** on a transparent background and
   composite over `edit.mp4` with ffmpeg (expected 2-3x faster, same look); (c) optional Remotion Lambda (AWS account
   needed, a few cents per render, 1-2 min for 3 min) — only if the user agrees to an AWS account.
4. **Speed test**: render `purple-demo` (330 frames) in the cloud session and compare with the laptop
   (laptop: ~3.6 frames/s on the 3-min comeback render at 75 % concurrency, ~5,376 frames in ~25 min).
5. Add the Colab/cloud workflow and the "no mixed-script words" rule to the skill's **Learned rules** (§11),
   and update §1.2 (transcription on Colab), then copy the skill back.
6. Optional: better Darija text model to compare later — `atlasia/moulsot.v0.3` (Qwen3-ASR, tops a community Darija
   leaderboard, self-reported; unclear word timestamps → use for text, Whisper for timing).

## 6. Things that went wrong (don't repeat)

| Problem | Fix |
|---|---|
| Laptop CPU transcription ~45 s/segment | Colab GPU |
| Whisper large-v2 drifts into MSA, garbles French/English | Darija turbo model + EN/FR pass + user's script/post caption |
| Captions straddling a moment edge were moved to the top over the face | top only while `nowMs` is inside the moment |
| Center-origin push-ins pushed a low-framed face further down (face zone 78 %) | bottom-origin push-ins, manual faceZone 0.725 |
| `∞` missing from Inter Tight (tiny fallback glyph) | use words ("many") |
| Mixed Latin+Arabic tokens rendered scrambled | Darija spellings / separate words, check with the regex |
| Remotion copies 1.2 GB public dir before every still/render | move raw media out of `public/` |
| 285 MB final can't be sent to the phone | 720p ~25 MB preview |
| Laptop went to sleep mid-session | keep-awake for long renders; a closed lid still sleeps |
