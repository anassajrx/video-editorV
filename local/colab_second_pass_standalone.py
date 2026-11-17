# ============================================================================
# STANDALONE English + French pass (run on ANOTHER Google account, at the same time as colab_transcribe.py)
# Finds the same phrases as colab_transcribe.py (same silence cut, same micro-pause split), then
# transcribes each phrase with the plain Whisper large-v3-turbo forced to English, then to French,
# so the foreign words come out in Latin letters.
#
# HOW TO USE
# 1. colab.research.google.com (other account) -> New notebook
# 2. Runtime -> Change runtime type -> T4 GPU -> Save
# 3. Paste this whole file into ONE cell, check VIDEO, press Run, Allow the Drive pop-up
# 4. Result in that account's Drive: MyDrive/darija-transcripts/<name>/second.json + second.txt
#    Share second.json "anyone with the link" and send the link to Claude.
# ============================================================================

# The video: Drive share link ("anyone with the link")
VIDEO = "https://drive.google.com/file/d/1y6cVwmcM_sPH-4NZ0zSG4ODpXuX9dKo7/view?usp=sharing"
BASE_MODEL = "openai/whisper-large-v3-turbo"
NOISE_DB = -38
MIN_SILENCE = 0.3
PAD = 0.1

import subprocess, sys, json, re, os

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers", "accelerate", "gdown"], check=True)

from google.colab import drive
drive.mount("/content/drive")

import numpy as np
import torch
import gdown
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline

assert torch.cuda.is_available(), "No GPU: Runtime -> Change runtime type -> T4 GPU, then run again."

m = re.search(r"/d/([\w-]+)|id=([\w-]+)", VIDEO)
file_id = m.group(1) or m.group(2)
src = f"/content/video_{file_id}"
if not os.path.exists(src):
    gdown.download(id=file_id, output=src, quiet=False)
OUT = f"/content/drive/MyDrive/darija-transcripts/video_{file_id[:8]}"
os.makedirs(OUT, exist_ok=True)

# ---------- same silence cut ----------
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                           capture_output=True, text=True, check=True).stdout.strip())
log = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-vn", "-af", f"silencedetect=n={NOISE_DB}dB:d={MIN_SILENCE}",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
keep, cursor = [], 0.0
for i, s in enumerate(starts):
    seg_end = min(dur, s + PAD)
    if seg_end - cursor > 0.15:
        keep.append((max(0.0, cursor), seg_end))
    cursor = max(0.0, (ends[i] if i < len(ends) else dur) - PAD)
if dur - cursor > 0.15:
    keep.append((cursor, dur))
print(f"Silence cut: {len(keep)} segments")

# ---------- audio + same micro-pause phrase split ----------
SR = 16000
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"],
                     check=True, capture_output=True).stdout
a = np.frombuffer(pcm, dtype=np.float32)


def db(s, e):
    x = a[int(s * SR):int(e * SR)]
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9) if len(x) else -99


def split(s, e):
    s, e = round(s, 3), round(e, 3)
    hop = 0.01
    d = np.array([db(s + k * hop, s + (k + 1) * hop) for k in range(int((e - s) / hop))])
    if len(d) == 0:
        return [(s, e)]
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
    return list(zip(b, b[1:]))


# ---------- plain Whisper large-v3-turbo, forced EN then FR ----------
proc = WhisperProcessor.from_pretrained(BASE_MODEL)
model = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL, torch_dtype=torch.float16).to("cuda").eval()
asr = pipeline("automatic-speech-recognition", model=model, tokenizer=proc.tokenizer,
               feature_extractor=proc.feature_extractor, torch_dtype=torch.float16, device="cuda")


def run(s, e, lang):
    clip = a[int(s * SR):int(e * SR)].copy()
    if len(clip) < SR * 0.15:
        return ""
    return asr({"raw": clip, "sampling_rate": SR}, generate_kwargs={"language": lang, "task": "transcribe"})["text"].strip()


rows = []
for i, (s, e) in enumerate(keep):
    for x, y in split(s, e):
        en, fr = run(x, y, "english"), run(x, y, "french")
        rows.append({"seg": i, "s": round(x, 3), "e": round(y, 3), "en": en, "fr": fr})
        print(f"SEG {i + 1:3d}/{len(keep)} {x:7.2f}-{y:7.2f} | EN: {en}\n                        | FR: {fr}", flush=True)

json.dump(rows, open(f"{OUT}/second.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
with open(f"{OUT}/second.txt", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(f"[{r['s']:7.2f}-{r['e']:7.2f}] EN: {r['en']}\n                  FR: {r['fr']}\n")
print("\nDONE. Saved in this account's Drive:", OUT, "(second.json, second.txt)")
