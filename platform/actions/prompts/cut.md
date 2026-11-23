You are running UNATTENDED on a GitHub Actions runner for the user's video platform. Job slug: `{SLUG}`.
Nobody can answer questions: when unsure, make the best choice and note it in `platform-out/cut-decisions.md`.

The user ticked Omni Flash and/or Change background, so this stage ONLY chooses the takes (the video work happens after,
on a GPU). Follow the skill `.claude/skills/darija-video-edit-local/SKILL.md` (read §0, §1.4.1, §1.5, §4, §10, §11).

- The Kaggle prep is done; its files are in `public/videos/{SLUG}/raw/`: in.mp4, phrases.json, second.json,
  removals.json (candidates only), cut.mp4.cuts.json, transcript.txt, meta.json.
- `transcript.txt`: `MS:` = MoulSot (the text), `AR:` = Whisper (its words carry the timings). No new transcription.
- User context: {CONTEXT} · User script (wins for the exact words): {SCRIPT}
- Report each step BEFORE starting it: `python3 platform/actions/progress.py retakes --msg "<what, English>"`.
- Never print transcript text in command output (public logs). Do not commit/push; do not edit platform/, .github/, .claude/.

Do:
1. Choose the takes like §1.5 step 2 / §4.2: keep the last COMPLETE take of each sentence; drop false starts,
   restarts, "3awd/mn jdid", rephrases; check cut points with `scripts/darija/cut_points.py` (§4.3).
   Write `public/videos/{SLUG}/raw/removals.json`.
2. `python3 -I scripts/darija/build_cut.py public/videos/{SLUG}/raw/cut.mp4.cuts.json public/videos/{SLUG}/raw/removals.json
   public/videos/{SLUG}/raw/segments.json --phrases=public/videos/{SLUG}/raw/phrases.json`
3. `platform-out/cut-decisions.md` (French, short): length before → after and the removal table (original times + reason).

Do NOT render anything, do NOT write captions or edit.json. Finish with a 2-line summary.
