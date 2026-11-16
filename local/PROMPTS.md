# Prompts to paste into Claude Code (Windows)

Open Claude Code inside your `video editor` folder first (`cd "$HOME\Documents\video editor"` then `claude`).

---

## PROMPT 1 — Install everything (once)

```
Set up this computer to edit my videos. Read .claude/skills/darija-video-edit-local/SKILL.md first and follow
section 1 (one-time setup) exactly. This is a Windows PC.

1. Check which tools are already installed: Git, Node.js (20.19+ or 22 LTS), Python 3.12, FFmpeg + ffprobe,
   GitHub CLI. Install only the missing ones with winget, one at a time. Tell me before each install that Windows
   may ask me for permission.
2. If the PATH needs a new terminal after installing, tell me exactly when to close and reopen Claude Code, and
   continue from where you stopped when I say "continue the setup".
3. Log me in to GitHub with `gh auth login` (I'll do the browser part), then clone the private repo
   anassajrx/video-editorv into a folder named "engine" inside this folder.
4. In engine/: npm ci, create the Python 3.12 venv (.venv), pip install -r requirements.txt, npx tsc --noEmit.
5. Warm up the speech models once (faster-whisper large-v2 and whisper.cpp large-v3) so the first edit is fast.
   Tell me the download size before starting and give me a progress line every few minutes.
6. Render one test still of the brand-demo composition to check Remotion works, and show it to me.
7. Never touch "raw footage/". Always quote paths (they contain spaces).

Finish with a checklist: each tool + version with ✅ or ❌, the engine path, the free disk space left, and anything
I still need to do.
```

---

## PROMPT 2 — Build the "Purple Room" style into the engine (once, after PROMPT 1)

```
Read .claude/skills/darija-video-edit-local/SKILL.md, section 6 (Purple Room style) and section 1.3, and look at
references/purple-room-storyboard.png and references/grade-compare.jpg (the approved grade is the MIDDLE image,
"SOFT", not the strong one).

In engine/, build the Purple Room style once:
1. Add the Alexandria font (npm @fontsource/alexandria, weights 600 and 800, arabic subset) to public/fonts and
   register it in src/brand/theme.ts. Arabic captions in this style use Alexandria, not Cairo.
2. Add the Purple Room tokens (plum, violet, lilac, white, muted) to the theme.
3. Build every component listed in the skill's table 6.3 in src/components/purple/, add their types to
   src/brand/types.ts and render them in src/EditTemplate.tsx. Follow the motion rules in 6.2 (ease-in-out, 0.5–0.9 s,
   no bounce, one object per frame). Keep the face rule: under-chin cards only, full-screen moments only when the
   face is not on screen.
4. Make a demo composition "purple-demo" that shows each component for 3 seconds on a sample clip, render one still
   per component, put them in one contact sheet in results/purple-demo/, look at it yourself, then show it to me.
5. npx tsc --noEmit, run check_face.py on the demo (must PASS), commit "purple-room: components" and push.

Keep it calm and minimal like the storyboard. Ask me only if something in the storyboard is unclear.
```

---

## PROMPT 3 — Edit a video (every time)

```
/darija-video-edit-local Edit the newest video in "raw footage/".
```

Optional additions to that line:
- `one shot` — no storyboard approval, deliver the final directly.
- `Here is the script: ...` — paste what you said; captions are more accurate and it's faster.
- `slug: my-video-name` — choose the folder name in results/.
- `no music` / `no end card` / `keep it under 60 s`.

After you receive the video, give notes with timestamps in one message, e.g.
`0:12 the caption says X, it should be Y · 0:40 cut the pause · make the music lower`.
If a note should apply to every future video, say "add this as a rule" — it goes into the skill's Learned rules.
