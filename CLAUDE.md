# CLAUDE.md — Video editing desk

This repo is a reusable video editing system. Remotion does the rendering. Every video follows the same brand, design system and workflow.

**Always use the `edit-skill` skill (`.claude/skills/edit-skill/SKILL.md`) before starting any edit in this repo.**
Then read `DESIGN.md` (look and motion) and `brand/BRAND.md` (brand). Do not invent new colors, fonts or component styles. Use the tokens in `src/brand/theme.ts`.

## Repo map
- `src/brand/` — theme tokens + `EditSpec` types (the edit format)
- `src/components/` — KineticCaptions, Footage (punch-ins, B&W, grade), Overlays (card, profile, timeline, terminal, stat, image)
- `src/EditTemplate.tsx` — renders any `EditSpec`
- `src/videos/<slug>/edit.json` — **one folder per video**; register it in `src/Root.tsx`
- `public/videos/<slug>/` — that video's footage, music, sfx, screenshots
- `scripts/cut-silences.mjs` — rough cut (removes pauses)
- `scripts/render-segments.mjs` — renders kept segments (low memory); used for retake re-cuts
- `scripts/transcribe.mjs` — word-level captions with Whisper (`--lang=ar` for Darija)
- `scripts/transcribe_fw.py` — faster-whisper fallback for Darija (no loops, stays in dialect)
- `scripts/face_zone.py` — measures where the face is (writes `faceZone`)
- `scripts/check_face.py` — fails if anything is drawn over/above the face

## Commands
- `npm run cut -- in.mp4 out.mp4` — remove silences
- `npm run transcribe -- in.mp4 words.json` — word timings (`--model=medium` for non-English)
- `npm run still -- <slug> out/x.png --frame=N --scale=0.4` — still for approval
- `npm run draft -- <slug> out/<slug>-draft.mp4` — quick low-res draft
- `npm run final -- <slug> out/<slug>-final.mp4` — full quality
- Long finals: push to GitHub and run the **Render video** GitHub Action (`.github/workflows/render.yml`)

## Rules
- **#1: Nothing is ever drawn over my face or above it, including captions.** Run `python3 scripts/face_zone.py src/videos/<slug>/edit.json` before layout and `python3 scripts/check_face.py <slug>` (must PASS) before sending any still, draft or final.
- I review a **plan** before anything is animated, and **stills** before the full render. Never skip these gates.
- Edits change `edit.json` first. Only touch components when the design system itself needs to change.
- When I give a note that should apply to every future video, add it to the edit skill's "Learned rules".
- Raw footage is not committed to git (too big). I give a Google Drive/Dropbox link; download it into `public/videos/<slug>/raw/` (git-ignored).
- Keep music low: my voice always sits on top.
- Commit after every approved round, with a message like `<slug>: round 2 notes`.
