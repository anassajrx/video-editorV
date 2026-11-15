"""Phrase-level transcription of a silence-cut clip, used to FIND RETAKES and to time captions.

Usage:
  python3 -I scripts/darija/transcribe_phrases.py <in.mp4> <cuts.json> <out.json> [--model=large-v2]

<in.mp4>    the clip the silence cut was made FROM (e.g. public/videos/<slug>/raw/in.mp4)
<cuts.json> the <cut>.cuts.json written by `npm run cut` (kept speech segments, source times)

Why per segment / per phrase: whole-file Whisper MERGES repeated sentences into one, so
retakes are invisible in a whole-file transcript. Short pieces are transcribed on their own
(no VAD, no prompt, no previous-text conditioning), so every take shows up.

Output JSON:
  segments: [{i, s, e, text, junk}]  one per silence-cut segment (junk = no real words:
            breath / mouth noise / "euh"; Whisper hallucinates "اشتركوا في القناة" or "شكرا" there)
  phrases:  [{s, e, text, words:[{t, s, e}]}]  segments split at micro-pauses (>=80 ms dips)
All times are SOURCE seconds (times in <in.mp4>).
Printed: one line per segment and phrase, to read the takes and spot repeats.
"""
import json
import os
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
src, cuts_path, out = args
SR = 16000
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"],
                     check=True, capture_output=True).stdout
a = np.frombuffer(pcm, dtype=np.float32)
cuts = json.load(open(cuts_path))["cuts"]
model = WhisperModel(opt.get("model", "large-v2"), device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)

HALLU = ("اشتركوا", "شكرا", "ترجمة", "نانسي", "subscribe")


def tr(s, e, words=False):
    seg, _ = model.transcribe(a[int(s * SR):int(e * SR)], language="ar", beam_size=5, word_timestamps=words,
                              vad_filter=False, condition_on_previous_text=False)
    seg = list(seg)
    text = " ".join(x.text.strip() for x in seg).strip()
    ws = [{"t": w.word.strip(), "s": round(w.start + s, 3), "e": round(w.end + s, 3)}
          for x in seg for w in (x.words or [])] if words else []
    return text, ws


def db(s, e):
    x = a[int(s * SR):int(e * SR)]
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9) if len(x) else -99


segments, phrases = [], []
for i, c in enumerate(cuts):
    s, e = c["sourceStart"], c["sourceEnd"]
    text, _ = tr(s, e)
    junk = (e - s < 0.5 and (not text or any(h in text for h in HALLU))) or not text
    segments.append({"i": i, "s": round(s, 3), "e": round(e, 3), "text": text, "junk": junk})
    print(f"SEG {i:3d} {s:8.2f}-{e:8.2f} {'JUNK ' if junk else ''}| {text}", flush=True)
    if junk:
        continue
    # split at micro-pauses (>= 80 ms, 12 dB under the segment median), pieces >= 0.6 s
    hop = 0.01
    d = np.array([db(s + k * hop, s + (k + 1) * hop) for k in range(int((e - s) / hop))])
    low = d < np.median(d) - 12
    pts, k = [], 0
    while k < len(low):
        if low[k]:
            j = k
            while j < len(low) and low[j]:
                j += 1
            if (j - k) * hop >= 0.08 and k > 0 and j < len(low):
                pts.append(s + (k + j) / 2 * hop)
            k = j
        else:
            k += 1
    b = [s]
    for x in pts:
        if x - b[-1] >= 0.6:
            b.append(x)
    if e - b[-1] < 0.6 and len(b) > 1:
        b.pop()
    b.append(e)
    for x, y in zip(b, b[1:]):
        t, ws = tr(x, y, words=True)
        phrases.append({"s": round(x, 3), "e": round(y, 3), "text": t, "words": ws})
        print(f"    {x:8.2f}-{y:8.2f} | {t}", flush=True)

json.dump({"segments": segments, "phrases": phrases}, open(out, "w"), ensure_ascii=False, indent=1)
print(f"Wrote {out}: {len(segments)} segments ({sum(s['junk'] for s in segments)} junk), {len(phrases)} phrases")
