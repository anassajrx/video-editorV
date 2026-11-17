# ============================================================================
# Darija transcription on Google Colab (GPU) with Whisper large-v3-turbo fine-tuned on Darija
#   -> phrases.json + cut.mp4.cuts.json  (same format as scripts/darija/transcribe_phrases.py,
#      so the local pipeline uses them unchanged: skill §3–§4.1)
#
# HOW TO USE (works from a phone browser too)
# 1. colab.research.google.com -> New notebook
# 2. Runtime -> Change runtime type -> T4 GPU -> Save
# 3. Paste this whole file into ONE cell, check VIDEO below, press Run
# 4. Allow the Google Drive pop-up (Colab reads the video from YOUR Drive)
# 5. ~2 min install + ~2 min model download + a few min transcription
# 6. Results are saved in your Drive: MyDrive/darija-transcripts/<video name>/
#      phrases.json  cut.mp4.cuts.json  transcript.txt
#    Then tell Claude: "the transcript is in Drive".
# ============================================================================

# The video: paste the Drive "Copy link" (link sharing: anyone with the link), or a Drive path like
# "/content/drive/MyDrive/my clip.MOV"
VIDEO = "https://drive.google.com/file/d/1y6cVwmcM_sPH-4NZ0zSG4ODpXuX9dKo7/view?usp=sharing"
BASE_MODEL = "openai/whisper-large-v3-turbo"
DARIJA_MODEL = "anaszil/whisper-large-v3-turbo-darija"    # Darija fine-tune (LoRA adapter on the base)
NOISE_DB = -38      # silence threshold (same as the skill: --noise=-38dB)
MIN_SILENCE = 0.3   # seconds
PAD = 0.1           # seconds kept around speech

import subprocess, sys, json, re, os

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers", "peft", "accelerate"], check=True)
# Colab ships an old torchao that makes peft refuse to load ("incompatible version of torchao"). We don't need it.
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao"], check=False)
if "torchao" in sys.modules or "peft" in sys.modules:
    raise SystemExit("torchao was removed. Now do: Runtime -> Restart session, then run this cell again.")

from google.colab import drive
drive.mount("/content/drive")

import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline

assert torch.cuda.is_available(), "No GPU: Runtime -> Change runtime type -> T4 GPU, then run again."

# VIDEO can be a Drive share link ("Copy link") or a Drive path
if VIDEO.startswith("http"):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gdown"], check=True)
    import gdown
    m = re.search(r"/d/([\w-]+)|id=([\w-]+)", VIDEO)
    assert m, f"Could not read the file id from the link: {VIDEO}"
    file_id = m.group(1) or m.group(2)
    local = f"/content/video_{file_id}"
    if not os.path.exists(local):
        gdown.download(id=file_id, output=local, quiet=False)
    name = f"video_{file_id[:8]}"
    VIDEO = local
else:
    assert os.path.exists(VIDEO), f"Video not found: {VIDEO}  (Files panel on the left -> drive -> MyDrive -> right-click the video -> Copy path)"
    name = os.path.splitext(os.path.basename(VIDEO))[0].strip().replace(" ", "_")
OUT = f"/content/drive/MyDrive/darija-transcripts/{name}"
os.makedirs(OUT, exist_ok=True)

# ---------- 1. silence cut (same rules as engine/scripts/cut-silences.mjs) ----------
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", VIDEO],
                           capture_output=True, text=True, check=True).stdout.strip())
log = subprocess.run(["ffmpeg", "-hide_banner", "-i", VIDEO, "-vn", "-af", f"silencedetect=n={NOISE_DB}dB:d={MIN_SILENCE}",
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
t, cuts = 0.0, []
for a_, b_ in keep:
    cuts.append({"sourceStart": round(a_, 3), "sourceEnd": round(b_, 3), "outStartMs": round(t * 1000)})
    t += b_ - a_
json.dump({"input": "public/videos/<slug>/raw/in.mp4", "removedSeconds": round(dur - t, 2), "cuts": cuts},
          open(f"{OUT}/cut.mp4.cuts.json", "w", encoding="utf-8"), indent=2)
print(f"Silence cut: {len(cuts)} segments, {dur:.1f}s -> {t:.1f}s")

# ---------- 2. load the Darija model ----------
processor = WhisperProcessor.from_pretrained(BASE_MODEL)
try:
    from peft import PeftModel
    base = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL, torch_dtype=torch.float16)
    model = PeftModel.from_pretrained(base, DARIJA_MODEL).merge_and_unload()
    print("Loaded Darija LoRA adapter on", BASE_MODEL)
except Exception as err:  # the repo may hold a full model instead of an adapter
    print("Adapter load failed, trying as a full model:", err)
    model = WhisperForConditionalGeneration.from_pretrained(DARIJA_MODEL, torch_dtype=torch.float16)
model = model.to("cuda").eval()
# word timestamps need the base model's alignment heads
model.generation_config = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL).generation_config
asr = pipeline("automatic-speech-recognition", model=model, tokenizer=processor.tokenizer,
               feature_extractor=processor.feature_extractor, torch_dtype=torch.float16, device="cuda")

SR = 16000
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", VIDEO, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"],
                     check=True, capture_output=True).stdout
a = np.frombuffer(pcm, dtype=np.float32)
HALLU = ("اشتركوا", "شكرا", "ترجمة", "نانسي", "subscribe")


def tr(s, e, words=False):
    clip = a[int(s * SR):int(e * SR)].copy()
    if len(clip) < SR * 0.15:
        return "", []
    kw = {"generate_kwargs": {"language": "arabic", "task": "transcribe"}}
    if words:
        kw["return_timestamps"] = "word"
    try:
        out = asr({"raw": clip, "sampling_rate": SR}, **kw)
    except Exception:  # very short clips can fail word alignment: fall back to text only
        out = asr({"raw": clip, "sampling_rate": SR}, generate_kwargs={"language": "arabic", "task": "transcribe"})
    text = out["text"].strip()
    ws = []
    for c in out.get("chunks") or []:
        ts = c.get("timestamp") or (None, None)
        if ts[0] is None:
            continue
        end = ts[1] if ts[1] is not None else ts[0] + 0.3
        ws.append({"t": c["text"].strip(), "s": round(ts[0] + s, 3), "e": round(end + s, 3)})
    return text, ws


def db(s, e):
    x = a[int(s * SR):int(e * SR)]
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9) if len(x) else -99


# ---------- 3. per-segment / per-phrase transcription (same logic as transcribe_phrases.py) ----------
segments, phrases = [], []
for i, c in enumerate(cuts):
    s, e = c["sourceStart"], c["sourceEnd"]
    text, _ = tr(s, e)
    junk = (e - s < 0.5 and (not text or any(h in text for h in HALLU))) or not text
    segments.append({"i": i, "s": round(s, 3), "e": round(e, 3), "text": text, "junk": junk})
    print(f"SEG {i + 1:3d}/{len(cuts)} {s:8.2f}-{e:8.2f} {'JUNK ' if junk else ''}| {text}", flush=True)
    if junk:
        continue
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
        t_, ws = tr(x, y, words=True)
        phrases.append({"s": round(x, 3), "e": round(y, 3), "text": t_, "words": ws})
        print(f"        {x:8.2f}-{y:8.2f} | {t_}", flush=True)

json.dump({"segments": segments, "phrases": phrases}, open(f"{OUT}/phrases.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
with open(f"{OUT}/transcript.txt", "w", encoding="utf-8") as f:
    for sg in segments:
        f.write(f"[{sg['s']:7.2f}] {'(junk) ' if sg['junk'] else ''}{sg['text']}\n")
print(f"\nDONE: {len(segments)} segments ({sum(x['junk'] for x in segments)} junk), {len(phrases)} phrases")
print("Saved in your Drive:", OUT)
