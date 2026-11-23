You are running UNATTENDED on a GitHub Actions runner for the user's video platform. Job slug: `{SLUG}`.
Nobody can answer questions: when unsure, make the best choice and list it in `platform-out/report.md`.

The storyboard stage already made this edit and the user reviewed it. Everything is restored in the repo:
`public/videos/{SLUG}/raw/` (edit.mp4 = final cut, graded, -14 LUFS; phrases.json; segments.json; meta.json),
`src/videos/{SLUG}/` (edit.json, pages.txt, .srt) and src/Root.tsx. `platform-out/storyboard.md` is what the user saw.

Follow the skill `.claude/skills/darija-video-edit-local/SKILL.md` (read §0, §6, §7, §8, §9, §10, §11) with these
PLATFORM OVERRIDES: no Drive tools, no new transcription, never print transcript text in commands' output (public logs),
do not commit/push, do not edit `platform/`, `.github/`, `.claude/`. Report each step BEFORE starting it:
`python3 platform/actions/progress.py <step> --msg "<what you are doing, English>"`.

The user's review:
"""
{NOTES}
"""

1. `progress.py notes` — Apply every note exactly (captions wording, graphics, timing...). If a note asks for a re-cut
   or a retake change, do it from in.mp4 like the storyboard stage did (build_cut → render-segments → loudness → grade),
   then re-run align_captions.py. If a note is impossible, say so in report.md.
2. `progress.py sfx` — Sound effects (§8: `scripts/fetch_sfx.py` / `scripts/auto_sfx.py`, else `make_sfx.py`), music
   bed levels, the B&W silence beat.
3. `progress.py qa` — `npx tsc --noEmit`; `python3 scripts/check_face.py {SLUG}` must PASS; one still per graphic/moment
   at its start + 0.9 s at `--scale=0.3`, LOOK at them (Arabic joined & in order, nothing cut off). Fix and re-check.
4. Write `platform-out/report.md` (French, short): what changed from the storyboard, notes applied, anything skipped.

Do NOT render the video: the platform renders it right after you finish (scripts/render-chunks.mjs {SLUG}).
Finish with a 3-line summary.
