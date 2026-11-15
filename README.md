# video-editor: your cloud editing desk

Everything runs in **Claude Code on the web** (claude.ai/code). Nothing gets installed on your laptop.

## The face rule
Nothing is ever drawn over or above your face. The system measures your face in every video and keeps captions and graphics below your chin, and an automatic check blocks any render that breaks this.

## One-time setup (≈20 min)
1. **Create a private GitHub repo** called `video-editor` and upload this folder's contents (GitHub web → "Add file → Upload files" works; drag everything in, including the hidden `.claude` and `.github` folders).
   - Easier: in a Claude Code web session, ask Claude to push this zip to your new repo.
2. **Open claude.ai/code**, choose the repo, and create an environment. Set **network access to "Full"** (or add `drive.usercontent.google.com`, `dropbox.com` and `registry.npmjs.org` to the allowed list) so Claude can download your footage.
3. Personalise the brand: put your name and handle in `brand/brand.json` and `brand/logo/wordmark.svg`. Replace `public/brand/avatar.png` with a clean headshot.
4. *(Optional)* Connect **Epidemic Sound** in claude.ai → Settings → Connectors for licensed music and SFX.

## Every video
1. Upload the raw clip to Google Drive and set sharing to **"Anyone with the link"**.
2. New Claude Code session on the repo. Paste:
   > New video, slug `my-first-video`. Footage: <drive link>. Script: <paste or "none">. Proof to show: <screenshots/links>. Follow the edit skill.
3. Claude rough-cuts, transcribes, then sends the **PLAN**. Reply `approved` or send notes.
4. Claude sends the **STILLS** contact sheet. Reply `approved` or send notes ("still 3: bigger").
5. Claude renders a **draft** and sends it. Send **all notes in one message** with timestamps.
6. When it's right: `render final`. Short videos render in the session (the 12.6s demo took ~54s). For long ones, use GitHub → **Actions → Render video → Run workflow** (slug, `final`), then download from *Artifacts*.
7. Tell Claude "add that to the skill" for any rule you never want to repeat.

## Where to keep large footage
Git can't hold big videos (100MB/file limit). Keep raw footage in Drive. Only the *edited* `cut-norm.mp4` is needed for rendering: commit it if it's under 100MB, or pass a direct link in the Action's `footage_url` field.

## Licence note
Remotion is free for individuals and companies of up to 3 people. Bigger companies need a company licence (remotion.pro).
