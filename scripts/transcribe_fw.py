"""Word-level transcription with faster-whisper (fallback for Darija / dialects).

Usage:  python3 scripts/transcribe_fw.py <input> <output.json> [--lang=ar] [--model=large-v2]
                [--from=SEC] [--to=SEC] [--prompt="..."]

Why: whisper.cpp large-v3 (npm run transcribe) tends to loop ("same sentence repeated to the
end") and drift into Modern Standard Arabic on Moroccan Darija. faster-whisper with VAD,
no conditioning on previous text and large-v2 is far more stable. Output format is the same
as transcribe.mjs: [{text, startMs, endMs}], timestamps relative to the full clip.
Model weights are downloaded from Hugging Face on first use (~3 GB, cached).
"""
import json
import os
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
if len(args) < 2:
    print(__doc__)
    sys.exit(1)
src, out = args[0], args[1]
lang = opt.get("lang", "ar")
model_name = opt.get("model", "large-v2")
t0 = float(opt.get("from", 0))
t1 = opt.get("to")

# Decode with ffmpeg to 16 kHz mono float32 (avoids PyAV version issues).
cmd = ["ffmpeg", "-hide_banner", "-v", "error", "-ss", str(t0)]
if t1 is not None:
    cmd += ["-to", str(t1)]
cmd += ["-i", src, "-f", "f32le", "-ar", "16000", "-ac", "1", "-"]
audio = np.frombuffer(subprocess.run(cmd, check=True, capture_output=True).stdout, dtype=np.float32)

model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
segments, info = model.transcribe(
    audio,
    language=lang,
    beam_size=5,
    word_timestamps=True,
    condition_on_previous_text=False,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 300},
    initial_prompt=opt.get("prompt"),
)
words = []
for seg in segments:
    for w in seg.words or []:
        text = w.word.strip()
        if not text:
            continue
        words.append({
            "text": text,
            "startMs": round((w.start + t0) * 1000),
            "endMs": round((w.end + t0) * 1000),
        })
    print(f"[{seg.start + t0:7.2f} -> {seg.end + t0:7.2f}] {seg.text.strip()}", flush=True)

json.dump(words, open(out, "w"), ensure_ascii=False, indent=2)
print(f"Wrote {len(words)} words to {out}")
