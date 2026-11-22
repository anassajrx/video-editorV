"""All-in-one Colab PREP for a Darija talking-head video (everything that needs no human/Claude judgement).

Google Drive in, Google Drive out:
  in : MyDrive/video-editor/raw footage/<clip>          (newest clip, or --video "<file name>")
  out: MyDrive/video-editor/results/<slug>/              (everything Claude Code needs, see bottom)

Colab (Runtime -> Change runtime type -> T4 GPU), ONE cell:
    from google.colab import drive; drive.mount('/content/drive')
    !wget -q -O colab_prep.py https://raw.githubusercontent.com/anassajrx/video-editorV/claude/hopeful-clarke-qhnr9z/local/colab/colab_prep.py
    !python colab_prep.py --slug my-video          # options: --video "IMG_1234.MOV"  --no-retakes  --no-grade

Steps (all automatic, ~5-10 min for a 5-min clip on a T4):
  1. convert to H.264 CFR 30 fps (fixes iPhone HEVC / rotation / VFR)        -> in.mp4
  2. silence cut (20 ms RMS, adaptive threshold, min 0.3 s, pad 0.1 s)        -> cut.mp4.cuts.json
  3. Darija transcription per segment + per phrase, word timestamps           -> phrases.json
     model: anaszil/whisper-large-v3-turbo-darija (LoRA on openai/whisper-large-v3-turbo)
  4. MoulSot v0.3 text pass on the same phrases (Darija + French/English words in Latin letters)
     -> phrases[i]["moulsot"] + second.json. Whisper above keeps the WORD TIMINGS; MoulSot gives the TEXT.
     (--text-model none, or MoulSot failing, falls back to the old Whisper EN + FR pass)
  5. automatic retake / false-start / junk detection, cut points moved into the quietest 10 ms
     (EDITABLE: Claude reviews it)                                             -> removals.json
  6. kept segments, frame-snapped, 8 ms fades, soft grade, two-pass loudness -14 LUFS / limiter
                                                                               -> segments.json, edit.mp4
  7. 720p preview for the phone + a readable report                           -> preview-720p.mp4, transcript.txt, report.md

Formats are IDENTICAL to the repo scripts (transcribe_phrases.py, build_cut.py, render-segments.mjs), so the
cloud session continues with align_captions.py / Remotion directly. All times in JSON are SOURCE seconds of in.mp4.
"""
import argparse
import difflib
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

T0 = time.time()
p = argparse.ArgumentParser()
p.add_argument("--slug", required=True)
p.add_argument("--video", default="", help="file name inside 'raw footage' (default: newest)")
p.add_argument("--root", default="/content/drive/MyDrive/video-editor")
p.add_argument("--work", default="/content/work")
p.add_argument("--darija-model", default="anaszil/whisper-large-v3-turbo-darija", help="'none' = plain base model")
p.add_argument("--base-model", default="openai/whisper-large-v3-turbo")
p.add_argument("--text-model", default="atlasia/moulsot.v0.3", help="text model (qwen-asr); 'none' = old Whisper EN/FR pass")
p.add_argument("--context", default="", help="optional topic words for MoulSot (tech names, brand...)")
p.add_argument("--no-retakes", action="store_true", help="detect retakes but do not cut them")
p.add_argument("--no-grade", action="store_true")
p.add_argument("--mic", default="", help="separate mic recording in 'raw footage' to use INSTEAD of the phone audio "
               "(file name, or 'auto' = newest audio file there); synced automatically (offset + clock drift)")
p.add_argument("--keep-in", action="store_true", default=True, help="copy in.mp4 to Drive (needed for re-cuts)")
args = p.parse_args()


def log(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


def prog(step, done=None, total=None, unit=""):
    """Machine-readable progress line, read by platform/kaggle/prep_runner.py (real counts, never estimated)."""
    print("@@P " + json.dumps({"step": step, "done": done, "total": total, "unit": unit}), flush=True)


def sh_progress(cmd, step, total_s):
    """Run ffmpeg with -progress and report real seconds processed / total seconds."""
    cmd = [cmd[0], "-progress", "pipe:1", "-nostats", *cmd[1:]]
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    last = 0.0
    for line in pr.stdout:
        if line.startswith("out_time_us=") and line.strip()[12:].isdigit():
            t = int(line.strip()[12:]) / 1e6
            if t - last >= 1 or t >= total_s:
                last = t
                prog(step, round(min(t, total_s), 1), round(total_s, 1), "s")
    err = pr.stderr.read()
    if pr.wait() != 0:
        raise RuntimeError(f"{cmd[0]} failed:\n{err[-3000:]}")


def sh(cmd, text=True):
    r = subprocess.run(cmd, capture_output=True, text=text)
    if r.returncode != 0:
        err = r.stderr if text else r.stderr.decode("utf8", "replace")
        raise RuntimeError(f"{cmd[0]} failed:\n{err[-3000:]}")
    return r


# ---------- 0. packages (fresh subprocess, so removing torchao needs no runtime restart) ----------
def pip(*pk):
    subprocess.run([sys.executable, "-m", "pip", "-q", "install", *pk], check=True)


try:
    import importlib.util as iu
    if iu.find_spec("torchao") is not None:  # Colab's torchao makes peft refuse to load the LoRA
        subprocess.run([sys.executable, "-m", "pip", "-q", "uninstall", "-y", "torchao"], check=False)
    if iu.find_spec("peft") is None:
        pip("peft")
    if iu.find_spec("transformers") is None:
        pip("transformers", "accelerate")
except Exception as e:  # noqa: BLE001
    log(f"package setup warning: {e}")
if shutil.which("ffmpeg") is None:
    sh(["apt-get", "-qq", "install", "-y", "ffmpeg"])

import numpy as np  # noqa: E402
import torch  # noqa: E402

RAW = os.path.join(args.root, "raw footage")
OUT = os.path.join(args.root, "results", args.slug)
W = args.work
os.makedirs(OUT, exist_ok=True)
os.makedirs(W, exist_ok=True)
SR = 16000
FPS = 30

# ---------- 1. input + convert ----------
vids = [f for f in glob.glob(os.path.join(RAW, "*")) if os.path.splitext(f)[1].lower() in (".mov", ".mp4", ".m4v", ".mkv")]
if args.video:
    vids = [f for f in vids if os.path.basename(f) == args.video]
if not vids:
    sys.exit(f"No video found in {RAW!r} (name {args.video!r}). Put the clip there or pass --video.")
src = max(vids, key=os.path.getmtime)
log(f"input: {src} ({os.path.getsize(src) / 1e6:.0f} MB) -> results/{args.slug}")
local_src = os.path.join(W, "src" + os.path.splitext(src)[1])
shutil.copy(src, local_src)  # reading big files straight from Drive is slow and flaky
IN = os.path.join(W, "in.mp4")
# 4K / 60 fps / HDR iPhone clips -> 1080p (short side), 30 fps, SDR. GPU (NVENC) when available, else CPU.
_pr = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,color_transfer",
                     "-of", "json", local_src]).stdout)["streams"][0]
HDR = _pr.get("color_transfer", "") in ("arib-std-b67", "smpte2084")
SCALE = "scale='if(gt(iw,ih),-2,min(1080,iw))':'if(gt(iw,ih),min(1080,ih),-2)':flags=lanczos"
TONEMAP = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,"
log(f"source video: {_pr.get('width')}x{_pr.get('height')}{' HDR (will tone-map to SDR)' if HDR else ''}, "
    f"{os.path.getsize(local_src) / 1e9:.1f} GB -> 1080p 30 fps")


def convert(gpu, tonemap):
    vf = (TONEMAP if tonemap else "") + f"fps=30,{SCALE},format=yuv420p"
    enc = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "18", "-b:v", "0"] if gpu else \
          ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16"]
    sh_progress(["ffmpeg", "-v", "error", "-y", *(["-hwaccel", "cuda"] if gpu else []), "-i", local_src, "-map", "0:v:0", "-map", "0:a:0",
        "-vf", vf, *enc, "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", IN], "convert", SRC_DUR)


SRC_DUR = float(json.loads(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", local_src]).stdout)["format"]["duration"])
prog("convert", 0, round(SRC_DUR, 1), "s")
_t = time.time()
for gpu, tm in ((True, HDR), (False, HDR), (False, False)):
    try:
        convert(gpu, tm)
        log(f"converted with {'GPU' if gpu else 'CPU'}{' + HDR tone-map' if tm else ''} in {(time.time() - _t) / 60:.1f} min")
        break
    except RuntimeError as e:
        log(f"   ({'GPU' if gpu else 'CPU'}{' + tone-map' if tm else ''} conversion not available here: {str(e).splitlines()[-1][:120]})")
else:
    sys.exit("Video conversion failed (see above).")
info = json.loads(sh(["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration", "-of", "json", IN]).stdout)
DUR = float(info["format"]["duration"])
wh = [(s.get("width"), s.get("height")) for s in info["streams"] if s.get("width")][0]
MIC = None
if args.mic:
    auds = [f for f in glob.glob(os.path.join(RAW, "*")) if os.path.splitext(f)[1].lower() in (".wav", ".m4a", ".mp3", ".aac", ".flac", ".ogg", ".opus", ".aif", ".aiff")]
    if args.mic != "auto":
        auds = [f for f in auds if os.path.basename(f) == args.mic]
        if not auds:
            sys.exit(f"Mic file {args.mic!r} not found in {RAW!r}.")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mic_sync import sync_mic  # noqa: E402
    # newest first; in 'auto' mode an audio file that doesn't match THIS video (e.g. an older recording) is skipped
    for mic_src in sorted(auds, key=os.path.getmtime, reverse=True):
        mic_local = os.path.join(W, "mic" + os.path.splitext(mic_src)[1])
        shutil.copy(mic_src, mic_local)
        synced = os.path.join(W, "in_mic.mp4")
        try:
            log(f"mic audio: trying {os.path.basename(mic_src)}")
            MIC = sync_mic(IN, mic_local, synced)
        except RuntimeError as e:
            log(f"   {os.path.basename(mic_src)}: {e}")
            if args.mic != "auto":
                sys.exit("The mic file could not be synced with this video (see above).")
            continue
        MIC["file"] = os.path.basename(mic_src)
        os.replace(synced, IN)
        log(f"mic synced: {MIC['file']}, offset {MIC['offsetS']:+.3f}s, drift {MIC['driftPpm']:+.0f} ppm, worst check error {MIC['worstErrorMs']} ms")
        break
    if MIC is None:
        log("!! no mic recording matching this video was found in 'raw footage': keeping the PHONE audio")
ORIENT = "vertical" if wh[1] >= wh[0] else "horizontal"
log(f"converted: {wh[0]}x{wh[1]} ({ORIENT}), {DUR:.1f}s")

pcm = sh(["ffmpeg", "-v", "error", "-i", IN, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"], text=False).stdout
A = np.frombuffer(pcm, dtype=np.float32)


def db(s, e):
    x = A[int(s * SR):int(e * SR)]
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9) if len(x) else -99.0


prog("silence", 0, 1, "")
# ---------- 2. silence cut (RMS: works on quiet phone audio AND on loud audio with room noise) ----------
hop = 0.02
rms = np.array([db(k * hop, (k + 1) * hop) for k in range(int(DUR / hop))])
floor = float(np.percentile(rms, 10))
thr = float(np.clip(floor + 6, -45, -30))
sil, runs, k = rms < thr, [], 0
while k < len(sil):
    if sil[k]:
        j = k
        while j < len(sil) and sil[j]:
            j += 1
        if (j - k) * hop >= 0.3:
            runs.append((k * hop, j * hop))
        k = j
    else:
        k += 1
keep, cur, pad = [], 0.0, 0.1
for s, e in runs:
    a, b = (s + pad if s > 0 else 0.0), (e - pad if e < DUR - 0.02 else DUR)
    if a > cur + 0.05:
        keep.append((cur, a))
    cur = max(cur, b)
if cur < DUR - 0.05:
    keep.append((cur, DUR))
cuts, o = [], 0.0
for s, e in keep:
    cuts.append({"sourceStart": round(s, 3), "sourceEnd": round(e, 3), "outStartMs": round(o * 1000)})
    o += e - s
json.dump({"input": "in.mp4", "removedSeconds": round(DUR - o, 2), "noiseFloorDb": round(floor, 1), "thresholdDb": round(thr, 1),
           "cuts": cuts}, open(os.path.join(W, "cut.mp4.cuts.json"), "w"), indent=1)
prog("silence", 1, 1, "")
log(f"silence cut: floor {floor:.1f} dB, threshold {thr:.1f} dB, {len(cuts)} segments, {DUR:.1f}s -> {o:.1f}s")

# ---------- 3. Darija transcription (per segment + per phrase) ----------
from transformers import GenerationConfig, WhisperForConditionalGeneration, WhisperProcessor  # noqa: E402
import gc  # noqa: E402

dev = "cuda" if torch.cuda.is_available() else "cpu"
dt = torch.float16 if dev == "cuda" else torch.float32
if dev == "cpu":
    log("WARNING: no GPU (Runtime -> Change runtime type -> T4 GPU). This will be slow.")
proc = WhisperProcessor.from_pretrained(args.base_model)
GEN = GenerationConfig.from_pretrained(args.base_model)  # alignment heads -> word timestamps


def load_base():
    m = WhisperForConditionalGeneration.from_pretrained(args.base_model, torch_dtype=dt, low_cpu_mem_usage=True)
    m.generation_config = GEN
    return m


try:  # one model in memory at a time (Colab RAM is ~12 GB)
    if args.darija_model == "none":
        raise RuntimeError("disabled with --darija-model none")
    from peft import PeftModel
    dar = PeftModel.from_pretrained(load_base(), args.darija_model).merge_and_unload().to(dev).eval()
    dar.generation_config = GEN
    log(f"Darija model loaded: {args.darija_model}")
except Exception as e:  # noqa: BLE001
    log(f"!! Darija LoRA failed to load ({str(e)[:160]}); falling back to {args.base_model} in Arabic")
    dar = load_base().to(dev).eval()


def transcribe(model, s, e, lang, words=True):
    x = A[int(s * SR):int(e * SR)]
    if len(x) < SR * 0.15:
        return "", []
    enc = proc(x, sampling_rate=SR, return_tensors="pt", return_attention_mask=True)
    feats = enc.input_features.to(dev, dt)
    with torch.no_grad():
        out = model.generate(feats, attention_mask=enc.attention_mask.to(dev), language=lang, task="transcribe", return_token_timestamps=words,
                             return_dict_in_generate=True, num_beams=1)
    get = (lambda k: out.get(k)) if isinstance(out, dict) else (lambda k: getattr(out, k, None))
    seqs = get("sequences") if get("sequences") is not None else out
    seq = seqs[0]
    text = proc.decode(seq, skip_special_tokens=True).strip()
    ws = []
    if words and get("token_timestamps") is not None:
        tts = get("token_timestamps")[0].tolist()
        cur_w, cur_s = "", None
        for tok, t in zip(seq.tolist(), tts):
            if tok >= proc.tokenizer.eos_token_id:  # special tokens
                continue
            piece = proc.tokenizer.decode([tok])
            if piece.startswith(" ") and cur_w.strip():
                ws.append({"t": cur_w.strip(), "s": round(s + cur_s, 3), "e": round(s + t, 3)})
                cur_w, cur_s = "", None
            if cur_s is None:
                cur_s = t
            cur_w += piece
        if cur_w.strip():
            ws.append({"t": cur_w.strip(), "s": round(s + (cur_s or 0), 3), "e": round(min(e, s + tts[-1]), 3)})
        # token timestamps mark token ENDS: shift each word start to the previous word end
        for i in range(1, len(ws)):
            ws[i]["s"] = max(ws[i - 1]["e"], min(ws[i]["s"], ws[i]["e"] - 0.05))
    return text, ws


HALLU = ("اشتركوا", "شكرا", "ترجمة", "نانسي", "subscribe", "thank you", "merci")
segments, phrases = [], []
prog("timings", 0, len(cuts), "segments")
for i, c in enumerate(cuts):
    prog("timings", i, len(cuts), "segments")
    s, e = c["sourceStart"], c["sourceEnd"]
    text, _ = transcribe(dar, s, e, "ar", words=False)
    junk = not text or (e - s < 0.6 and any(h in text.lower() for h in HALLU))
    segments.append({"i": i, "s": round(s, 3), "e": round(e, 3), "text": text, "junk": junk})
    if junk:
        continue
    h = 0.01
    d = np.array([db(s + q * h, s + (q + 1) * h) for q in range(int((e - s) / h))])
    low = d < np.median(d) - 12
    pts, q = [], 0
    while q < len(low):
        if low[q]:
            j = q
            while j < len(low) and low[j]:
                j += 1
            if (j - q) * h >= 0.08 and q > 0 and j < len(low):
                pts.append(s + (q + j) / 2 * h)
            q = j
        else:
            q += 1
    b = [s]
    for x in pts:
        if x - b[-1] >= 0.6:
            b.append(x)
    if e - b[-1] < 0.6 and len(b) > 1:
        b.pop()
    b.append(e)
    for x, y in zip(b, b[1:]):
        t, ws = transcribe(dar, x, y, "ar")
        phrases.append({"s": round(x, 3), "e": round(y, 3), "text": t, "words": ws})
    if i % 10 == 0:
        log(f"Darija: segment {i + 1}/{len(cuts)}")
json.dump({"segments": segments, "phrases": phrases}, open(os.path.join(W, "phrases.json"), "w"), ensure_ascii=False, indent=1)
prog("timings", len(cuts), len(cuts), "segments")
log(f"Darija done: {len(phrases)} phrases, {sum(s['junk'] for s in segments)} junk segments")

# ---------- 4. text pass: MoulSot (own process: qwen-asr needs another transformers version) ----------
del dar
gc.collect()
if dev == "cuda":
    torch.cuda.empty_cache()

MOUL = r"""
import json, sys, numpy as np, torch
from qwen_asr import Qwen3ASRModel
W, mid, ctx = sys.argv[1], sys.argv[2], sys.argv[3]
SR = 16000
A = np.load(f"{W}/audio16k.npy")
P = json.load(open(f"{W}/spans.json"))
dt = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
m = Qwen3ASRModel.from_pretrained(mid, dtype=dt, device_map="cuda", max_inference_batch_size=8, max_new_tokens=300)
out = []
for k in range(0, len(P), 16):
    items = [(A[int(s * SR):int(e * SR)], SR) for s, e in P[k:k + 16]]
    out += [(r.text or "").strip() for r in m.transcribe(audio=items, context=ctx, language="Arabic")]
    print("@@P " + json.dumps({"step": "text", "done": len(out), "total": len(P), "unit": "phrases"}), flush=True)
json.dump(out, open(f"{W}/moulsot.json", "w"), ensure_ascii=False)
"""


def moulsot_pass():
    if args.text_model == "none" or dev != "cuda" or not phrases:
        return None
    try:
        np.save(os.path.join(W, "audio16k.npy"), A)
        json.dump([[p["s"], p["e"]] for p in phrases], open(os.path.join(W, "spans.json"), "w"))
        open(os.path.join(W, "moulsot_run.py"), "w").write(MOUL)
        prog("text", 0, len(phrases), "phrases")
        pip("qwen-asr")
        r = subprocess.run([sys.executable, os.path.join(W, "moulsot_run.py"), W, args.text_model, args.context], text=True)
        out = json.load(open(os.path.join(W, "moulsot.json"), encoding="utf8")) if r.returncode == 0 else None
        if not out or len(out) != len(phrases):
            raise RuntimeError(f"exit {r.returncode}, {len(out or [])}/{len(phrases)} lines")
        return out
    except Exception as e:  # noqa: BLE001
        log(f"!! MoulSot failed ({str(e)[:200]}) -> falling back to the Whisper EN/FR pass")
        return None


ms = moulsot_pass()
second = []
if ms is not None:
    for n, ph in enumerate(phrases):
        ph["moulsot"] = ms[n]
        second.append({"seg": n, "s": ph["s"], "e": ph["e"], "moulsot": ms[n], "en": "", "fr": ""})
    TEXT_MODEL = args.text_model
    log("MoulSot text pass done")
else:
    base = load_base().to(dev).eval()
    for n, ph in enumerate(phrases):
        prog("text", n, len(phrases), "phrases")
        en, enw = transcribe(base, ph["s"], ph["e"], "en")
        fr, frw = transcribe(base, ph["s"], ph["e"], "fr")
        second.append({"seg": n, "s": ph["s"], "e": ph["e"], "en": en, "fr": fr, "en_words": enw, "fr_words": frw})
    TEXT_MODEL = f"Whisper EN/FR ({args.base_model})"
    log("EN/FR pass done")
    del base
    gc.collect()
    if dev == "cuda":
        torch.cuda.empty_cache()
json.dump({"segments": segments, "phrases": phrases}, open(os.path.join(W, "phrases.json"), "w"), ensure_ascii=False, indent=1)
json.dump(second, open(os.path.join(W, "second.json"), "w"), ensure_ascii=False, indent=1)
TX = lambda ph: ph.get("moulsot") or ph["text"]  # noqa: E731  best text for retake matching

prog("text", len(phrases), len(phrases), "phrases")
# ---------- 5. retakes / false starts (automatic, editable) ----------
AR_N = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"})


def norm(t):
    t = re.sub(r"[\u064B-\u065F\u0640.,!?؟،:\"'«»-]", " ", t.lower()).translate(AR_N)
    return " ".join(t.split())


def sim(a, b):
    a, b = norm(a), norm(b)
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def valley(t):  # quietest 20 ms within +-0.15 s
    return float(min(np.arange(t - 0.15, t + 0.15, 0.005), key=lambda v: db(v - 0.01, v + 0.01)))


removals = []
for i, ph in enumerate(phrases):
    txt = norm(TX(ph))
    if not txt:
        continue
    for j in range(i + 1, min(i + 4, len(phrases))):
        nx = phrases[j]
        if nx["s"] - ph["e"] > 20:
            break
        r = sim(TX(ph), TX(nx))
        a_w, b_w = txt.split(), norm(TX(nx)).split()
        prefix = len(a_w) >= 2 and a_w == b_w[:len(a_w)]
        restart = len(a_w) >= 2 and len(a_w) < len(b_w) and difflib.SequenceMatcher(None, a_w, b_w[:len(a_w)]).ratio() >= 0.7
        if r >= 0.62 or prefix or restart:
            kind = "retake" if r >= 0.62 else "false start"
            removals.append({"s": round(valley(ph["s"]), 3), "e": round(valley(nx["s"]), 3), "auto": True,
                             "reason": f"{kind} (similarity {r:.2f}): first take '{TX(ph)[:60]}' -> kept '{TX(nx)[:60]}'"})
            break
# merge overlapping
removals.sort(key=lambda r: r["s"])
merged = []
for r in removals:
    if merged and r["s"] <= merged[-1]["e"]:
        merged[-1]["e"] = max(merged[-1]["e"], r["e"])
        merged[-1]["reason"] += " + " + r["reason"]
    else:
        merged.append(r)
removals = merged
json.dump(removals, open(os.path.join(W, "removals.json"), "w"), ensure_ascii=False, indent=1)
log(f"retakes: {len(removals)} found ({'NOT cut: --no-retakes' if args.no_retakes else 'cut'})")

# ---------- 6. kept segments (build_cut.py logic) ----------
rem = [] if args.no_retakes else [(r["s"], r["e"]) for r in removals]
rem += [(s["s"], s["e"]) for s in segments if s["junk"]]
kept = []
for c in cuts:
    pieces = [(c["sourceStart"], c["sourceEnd"])]
    for a, b in sorted(rem):
        nxt = []
        for x, y in pieces:
            if b <= x or a >= y:
                nxt.append((x, y))
                continue
            if a > x:
                nxt.append((x, a))
            if b < y:
                nxt.append((b, y))
        pieces = nxt
    kept += [[round(x, 3), round(y, 3)] for x, y in pieces if y - x >= 0.1]
json.dump(kept, open(os.path.join(W, "segments.json"), "w"))

# render segments (render-segments.mjs logic) WITH the soft grade (one encode generation)
snap = lambda t: round(t * FPS) / FPS  # noqa: E731
GRADE = "hqdn3d=2:2:3:3,curves=all='0/0 0.25/0.22 0.6/0.61 1/0.98',eq=saturation=1.05,colorbalance=rs=0.02:bs=0.05:bm=0.02,unsharp=5:5:0.3,vignette=PI/7"
vf = f"fps={FPS},format=yuv420p" + ("" if args.no_grade else "," + GRADE)
parts = os.path.join(W, "parts")
shutil.rmtree(parts, ignore_errors=True)
os.makedirs(parts)
lst = []
segs = [(snap(a), snap(b)) for a, b in kept if snap(b) - snap(a) >= 1 / FPS]
for n, (a, b) in enumerate(segs):
    prog("render", n, len(segs), "segments")
    part = os.path.join(parts, f"p{n:04d}.mov")
    sh(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", IN, "-t", f"{b - a:.4f}", "-map", "0:v:0", "-map", "0:a:0",
        "-vf", vf, "-frames:v", str(round((b - a) * FPS)), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
        "-af", f"afade=t=in:d=0.008,afade=t=out:st={max(0, b - a - 0.008):.4f}:d=0.008", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", part])
    lst.append(f"file '{part}'")
open(os.path.join(parts, "list.txt"), "w").write("\n".join(lst))
RAWCUT = os.path.join(W, "edit-raw.mp4")
sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(parts, "list.txt"), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", RAWCUT])
FINAL_DUR = sum(b - a for a, b in segs)
prog("render", len(segs), len(segs), "segments")
log(f"cut rendered: {len(segs)} segments, {FINAL_DUR:.1f}s")

# loudness: two-pass loudnorm + oversampled limiter, nudged until -14 +-0.3 LUFS (max 3 tries)
meas = sh(["ffmpeg", "-hide_banner", "-i", RAWCUT, "-af", "loudnorm=I=-14:TP=-1:LRA=7:print_format=json", "-f", "null", "-"]).stderr
J = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
M = f"measured_I={J['input_i']}:measured_TP={J['input_tp']}:measured_LRA={J['input_lra']}:measured_thresh={J['input_thresh']}:offset={J['target_offset']}"
EDIT = os.path.join(W, "edit.mp4")
target, lim, I = -13.5, 0.7, None
for _pass in range(3):
    prog("loudness", _pass, 3, "passes")
    sh(["ffmpeg", "-v", "error", "-y", "-i", RAWCUT, "-af",
        f"loudnorm=I={target}:TP=-1.5:LRA=9:{M},aresample=192000,alimiter=limit={lim}:attack=1:release=50:level=false,aresample=48000",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", EDIT])
    eb = sh(["ffmpeg", "-hide_banner", "-i", EDIT, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", eb)[-1])
    PK = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", eb)[-1])
    if abs(I + 14) <= 0.3:
        break
    target += (-14 - I)
    lim = min(0.85, lim + 0.06)
log(f"loudness: {I:.1f} LUFS, true peak {PK:.1f} dBTP")

PREV = os.path.join(W, "preview-720p.mp4")
SHORT720 = "scale='if(gt(iw,ih),-2,720)':'if(gt(iw,ih),720,-2)'"  # 720p for vertical AND horizontal
prog("loudness", 3, 3, "passes")
sh_progress(["ffmpeg", "-v", "error", "-y", "-i", EDIT, "-vf", SHORT720, "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1100k",
             "-maxrate", "1300k", "-bufsize", "2600k", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", PREV], "preview", FINAL_DUR)

# ---------- 7. readable transcript + report, copy to Drive ----------
mmss = lambda t: f"{int(t // 60)}:{t % 60:05.2f}"  # noqa: E731
removed = lambda s, e: any(a - 0.05 <= s and e <= b + 0.05 for a, b in rem)  # noqa: E731
lines = []
for n, ph in enumerate(phrases):
    sc = second[n]
    flag = "REMOVED " if removed(ph["s"], ph["e"]) else ""
    if "moulsot" in ph:  # MS = MoulSot text (use it), AR = Whisper Darija (its words carry the timings)
        lines.append(f"[{n:3d}] {mmss(ph['s'])}-{mmss(ph['e'])} {flag}\n   MS: {ph['moulsot']}\n   AR: {ph['text']}")
    else:
        lines.append(f"[{n:3d}] {mmss(ph['s'])}-{mmss(ph['e'])} {flag}\n   AR: {ph['text']}\n   EN: {sc['en']}\n   FR: {sc['fr']}")
open(os.path.join(W, "transcript.txt"), "w", encoding="utf8").write("\n".join(lines) + "\n")
AUDIO_LINE = (f"mic {MIC['file']} (offset {MIC['offsetS']:+.3f}s, drift {MIC['driftPpm']:+.0f} ppm, "
              f"worst sync error {MIC['worstErrorMs']} ms)") if MIC else "phone"
rep = [f"# {args.slug} — Colab prep report", "",
       f"- Source: `{os.path.basename(src)}` · {wh[0]}x{wh[1]} ({ORIENT}) · {mmss(DUR)}",
       f"- Audio: {AUDIO_LINE}",
       f"- Silence cut: floor {floor:.1f} dB, threshold {thr:.1f} dB → {len(cuts)} segments",
       f"- Junk segments removed: {sum(s['junk'] for s in segments)}",
       f"- Retakes / false starts: {len(removals)} ({'NOT applied' if args.no_retakes else 'applied'}) — REVIEW in removals.json",
       f"- Final: {mmss(FINAL_DUR)} · {I:.1f} LUFS · peak {PK:.1f} dBTP · grade: {'none' if args.no_grade else 'soft'}",
       f"- Timings: {args.darija_model} · text: {TEXT_MODEL} · device: {dev}",
       f"- Prep time: {(time.time() - T0) / 60:.1f} min", "", "## Removals (ORIGINAL clip time)", ""]
rep += [f"- {mmss(r['s'])} – {mmss(r['e'])}: {r['reason']}" for r in removals] or ["- none"]
open(os.path.join(W, "report.md"), "w", encoding="utf8").write("\n".join(rep) + "\n")

json.dump({"slug": args.slug, "source": os.path.basename(src), "width": wh[0], "height": wh[1], "orientation": ORIENT,
           "fps": FPS, "sourceDurationS": round(DUR, 3), "finalDurationS": round(FINAL_DUR, 3), "lufs": I, "truePeakDb": PK,
           "graded": not args.no_grade, "micAudio": MIC, "backgroundSwapped": False, "retakesApplied": not args.no_retakes,
           "darijaModel": args.darija_model, "textModel": TEXT_MODEL},
          open(os.path.join(W, "meta.json"), "w"), indent=1)
files = ["meta.json", "edit.mp4", "preview-720p.mp4", "cut.mp4.cuts.json", "phrases.json", "second.json", "removals.json", "segments.json",
         "transcript.txt", "report.md"] + (["in.mp4"] if args.keep_in else [])
for f in files:
    shutil.copy(os.path.join(W, f), os.path.join(OUT, f))
log(f"DONE in {(time.time() - T0) / 60:.1f} min -> {OUT}")
print("\nNext: share the folder 'video-editor/results' as 'Anyone with the link' (once), then give Claude Code the link to "
      f"results/{args.slug}.")
