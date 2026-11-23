You are running UNATTENDED on a GitHub Actions runner for the user's video platform. Job slug: `{SLUG}`.
Nobody can answer questions: when unsure, make the best choice and list it under "Decisions to check" in storyboard.md.

Follow the skill `.claude/skills/darija-video-edit-local/SKILL.md` (read it first, fully: rules §0, §1.4.1, §1.5, §4,
§6, §7, §8, §10, §11) with these PLATFORM OVERRIDES:

- The Kaggle prep (= Colab Part A) is done. Its files are already in `public/videos/{SLUG}/raw/`: in.mp4, edit.mp4 (junk
  removed, retakes NOT cut, not graded), phrases.json, second.json, removals.json (candidates only), segments.json,
  cut.mp4.cuts.json, transcript.txt, meta.json, report.md. Do NOT run fetch_colab.py, gdown or any Drive tool.
- Transcription: `transcript.txt` shows `MS:` (MoulSot, the TEXT to use) and `AR:` (Whisper, its words in
  phrases.json carry the TIMINGS). Do NOT run any new transcription pass (no second_opinion.py, no whisper.cpp).
- User context (topic words): {CONTEXT}
- User script / reference caption (if given it WINS over both models for the exact words): {SCRIPT}
- Report each step BEFORE starting it (this drives the user's progress bar):
  `python3 platform/actions/progress.py <step> --msg "<what you are doing, in English, no transcript text>"`
  For loops with a known count you may add real numbers: `progress.py captions 12 40 pages`.
- Never print transcript/caption text in Bash commands' output beyond what you need (the logs are public).
- Do not commit, push, or edit files under `platform/`, `.github/`, `.claude/`.
- Runner: Ubuntu, 4 CPU, no GPU. For HTML screenshots use Playwright with
  `chromium.launch({ executablePath: '/usr/bin/google-chrome' })` (or plain `google-chrome --headless --screenshot`)
  if the bundled Playwright browser fails. Remotion stills work as usual (`npx remotion still`).

Steps:
1. `progress.py retakes` — Read transcript.txt + removals.json like §1.5 step 2 / §4.2: keep the last COMPLETE take of
   each sentence; drop false starts, restarts, rephrases; check cut points (§4.3). Write the final removals.json.
2. `progress.py cut` — Build the cut from in.mp4 (§1.5 step 4: build_cut.py → render-segments → §5.1 loudness → §5.2
   soft grade) → `public/videos/{SLUG}/raw/edit.mp4` (overwrite) + segments.json. Verify every kept line appears once.
3. `progress.py captions` — pages.txt (§7.2–7.3, foreign words in Latin) → align_captions.py → edit.json + .srt.
   Read meta.json `orientation` (vertical 1080x1920 or horizontal 1920x1080) for edit.json.
4. `progress.py graphics` — Plan the Purple Room graphics/moments in edit.json (§6, §8: face_zone.py, music bed
   `music/lofi-bed.m4a`), register the composition in src/Root.tsx, `npx tsc --noEmit`, and
   `python3 scripts/check_face.py {SLUG}` must print PASS. No SFX yet (final stage).
5. `progress.py storyboard` — The storyboard gate (§6.4): ONE image `platform-out/storyboard.png` (real graded frames
   from `npx remotion still` at the start of each scene + 0.9 s, one panel per scene, time, what is said, motion note,
   palette), deviceScaleFactor 2. LOOK at it (Read the PNG): Arabic joined and in order, nothing cut off.
   Then `platform-out/storyboard.md` (in French, short): length before → after, the removal table (original times +
   reason), the scene list (time · what is said · visual · motion), and "Decisions to check".

Finish with a 3-line summary. Do not render the full video.
