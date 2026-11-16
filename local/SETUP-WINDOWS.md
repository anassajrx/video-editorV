# Set up your Windows PC to edit videos with Claude Code

About 30–45 minutes the first time (mostly downloads). After that, every edit is one sentence.

## What's in this kit

```
video-editor-kit/
├── SETUP-WINDOWS.md                          <- this guide
├── PROMPTS.md                                <- the 3 prompts you paste into Claude Code
├── darija-video-edit-local/SKILL.md          <- the skill (all the rules, steps and fixes)
└── references/
    ├── purple-room-storyboard-v4.png         <- the approved style (storyboard)
    └── grade-compare.jpg                     <- the approved grade = the MIDDLE image ("SOFT")
```

---

## Step 1 — Create the folder

1. Open **File Explorer** → **Documents** (or `C:\`). Avoid Desktop/OneDrive if you can: OneDrive syncing slows renders.
2. Create a folder named **`video editor`**, and inside it three folders:
   - `references`
   - `raw footage`
   - `results`
3. Copy the two images from this kit's `references/` folder into your `video editor\references\`.
4. Create the folders `video editor\.claude\skills\darija-video-edit-local\` and copy **`SKILL.md`** into it.
   (Folders starting with a dot are fine on Windows. If Explorer refuses, create it in step 3 with PowerShell:
   `mkdir "$HOME\Documents\video editor\.claude\skills\darija-video-edit-local"`.)

Result:
```
Documents\video editor\
├── .claude\skills\darija-video-edit-local\SKILL.md
├── references\   (the 2 images)
├── raw footage\
└── results\
```

## Step 2 — Install Git for Windows (Claude Code needs it)

Open **PowerShell** (Start menu → type "PowerShell" → Enter) and run:

```powershell
winget install --id Git.Git -e
```

Click **Yes** if Windows asks for permission. Then **close PowerShell**.

## Step 3 — Install Claude Code

Open a **new PowerShell** and run:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Close PowerShell and open a new one. Check it worked:

```powershell
claude --version
```

(If that fails: `winget install --id OpenJS.NodeJS.LTS -e`, reopen PowerShell, then `npm install -g @anthropic-ai/claude-code`.)

## Step 4 — Open Claude Code in your folder

```powershell
cd "$HOME\Documents\video editor"
claude
```

The first time, it opens your browser to log in with your Claude account. When it asks whether you trust this
folder, say **Yes**.

Type `/` and check that **darija-video-edit-local** appears in the list. If not, check step 1.4 and restart `claude`.

## Step 5 — Paste PROMPT 1 (install everything)

Open `PROMPTS.md`, copy **PROMPT 1**, paste it into Claude Code, press Enter.

- Claude installs Node, Python, FFmpeg and the GitHub CLI, downloads the editing engine and its packages.
- Windows will show permission pop-ups: click **Yes**.
- When it asks you to **log in to GitHub** (`gh auth login`), choose: GitHub.com → HTTPS → Login with a web browser,
  then paste the code it shows in the browser.
- When it says "close and reopen the terminal": type `/exit`, close PowerShell, open a new one, and run
  `cd "$HOME\Documents\video editor"` then `claude` again, then type: **continue the setup**.

At the end it prints a checklist with ✅ for every tool.

## Step 6 — Paste PROMPT 2 (build the Purple Room style, once)

This builds the purple graphics, the Alexandria font and the soft grade into the engine (~45 min, one time only).
It sends you a few test images to check.

## Step 7 — Edit a video (every time)

1. Drop your clip into `video editor\raw footage\`.
2. Open Claude Code in the folder (step 4) and paste **PROMPT 3**, or just type:
   `/darija-video-edit-local edit the new video`
3. You get a storyboard image to approve, then the final video in `video editor\results\<name>\`:
   the MP4, the `.srt` subtitles and a `report.md` (what was cut, which captions are guesses).

## Tips

- Laptop plugged in while rendering; close Chrome tabs and other heavy apps.
- Needs about **12 GB** of free disk for the speech models the first time.
- "Where are we?" works any time: Claude gives you the step and the time left.
- Want it to just finish without asking? Add **"one shot"** to your message.
- Have the script? Paste it in your message: captions come out more accurate and it's ~10 minutes faster.
