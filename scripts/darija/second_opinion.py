"""Second-opinion transcripts for writing Darija captions. ONE command, ~8-10 min per minute of speech.

Usage:
  python3 -I scripts/darija/second_opinion.py <in.mp4> <phrases.json> <out.json> [--no-cpp]

Run it once, after transcribe_phrases.py. It does exactly two things, then stops:
  1. A FRENCH pass on every phrase of phrases.json (faster-whisper large-v2, model loaded ONCE).
     It recovers the French/English words (application, plateforme, personnalisation, impossible...)
     that the Arabic pass turns into MSA or nonsense.
  2. ONE whisper.cpp large-v3 run on the WHOLE clip (-mc 0), for sentence context and numbers.
     Never run whisper.cpp on many short clips: it reloads the 3 GB model for every call (~1-3 min
     each) and that wasted ~16 min on the second video.

Output: prints, per phrase, AR (from phrases.json) and FR side by side, then the whisper.cpp lines.
Write pages.txt from these three views; do NOT run more transcription passes after this one.
If the user gave a script, skip this tool entirely and use the script text.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

args = [a for a in sys.argv[1:] if not a.startswith("--")]
src, phrases_path, out_path = args
SR = 16000
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"],
                     check=True, capture_output=True).stdout
audio = np.frombuffer(pcm, dtype=np.float32)

from faster_whisper import WhisperModel  # noqa: E402

model = WhisperModel("large-v2", device="cpu", compute_type="int8")
phrases = json.load(open(phrases_path))["phrases"]
rows = []
for p in phrases:
    s, e = p["s"], p["e"]
    clip = audio[int(s * SR):int(e * SR)]
    segs, _ = model.transcribe(clip, language="fr", beam_size=5, condition_on_previous_text=False,
                               vad_filter=False, word_timestamps=True)
    words = [{"t": w.word.strip(), "s": round(s + w.start, 2), "e": round(s + w.end, 2)} for g in segs for w in g.words]
    ar = " ".join(w["t"] for w in p.get("words", [])) or p.get("text", "")
    fr = " ".join(w["t"] for w in words)
    print(f"{s:7.2f}-{e:7.2f}\n   AR: {ar}\n   FR: {fr}", flush=True)
    rows.append({"s": s, "e": e, "ar": ar, "fr": words})

cpp = []
binary = next((b for b in (os.path.join(".whisper", "main.exe"), os.path.join(".whisper", "main")) if os.path.exists(b)),
              os.path.join(".whisper", "main"))  # installed by `npm run transcribe` once (main.exe on Windows)
mdl = os.path.join(".whisper", "ggml-large-v3.bin")
if "--no-cpp" not in sys.argv and os.path.exists(binary) and os.path.exists(mdl):
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "full.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", "16000", "-ac", "1", wav], check=True)
        r = subprocess.run([binary, "-m", mdl, "-l", "ar", "-mc", "0", "-t", str(os.cpu_count() or 4), "-f", wav],
                           capture_output=True, text=True)
        print("\n== whisper.cpp large-v3, whole clip ==")
        print(r.stdout.strip())
        cpp = r.stdout.strip().splitlines()
else:
    print("\n(whisper.cpp skipped: run `npm run transcribe` once to install .whisper/main + large-v3, or --no-cpp)")

json.dump({"phrases": rows, "whisper_cpp": cpp}, open(out_path, "w"), ensure_ascii=False, indent=1)
print(f"\nwrote {out_path}")
