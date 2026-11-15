# DESIGN.md — Video design system

Source of truth for how every video looks and moves. Tokens live in `src/brand/theme.ts` (mirrors `brand/brand.json`).
Derived from the reference edit (`.claude/skills/edit-skill/references/`) and re-skinned for a tech brand.

## 1. Format
- Default: **vertical 1080x1920, 30fps**. Horizontal 1920x1080 uses the same components (`orientation: "horizontal"`).
- Loudness: **-14 LUFS integrated** (the reference measured -14.1), true peak ≤ -1 dBTP.
- Pace: **~3.5–4 words/second**, **zero dead air**. The reference has no pause longer than 0.25s.

## 2. Layout zones (vertical): THE FACE RULE
**Hard rule, no exceptions: nothing is ever drawn over the face or above it.** No captions, cards, avatars, stickers, emojis or glows over the forehead, eyes, mouth, beard/chin, or the space above the head.

The face area is **measured per video** by `scripts/face_zone.py`, which detects the face in every second of footage and accounts for the zoom-ins. It is stored as `faceZone` in `edit.json`. The layout is computed from it (`src/brand/layout.ts`):
```
0%   ┌──────────────┐
     │  ABOVE HEAD  │  ❌ forbidden
     │  FACE ZONE   │  ❌ forbidden (hair → chin/beard + margin)
fb   ├──────────────┤  fb = faceZone.bottom (measured)
     │  CAPTIONS    │  start at fb + 2%, band of 13%
     ├──────────────┤
     │  GRAPHICS    │  cards / terminal / profile / timeline start here
94%  ├──────────────┤
     │  safe margin │
100% └──────────────┘
```
- Captions and graphics are top-anchored and **clamped** so they can never move above these lines, even if an `edit.json` asks for it.
- `scripts/check_face.py <slug>` renders the edit with the footage hidden and fails if a single pixel is drawn in the face zone. **It must PASS before any still, draft or final is sent.**
- If `faceZone.bottom` > 0.62, the face is framed too big for both captions and graphics. Use smaller punch-ins (max 1.08), show only one of caption/graphic at a time, or reframe when filming (eyes at about 1/4 from the top, chest visible).
- Side margins are 7% of the frame.

## 3. Captions (KineticCaptions)
- **Word-by-word reveal**, max **5 words per page**. Each word springs in: scale 0.7→1, 24px rise, blur 10→0, about 6 frames.
- **Mixed typography is the signature.** Each page mixes 2–3 roles:

| Role | Look | When |
|---|---|---|
| default | Inter Tight 700, 76px, white | normal words |
| soft | Inter Tight 500, 44px, grey | filler: I, a, the, was, to, in, and |
| hero | Inter Tight 800, 124px | the ONE word that matters on the page |
| serif | Instrument Serif italic, 104px | emotion / time / human words |
| signal | 800, 100px, cyan glow | tech concepts, the key verb |
| ember | 800, 112px, amber glow | money, numbers, results |
| mono | JetBrains Mono 600, cyan | code, tools, commands, file names |
| error | 800, red glow | doubt, failure, bugs (pair with B&W) |

- Rules: max **one** hero/ember/signal per page. End pages on natural phrase breaks (`pageBreakAfter`). Never all-caps whole sentences.

## 4. Graphic components (src/components/Overlays.tsx)
| Type | Use it when the script… | Reference equivalent |
|---|---|---|
| `profile` | introduces a person (you, a client, a user) | avatar bubble + bullet lines |
| `timeline` | describes progress from A → B | 9-5 → beginner → 2k/mo bar |
| `card` | names a product, feature, skill, offer | glowing glass cards |
| `terminal` | mentions code, deploy, a command, a bug | (tech replacement for tweet embeds) |
| `stat` | says a big number that IS the story | "$2000" moments |
| `image` | shows proof: screenshot, tweet, dashboard, PR | tweet/screenshot embeds |

- Pop in with a spring (scale 0.82→1, ~10 frames) and fade out over 8 frames. Glass cards have a 2px accent border plus an outer glow that pulses gently.
- Density: **one graphic every 3–5 seconds**, never two at once. Hold each for 1.5–3.5s.
- The accent color matches meaning: signal for tech/skill, ember for money/result, error for problems.

## 5. Footage treatment (Footage.tsx)
- A slow constant push-in (1.00 → 1.05 over the video).
- **Punch-ins** on jump cuts: alternate scale 1.0 ↔ 1.06–1.12 (smaller when the face is framed big) so cuts feel intentional. Punch in on emphasis words.
- **B&W "doubt" moments** (`monoRanges`): fully desaturate, use `error`/`serif` caption roles, 1–3s long, max 1–2 per video.
- Grade: soft-light cyan tint (22%), vignette, bottom gradient for caption legibility.

## 6. Story → visual mapping (from the reference structure)
1. **Hook (0–3s):** the result first ("now he makes $2,000/mo") plus a stat or timeline. Captions start on frame 1.
2. **Struggle:** profile card and timeline at the start position. Soft/serif captions.
3. **Doubt:** B&W plus error words.
4. **Turning point:** a signal word plus terminal/card graphics. Return to color.
5. **Result:** ember words, card in ember, timeline pin moves to the end.
6. **CTA:** mono command-style or hero word ("comment SHIP"), plus the logo mark.

## 7. Sound
- Music bed ducked to about **-26 LUFS under the voice** (around volume 0.08–0.15). The voice is always on top.
- SFX: a soft *whoosh* on every card pop, a *click/type* under terminal text, a *riser* into the result, a *bass hit* on ember numbers. Max one SFX per second.

## 8. Don'ts
- Nothing over or above the face (see §2), no shapes or graphics behind the head, no emojis in captions.
- No stock "tech" clichés (matrix code rain, hoodie hacker, binary). Show real screens instead.
- No more than 2 accent colors in one frame. No transitions that spin or flip.
