---
name: edit-skill
description: Edit a talking-head video in the user's tech personal-brand style with Remotion (kinetic mixed-type captions, glowing cyan cards, terminal graphics, punch-ins, B&W doubt moments). Use for any new video edit, re-edit, or round of notes in this repo.
---

# Edit skill: tech personal brand

> **#1 RULE (never break it): nothing is ever placed over the face or above it.** Captions and graphics live only below the chin. Run `face_zone.py` before layout and `check_face.py` before sending anything. See DESIGN.md §2.

You are the editor for a software engineer's personal brand. The look is defined in `DESIGN.md` and `brand/BRAND.md`, and the code in `src/` already implements it. Your job is to turn raw footage into a `src/videos/<slug>/edit.json`, get approval at each gate, and render.

Reference: a 43s vertical edit was analysed (`references/style-analysis.md`, contact sheets in `references/`). We copy its *structure and energy*, re-skinned from purple to our cyan/amber tech palette.

## Workflow (never skip a gate)

### 0. Intake
- Get the footage. If it's a Drive/Dropbox link, download it to `public/videos/<slug>/raw/`. Ask for the script if there is one, plus any screenshots/proof to show.
- Check it: `ffprobe` for resolution/fps/duration, and confirm where the face sits in the frame (extract one still and look at it).

### 1. Rough cut
- `npm run cut -- public/videos/<slug>/raw/in.mp4 public/videos/<slug>/cut.mp4`. Tune `--noise` if words get clipped (-40dB) or pauses remain (-30dB).
- Also remove retakes, false starts and repeated sentences: transcribe first, find the duplicates, and keep the last good take.
- Normalise audio to -14 LUFS: `ffmpeg -i cut.mp4 -af loudnorm=I=-14:TP=-1:LRA=7 -c:v copy cut-norm.mp4`.

### 2. Transcribe
- `npm run transcribe -- public/videos/<slug>/cut-norm.mp4 src/videos/<slug>/words.json` (`--model=medium` if not English).
- Fix misheard words using the script.

### 2b. Face zone
- `python3 scripts/face_zone.py src/videos/<slug>/edit.json` (run it after punch-ins are set, and again whenever they change). It writes `faceZone`; the layout clamps everything below it.

### 3. PLAN → wait for "approved"
Send a numbered table, one row per caption page:
`# | time | words (with roles) | graphic | footage (punch-in / B&W) | sfx`
Apply the story → visual mapping from DESIGN.md §6. One graphic every 3–5s, never two at once.

### 4. STILLS → wait for "approved"
- Write `edit.json`, register the slug in `src/Root.tsx`, then render one still per graphic: `npm run still -- <slug> out/<slug>/s<N>.png --frame=<F> --scale=0.4`.
- Run `python3 scripts/check_face.py <slug>`. It must print PASS. If it fails, fix the layout (fewer words per page, smaller punch-ins, no graphic during that caption) and rerun.
- Combine them into one contact sheet (`ffmpeg ... hstack`), look at it yourself first (face covered? text cut off? two accents in one frame?), then send it. Notes come back as "still 3: bigger".

### 5. DRAFT
- `npm run draft -- <slug> out/<slug>-draft.mp4` and send it.
- If it would take longer than ~8 minutes (videos over ~3 min), render on GitHub Actions instead (see README).

### 6. NOTES → fix → still → draft
- Ask for all notes in one message, with timestamps. Change `edit.json`, send stills of each fix, re-draft. Commit each round.
- If a note is a *taste rule* ("never…", "always…", "I hate…"), add it to **Learned rules** below and say so.

### 7. FINAL
- `npm run final -- <slug> out/<slug>-final.mp4` (or the GitHub Action). Verify loudness on the output, then send it.

## Caption role assignment (the signature look)
For each page of ≤5 words:
- Filler words (I, a, the, was, is, to, in, of, and, so, it, my) → `soft`
- The single most important word → `hero`, OR a colored role if it fits better:
  - tech / skill / action verb → `signal`
  - money, %, numbers, results → `ember`
  - code, tools, commands, file names → `mono`
  - doubt, fail, bug, stuck → `error` (use inside B&W ranges)
- Feelings, time, story words (weeks, finally, anyway, hated, love) → `serif`
- Everything else → `default`
- Max one of hero/signal/ember/mono/error per page. Break pages at commas and natural phrase ends.

## Darija captions (Moroccan Arabic videos)
- **Full step-by-step runbook, scripts and every known pitfall: `.claude/skills/darija-video-edit/SKILL.md`. Follow it for any Darija video.**
- Transcribe with `npm run transcribe -- <in.mp4> <words.json> --lang=ar` (defaults to the multilingual `large-v3` model; `--model=medium` if too slow).
- Write what is actually said in **Darija, in Arabic letters**. Never translate into Modern Standard Arabic, never "correct" Darija into formal Arabic.
- If whisper.cpp loops (same sentence repeated to the end) or drifts into MSA, use `python3 scripts/transcribe_fw.py <in.mp4> <words.json> --lang=ar --model=large-v2 --prompt="<a Darija sentence from the video>"` (faster-whisper, VAD, no previous-text conditioning). Re-transcribe any wordless stretch on its own before cutting it: it may hold words Whisper skipped.
- Before every retake/mistake cut, check the energy around the cut point and move it into a real valley; if the speech is continuous (no valley), keep the retake rather than cut mid-word.
- Whisper is weak at Darija: read the whole transcript for context and fix misheard words. Use common Darija spellings: كنقول، بزاف، دابا، واش، علاش، ديال، غادي، حيت، شي، هادشي.
- **Foreign words stay in their original language (rule of 2026-11-15):** English/French words spoken inside the Darija are written in that language, in Latin letters, as said (`flight`, `booking`, `website`, `workflow`, `les résultats`, `manuellement`). Never write them in Arabic letters. Brand/tool names stay Latin too (GitHub, React, Claude, ChatGPT). Darija articles/prefixes are a separate small word before them: `الـ website`, `فالـ cloud`.
- Word-by-word reveal, **max 4 words per page** (enforced in KineticCaptions for Arabic pages), page breaks at natural phrase ends.
- Roles: most words `default`; small filler words (و، ف، ل، اللي، هو، ديال، راه، غير) `soft`; ONE key word per page as `hero`, or `signal` for tech words, `ember` for money/numbers, `error` for problems.
- No punctuation at the end of caption pages.
- Rendering: Arabic words use Cairo (`fonts.arabic`, bundled in public/fonts) and Arabic pages are laid out `direction: rtl`. No letter-spacing on Arabic (it breaks letter joining); `serif` maps to Cairo 700 (Arabic has no italic).
- Check a contact sheet for disconnected/reversed letters and word order before rendering.
- Deliver an Arabic `.srt` with the video (one cue per caption page).

## Graphic picking
| Script says… | Use |
|---|---|
| introduces a person | `profile` (avatar from `public/brand/avatar.png` or a client photo) |
| from X to Y / journey / months | `timeline` (pin moves on the result word) |
| a product, project, skill, offer | `card` (signal; ember if paid/premium) |
| code, deploy, git, a bug, a command | `terminal` (realistic commands, max 4 lines) |
| one big number | `stat` (only if captions don't already show it big) |
| proof (tweet, dashboard, PR, analytics) | `image` with a screenshot in `public/videos/<slug>/` |

## Sound
- If the Epidemic Sound connector is available, use it for the music bed and SFX. Otherwise ask for files or use royalty-free ones the user provides. Never use unlicensed music.
- Music volume 0.08–0.15 under the voice. SFX: whoosh on card pops, keyboard clicks under the terminal, riser into the result, hit on ember numbers.

## Quality checklist (run before every send)
- [ ] `check_face.py` PASS: nothing over or above the face, chin and beard included
- [ ] No dead air > 0.25s; audio around -14 LUFS
- [ ] Every page has mixed roles; no page with two accent words
- [ ] Never two graphics at once; graphics hold ≥ 1.5s
- [ ] First caption on frame 1; hook graphic in the first 3s
- [ ] Spelling of names, tools and numbers checked against the script

## Learned rules
<!-- Add the user's taste rules here as they come up, one line each, with the date. -->
- 2026-11-14: NEVER put captions or anything else over or above my face. Everything goes below the chin. (Enforced in code + check_face.py.)
- 2026-11-15: In Darija captions, English/French words stay in their ORIGINAL language and Latin letters (never transliterated into Arabic letters).
- 2026-11-15: ALL retakes must be removed. Whole-file Whisper merges repeated sentences into one, so never look for retakes in a whole-file transcript: transcribe every silence-cut segment (and every phrase between micro-pauses) on its own, list each line, keep only the last complete take, then re-transcribe the final cut to confirm every line appears once. Also cut the short no-word segments (breaths, mouth noise, "euh"; Whisper hallucinates "اشتركوا في القناة"/"شكرا" on them). Time captions from per-phrase word timestamps, not whole-file ones.
