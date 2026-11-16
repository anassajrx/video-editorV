# CLAUDE.md — Video editing engine

This repo is the engine behind the user's video edits (Moroccan Darija talking-head videos, vertical 1080x1920).
Remotion renders; Python/ffmpeg scripts cut, transcribe and check. It is normally cloned as `engine/` inside the
user's local `video editor` folder (Windows).

**Before any edit, follow the skill `darija-video-edit-local` (`.claude/skills/darija-video-edit-local/SKILL.md`).**
It is the single source of truth: setup, pipeline, the "Purple Room" style, rules and every known pitfall.
Style reference: `local/style/purple-room-storyboard.png` (soft grade: `local/style/grade-compare.jpg`, middle image).

## Repo map
- `.claude/skills/darija-video-edit-local/` — the skill (master copy; the local folder keeps a copy)
- `local/` — Windows starter kit: `SETUP-WINDOWS.md`, `PROMPTS.md`, `style/` reference images
- `src/brand/` — theme tokens, layout, `EditSpec` types (the edit format)
- `src/components/` — KineticCaptions, Footage (push-ins, B&W), Overlays, Icons (+ `purple/` once built)
- `src/EditTemplate.tsx` — renders any `EditSpec`; `src/Root.tsx` registers one composition per video
- `src/videos/<slug>/edit.json` — one folder per video; `brand-demo` is the setup test composition
- `public/fonts/` — bundled fonts · `public/music/lofi-bed.m4a` — licensed music bed · `public/videos/<slug>/` — per-video media (raw/ is git-ignored)
- `scripts/cut-silences.mjs`, `scripts/render-segments.mjs` — silence cut, low-memory segment render
- `scripts/transcribe.mjs` — whisper.cpp (installs `.whisper/`)
- `scripts/darija/` — transcribe_phrases (retakes), second_opinion (captions), cut_points, build_cut, align_captions, `pages.example.txt`
- `scripts/face_zone.py`, `scripts/check_face.py` (+ `scripts/models/`) — the face rule
- `scripts/make_sfx.py` — original sound effects

## Rules
- **#1: Nothing is ever drawn over the user's face or above it, including captions.** `check_face.py <slug>` must PASS
  before any still, draft or final is sent.
- All retakes removed; captions in Darija with foreign words kept in their original language; Purple Room style.
- Edits change `edit.json` first; only touch components when the style itself changes.
- Raw footage and renders are never committed (`public/videos/*/raw/`, `out/`).
- A note that should apply to every future video goes into the skill's "Learned rules".
- Commit after every delivered round: `<slug>: final edit` / `<slug>: round N notes`.
