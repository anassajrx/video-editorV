# Video platform: setup (one time)

```
Website (Vercel) ──Run──▶ GitHub Actions ──push──▶ Kaggle T4: prep (convert, cut, MoulSot + Whisper)
      ▲   reads status.json every 3 s         │                         │ writes status.json + results
      └────────── Google Drive: My Drive/video-editor/jobs/<slug>/ ◀────┘
GitHub Actions + Claude (your Pro token): storyboard → you Accept / write notes → animations, SFX, render → Drive
```

Secrets go ONLY into GitHub (Settings → Secrets) / Kaggle / Vercel forms. Never paste them in a chat.

## Part 1: Google (Drive + Gmail access) ≈ 10 min

1. Open https://console.cloud.google.com → project menu (top left) → **New project** → name `video-platform` → Create → select it.
2. **APIs & Services → Library**: search **Google Drive API** → Enable. Back, search **Gmail API** → Enable.
3. **Google Auth Platform** (or "OAuth consent screen") → **Get started**:
   - App name `video-platform`, support email = yours → Next
   - Audience: **External** → Next → contact email = yours → Finish / Create.
4. **Data access** → **Add or remove scopes** → in "Manually add scopes" paste:
   `https://www.googleapis.com/auth/drive, https://www.googleapis.com/auth/gmail.send` → Add → Update → Save.
5. **Audience** → **Publish app** → Confirm (status: *In production*). Without this, the token dies after 7 days.
   The "unverified app" warning you'll see is normal: the app is yours only.
6. **Clients** → **Create client** → type **Web application** → name `video-platform` →
   *Authorized redirect URIs* → **Add URI** → `https://developers.google.com/oauthplayground` → Create.
   Keep the window: you need the **Client ID** and **Client secret**.
7. Get the refresh token: open https://developers.google.com/oauthplayground
   - ⚙️ (top right) → tick **Use your own OAuth credentials** → paste Client ID + Client secret → Close.
   - Left box "Input your own scopes": `https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/gmail.send`
     → **Authorize APIs** → choose your account → "Google hasn't verified this app" → **Advanced** →
     **Go to video-platform (unsafe)** → tick everything → Continue.
   - **Exchange authorization code for tokens** → copy the **Refresh token** (starts with `1//`).

## Part 2: Kaggle key ≈ 2 min
https://www.kaggle.com/settings → **API** → **Create New Token**.
- Old style: a `kaggle.json` downloads → open it: it has `"username"` and `"key"`.
- New style: a token starting with `KGAT_` is shown → copy it, and note your Kaggle username.

## Part 3: GitHub secrets ≈ 5 min
https://github.com/anassajrx/video-editorV/settings/secrets/actions → **New repository secret**, one by one:

| Name | Value |
|---|---|
| `GOOGLE_CLIENT_ID` | Client ID (Part 1 step 6) |
| `GOOGLE_CLIENT_SECRET` | Client secret |
| `GOOGLE_REFRESH_TOKEN` | Refresh token (Part 1 step 7) |
| `KAGGLE_USERNAME` | your Kaggle username |
| `KAGGLE_KEY` | the `key` from kaggle.json (old style) |
| `KAGGLE_API_TOKEN` | the `KGAT_...` token (new style; add this one OR `KAGGLE_KEY`) |

Then tell Claude "secrets done" + the Drive link of a short test video.

## Later (step 2 and 3 of the build)
- `CLAUDE_CODE_OAUTH_TOKEN`: on a computer with Node: `npm install -g @anthropic-ai/claude-code`, then
  `claude setup-token` → log in → copy the token → GitHub secret `CLAUDE_CODE_OAUTH_TOKEN`.
- Vercel account (free, "Continue with GitHub") and a GitHub fine-grained token for the website.

## Part 4: the website (Vercel) ≈ 10 min

### 4a. GitHub token for the website (lets the Run / Accept / Retry buttons start the jobs)
1. https://github.com/settings/personal-access-tokens/new
2. Token name `ve-website` · Expiration **1 year** (or custom) · Resource owner: you.
3. Repository access → **Only select repositories** → `video-editorV`.
4. Permissions → Repository permissions → **Actions: Read and write** (Metadata: Read-only is added automatically).
5. **Generate token** → copy it (starts with `github_pat_`). Keep it for 4b.

### 4b. Vercel
1. https://vercel.com/signup → **Hobby** → **Continue with GitHub**.
2. **Add New… → Project** → Import `video-editorV` (if it's not listed: "Adjust GitHub App Permissions" → allow it).
3. **Root Directory** → **Edit** → choose `platform/web` → Continue. Framework: Next.js (automatic).
4. **Environment Variables** — add these 8 (Name → Value):

| Name | Value |
|---|---|
| `APP_PASSWORD` | the password YOU will type to open the site (choose a strong one) |
| `APP_SECRET` | any long random text, ~40 characters (e.g. mash the keyboard); it signs your login cookie |
| `GOOGLE_CLIENT_ID` | same as in GitHub |
| `GOOGLE_CLIENT_SECRET` | same as in GitHub |
| `GOOGLE_REFRESH_TOKEN` | same as in GitHub |
| `GITHUB_TOKEN` | the `github_pat_…` token from 4a |
| `GITHUB_REPO` | `anassajrx/video-editorV` |
| `GITHUB_REF` | `main` |

5. **Deploy**. After ~1 min you get a link like `https://video-editor-v-xxxx.vercel.app`: open it, type your password.
