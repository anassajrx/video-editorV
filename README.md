# video-editorV

The engine Claude Code uses to edit Moroccan Darija talking-head videos in the **Purple Room** style:
silences and every retake removed, -14 LUFS audio, soft grade, Darija captions (foreign words kept in their
original language), calm purple graphics and animation moments, music and SFX, an Arabic `.srt`, and a hard rule
that nothing is ever drawn over the face.

**Start here (Windows):** [`local/SETUP-WINDOWS.md`](local/SETUP-WINDOWS.md), then the prompts in
[`local/PROMPTS.md`](local/PROMPTS.md). The full runbook is the skill
[`.claude/skills/darija-video-edit-local/SKILL.md`](.claude/skills/darija-video-edit-local/SKILL.md).

Requirements: Git for Windows, Node.js 22, Python 3.12, FFmpeg (the setup prompt installs them).

```bash
npm ci
py -3.12 -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt
npx tsc --noEmit
```
