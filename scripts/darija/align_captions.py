"""Time hand-written Darija caption pages against the audio, write them into edit.json + an .srt.

Usage:
  python3 -I scripts/darija/align_captions.py <pages.txt> <phrases.json> <segments.json> <edit.json> <out.srt>

<pages.txt>     YOUR caption text, one caption page per line, in spoken order (max 4 words):
                  واش/s عارف/h بلي/s
                  الـ/s AI/g دابا
                  AI_Agent/g          (underscore = one caption word containing a space)
                  تبعني/h @153.67-154.33   (optional: force this page to SOURCE seconds)
                roles: d=default s=soft h=hero g=signal e=ember r=error m=mono v=serif (default d)
                lines starting with # are comments
<phrases.json>  from transcribe_phrases.py (word timestamps, SOURCE seconds)
<segments.json> from build_cut.py (the kept segments actually rendered)

How: the caption words are aligned to Whisper's phrase-level words with a fuzzy, Darija-aware
sequence alignment (Needleman-Wunsch). Matched words take Whisper's times, unmatched words are
interpolated between neighbours, '@' pages are spread over the forced range. Source times are
then mapped onto the final (cut) timeline, frame-snapped exactly like render-segments.mjs.
It prints every page next to what Whisper heard: read it and add '@' ranges where they disagree.
"""
import json
import re
import sys
from difflib import SequenceMatcher

pages_path, phrases_path, seg_path, edit_path, srt_path = sys.argv[1:6]
ROLE = {"d": "default", "s": "soft", "h": "hero", "g": "signal", "e": "ember", "r": "error", "m": "mono", "v": "serif"}

pages = []  # [{"words":[{text, role}], "force":(s,e)|None}]
for line in open(pages_path, encoding="utf8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    force = None
    m = re.search(r"@([\d.]+)-([\d.]+)\s*$", line)
    if m:
        force = (float(m.group(1)), float(m.group(2)))
        line = line[: m.start()].strip()
    ws = []
    for tok in line.split():
        text, _, r = tok.partition("/")
        ws.append({"text": text.replace("_", " "), "role": ROLE.get(r or "d", r or "default")})
    assert 1 <= len(ws) <= 4, f"page must have 1-4 words: {line}"
    assert sum(w["role"] in ("hero", "signal", "ember", "error", "mono") for w in ws) <= 1, f"max one accent per page: {line}"
    pages.append({"words": ws, "force": force})

segs = json.load(open(seg_path))
snap = lambda t: round(t * 30) / 30
fs, t = [], 0.0
for a, b in segs:
    a2, b2 = snap(a), snap(b)
    if b2 - a2 < 1 / 30:
        continue
    fs.append((a2, b2, t))
    t += b2 - a2
DUR = t
inside = lambda v: any(a - 0.02 <= v <= b + 0.02 for a, b, _ in fs)


def s2f(v):
    for a, b, o in fs:
        if a - 0.01 <= v <= b + 0.01:
            return o + min(max(v, a), b) - a
        if v < a:
            return o
    return DUR


src = [w for p in json.load(open(phrases_path))["phrases"] for w in p["words"] if inside((w["s"] + w["e"]) / 2)]
src.sort(key=lambda w: w["s"])


def norm(s):
    s = s.lower()
    s = re.sub(r"[ً-ٟـ.,!?؟،:]", "", s)
    for x, y in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ذ", "د"), ("ث", "ت"), ("ظ", "ض")):
        s = s.replace(x, y)
    return re.sub(r"^(وال|فال|بال|ال|و|ف)", "", s) if len(s) > 3 else s


LAT = {"ai": "اي", "agent": "جينت", "agents": "جينت", "chatgpt": "جبتي", "excel": "اكسل"}


def sim(x, y):
    x, y = norm(x), norm(y)
    for k, v in LAT.items():
        x, y = x.replace(k, v), y.replace(k, v)
    return SequenceMatcher(None, x, y).ratio()


flat = [(pi, w) for pi, p in enumerate(pages) for w in p["words"]]
n, m = len(flat), len(src)
G = -0.35
S = [[0.0] * (m + 1) for _ in range(n + 1)]
B = [[0] * (m + 1) for _ in range(n + 1)]
for x in range(1, n + 1):
    S[x][0], B[x][0] = x * G, 1
for y in range(1, m + 1):
    S[0][y], B[0][y] = y * G, 2
for x in range(1, n + 1):
    for y in range(1, m + 1):
        c = [S[x - 1][y - 1] + (sim(flat[x - 1][1]["text"], src[y - 1]["t"]) - 0.45) * 2, S[x - 1][y] + G, S[x][y - 1] + G]
        k = max(range(3), key=lambda q: c[q])
        S[x][y], B[x][y] = c[k], k
match, x, y = {}, n, m
while x > 0 and y > 0:
    k = B[x][y]
    if k == 0:
        if sim(flat[x - 1][1]["text"], src[y - 1]["t"]) >= 0.34:
            match[x - 1] = y - 1
        x, y = x - 1, y - 1
    elif k == 1:
        x -= 1
    else:
        y -= 1

st, en = [None] * n, [None] * n
for i, j in match.items():
    st[i], en[i] = src[j]["s"], src[j]["e"]
k = 0
for p in pages:  # forced ranges override
    if p["force"]:
        a, b = p["force"]
        L = sum(max(len(w["text"]), 2) for w in p["words"])
        t0 = a
        for q, w in enumerate(p["words"]):
            dt = (b - a) * max(len(w["text"]), 2) / L
            st[k + q], en[k + q] = t0, t0 + dt
            t0 += dt
    k += len(p["words"])
i = 0
while i < n:  # interpolate the rest
    if st[i] is None:
        j = i
        while j < n and st[j] is None:
            j += 1
        a = en[i - 1] if i > 0 else (src[0]["s"] if src else 0)
        b = st[j] if j < n else (src[-1]["e"] if src else a + 1)
        for q in range(j - i):
            st[i + q], en[i + q] = a + (b - a) * q / (j - i), a + (b - a) * (q + 1) / (j - i)
        i = j
    else:
        i += 1

words = []
for i, (pi, w) in enumerate(flat):
    a = s2f(st[i])
    b = max(s2f(en[i]), a + 0.08)
    last = i + 1 == n or flat[i + 1][0] != pi
    words.append({"text": w["text"], "startMs": round(a * 1000), "endMs": round(b * 1000), "role": w["role"],
                  **({"pageBreakAfter": True} if last else {})})
for x, y in zip(words, words[1:]):
    y["startMs"] = max(y["startMs"], x["startMs"])
    y["endMs"] = max(y["endMs"], y["startMs"] + 60)

spec = json.load(open(edit_path))
spec["captions"] = words
spec["durationMs"] = round(DUR * 1000)
json.dump(spec, open(edit_path, "w"), ensure_ascii=False, indent=2)


def ts(v):
    ms = int(round(v * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


cues, cur = [], []
for w in words:
    cur.append(w)
    if w.get("pageBreakAfter"):
        cues.append(cur)
        cur = []
out = []
for k, c in enumerate(cues):
    end = c[-1]["endMs"] / 1000 + 0.25
    if k + 1 < len(cues):
        end = min(end, cues[k + 1][0]["startMs"] / 1000)
    out.append(f"{k + 1}\n{ts(c[0]['startMs'] / 1000)} --> {ts(end)}\n‫{' '.join(w['text'] for w in c)}‬\n")
open(srt_path, "w", encoding="utf8").write("\n".join(out))

k = 0
for p in pages:
    ids = [match.get(q) for q in range(k, k + len(p["words"]))]
    heard = " ".join(src[j]["t"] for j in ids if j is not None)
    flag = "  (forced)" if p["force"] else ("  <-- CHECK: nothing matched" if not heard else "")
    print(f"{words[k]['startMs'] / 1000:7.2f}  {' '.join(w['text'] for w in p['words']):34s} | heard: {heard}{flag}")
    k += len(p["words"])
print(f"matched {len(match)}/{n} words; duration {DUR:.2f}s; wrote captions to {edit_path} and {srt_path}")
