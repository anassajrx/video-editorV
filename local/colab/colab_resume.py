#!/usr/bin/env python3
"""RESUME Part A after the Darija transcription is done (rescue script, e.g. when the run is slow or was stopped).

Uses what Part A already left on Colab's disk (/content/work): in.mp4 (converted, mic audio already in it),
cut.mp4.cuts.json, phrases.json (Darija). It:
  1. saves phrases.json + cut.mp4.cuts.json to Drive right away (backup)
  2. runs the English + French pass WITH PROGRESS, saving progress to Drive every 25 phrases (a re-run continues)
  3. finishes Part A exactly like colab_prep.py (retake list, preview cut, loudness, report) and copies everything
Usage (new Colab cell, same runtime, after stopping Part A):
  !wget -q -O /content/colab_resume.py <raw github url>/local/colab/colab_resume.py
  !cd /content && python colab_resume.py --slug my-video --source "Vsl.mp4" --mic-file "Recording (3).m4a" --no-retakes --no-grade
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
p.add_argument("--no-retakes", action="store_true", help="detect retakes but do not cut them")
p.add_argument("--no-grade", action="store_true")
p.add_argument("--mic", default="", help="separate mic recording in 'raw footage' to use INSTEAD of the phone audio "
               "(file name, or 'auto' = newest audio file there); synced automatically (offset + clock drift)")
p.add_argument("--source", default="", help="original video file name (for the report)")
p.add_argument("--mic-file", default="", help="mic file used in the first run (for the report)")
p.add_argument("--keep-in", action="store_true", default=True, help="copy in.mp4 to Drive (needed for re-cuts)")
args = p.parse_args()


def log(msg):
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


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

# ---------- resume: load the state Part A left in /content/work ----------
IN = os.path.join(W, "in.mp4")
for f in ("in.mp4", "cut.mp4.cuts.json", "phrases.json"):
    if not os.path.exists(os.path.join(W, f)):
        sys.exit(f"Missing {os.path.join(W, f)}: this Colab runtime does not have Part A's work (was it restarted?). Run Part A again.")
for f in ("phrases.json", "cut.mp4.cuts.json"):
    shutil.copy(os.path.join(W, f), os.path.join(OUT, f))
log(f"backup: phrases.json + cut.mp4.cuts.json saved to {OUT}")
src = args.source or "in.mp4"
info = json.loads(sh(["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration", "-of", "json", IN]).stdout)
DUR = float(info["format"]["duration"])
wh = [(s.get("width"), s.get("height")) for s in info["streams"] if s.get("width")][0]
ORIENT = "vertical" if wh[1] >= wh[0] else "horizontal"
MIC = {"file": args.mic_file} if args.mic_file else None
pcm = sh(["ffmpeg", "-v", "error", "-i", IN, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"], text=False).stdout
A = np.frombuffer(pcm, dtype=np.float32)


def db(s, e):
    x = A[int(s * SR):int(e * SR)]
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9) if len(x) else -99.0


_c = json.load(open(os.path.join(W, "cut.mp4.cuts.json")))
cuts, floor, thr = _c["cuts"], _c.get("noiseFloorDb", 0.0), _c.get("thresholdDb", 0.0)
_p = json.load(open(os.path.join(W, "phrases.json"), encoding="utf8"))
segments, phrases = _p["segments"], _p["phrases"]
log(f"resumed: {wh[0]}x{wh[1]} {ORIENT}, {DUR:.0f}s, {len(cuts)} segments, {len(phrases)} Darija phrases")

# ---------- models ----------
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


# ---------- 4. EN / FR pass WITH PROGRESS (checkpoint to Drive every 25 phrases) ----------
ck = os.path.join(OUT, "second.partial.json")
second = json.load(open(ck, encoding="utf8")) if os.path.exists(ck) else []
if second:
    log(f"EN/FR: continuing from phrase {len(second)}/{len(phrases)} (saved progress)")
base = load_base().to(dev).eval()
t_enfr, n0 = time.time(), len(second)
for n in range(len(second), len(phrases)):
    ph = phrases[n]
    en, enw = transcribe(base, ph["s"], ph["e"], "en")
    fr, frw = transcribe(base, ph["s"], ph["e"], "fr")
    second.append({"seg": n, "s": ph["s"], "e": ph["e"], "en": en, "fr": fr, "en_words": enw, "fr_words": frw})
    done = n + 1
    if done % 10 == 0 or done == len(phrases):
        per = (time.time() - t_enfr) / (done - n0)
        log(f"EN/FR: phrase {done}/{len(phrases)}  (~{(len(phrases) - done) * per / 60:.0f} min left)")
    if done % 25 == 0:
        json.dump(second, open(ck, "w"), ensure_ascii=False)
json.dump(second, open(os.path.join(W, "second.json"), "w"), ensure_ascii=False, indent=1)
log("EN/FR pass done")
del base
gc.collect()
if dev == "cuda":
    torch.cuda.empty_cache()

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
    txt = norm(ph["text"])
    if not txt:
        continue
    for j in range(i + 1, min(i + 4, len(phrases))):
        nx = phrases[j]
        if nx["s"] - ph["e"] > 20:
            break
        r = sim(ph["text"], nx["text"])
        a_w, b_w = txt.split(), norm(nx["text"]).split()
        prefix = len(a_w) >= 2 and a_w == b_w[:len(a_w)]
        restart = len(a_w) >= 2 and len(a_w) < len(b_w) and difflib.SequenceMatcher(None, a_w, b_w[:len(a_w)]).ratio() >= 0.7
        if r >= 0.62 or prefix or restart:
            kind = "retake" if r >= 0.62 else "false start"
            removals.append({"s": round(valley(ph["s"]), 3), "e": round(valley(nx["s"]), 3), "auto": True,
                             "reason": f"{kind} (similarity {r:.2f}): first take '{ph['text'][:60]}' -> kept '{nx['text'][:60]}'"})
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
    part = os.path.join(parts, f"p{n:04d}.mov")
    sh(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-ss", f"{a:.4f}", "-i", IN, "-t", f"{b - a:.4f}", "-map", "0:v:0", "-map", "0:a:0",
        "-vf", vf, "-frames:v", str(round((b - a) * FPS)), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
        "-af", f"afade=t=in:d=0.008,afade=t=out:st={max(0, b - a - 0.008):.4f}:d=0.008", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", part])
    lst.append(f"file '{part}'")
open(os.path.join(parts, "list.txt"), "w").write("\n".join(lst))
RAWCUT = os.path.join(W, "edit-raw.mp4")
sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(parts, "list.txt"), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", RAWCUT])
FINAL_DUR = sum(b - a for a, b in segs)
log(f"cut rendered: {len(segs)} segments, {FINAL_DUR:.1f}s")

# loudness: two-pass loudnorm + oversampled limiter, nudged until -14 +-0.3 LUFS (max 3 tries)
meas = sh(["ffmpeg", "-hide_banner", "-i", RAWCUT, "-af", "loudnorm=I=-14:TP=-1:LRA=7:print_format=json", "-f", "null", "-"]).stderr
J = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
M = f"measured_I={J['input_i']}:measured_TP={J['input_tp']}:measured_LRA={J['input_lra']}:measured_thresh={J['input_thresh']}:offset={J['target_offset']}"
EDIT = os.path.join(W, "edit.mp4")
target, lim, I = -13.5, 0.7, None
for _ in range(3):
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
sh(["ffmpeg", "-v", "error", "-y", "-i", EDIT, "-vf", SHORT720, "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1100k",
    "-maxrate", "1300k", "-bufsize", "2600k", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", PREV])

# ---------- 7. readable transcript + report, copy to Drive ----------
mmss = lambda t: f"{int(t // 60)}:{t % 60:05.2f}"  # noqa: E731
removed = lambda s, e: any(a - 0.05 <= s and e <= b + 0.05 for a, b in rem)  # noqa: E731
lines = []
for n, ph in enumerate(phrases):
    sc = second[n]
    flag = "REMOVED " if removed(ph["s"], ph["e"]) else ""
    lines.append(f"[{n:3d}] {mmss(ph['s'])}-{mmss(ph['e'])} {flag}\n   AR: {ph['text']}\n   EN: {sc['en']}\n   FR: {sc['fr']}")
open(os.path.join(W, "transcript.txt"), "w", encoding="utf8").write("\n".join(lines) + "\n")
AUDIO_LINE = f"mic {MIC['file']} (synced in the first Part A run, see its log)" if MIC else "phone (or see the first run's log)"
rep = [f"# {args.slug} — Colab prep report", "",
       f"- Source: `{os.path.basename(src)}` · {wh[0]}x{wh[1]} ({ORIENT}) · {mmss(DUR)}",
       f"- Audio: {AUDIO_LINE}",
       f"- Silence cut: floor {floor:.1f} dB, threshold {thr:.1f} dB → {len(cuts)} segments",
       f"- Junk segments removed: {sum(s['junk'] for s in segments)}",
       f"- Retakes / false starts: {len(removals)} ({'NOT applied' if args.no_retakes else 'applied'}) — REVIEW in removals.json",
       f"- Final: {mmss(FINAL_DUR)} · {I:.1f} LUFS · peak {PK:.1f} dBTP · grade: {'none' if args.no_grade else 'soft'}",
       f"- Darija model: {args.darija_model} · EN/FR: {args.base_model} · device: {dev}",
       f"- Prep time: {(time.time() - T0) / 60:.1f} min", "", "## Removals (ORIGINAL clip time)", ""]
rep += [f"- {mmss(r['s'])} – {mmss(r['e'])}: {r['reason']}" for r in removals] or ["- none"]
open(os.path.join(W, "report.md"), "w", encoding="utf8").write("\n".join(rep) + "\n")

json.dump({"slug": args.slug, "source": os.path.basename(src), "width": wh[0], "height": wh[1], "orientation": ORIENT,
           "fps": FPS, "sourceDurationS": round(DUR, 3), "finalDurationS": round(FINAL_DUR, 3), "lufs": I, "truePeakDb": PK,
           "graded": not args.no_grade, "micAudio": MIC, "backgroundSwapped": False, "retakesApplied": not args.no_retakes,
           "darijaModel": args.darija_model, "enfrModel": args.base_model},
          open(os.path.join(W, "meta.json"), "w"), indent=1)
files = ["meta.json", "edit.mp4", "preview-720p.mp4", "cut.mp4.cuts.json", "phrases.json", "second.json", "removals.json", "segments.json",
         "transcript.txt", "report.md"] + (["in.mp4"] if args.keep_in else [])
for f in files:
    shutil.copy(os.path.join(W, f), os.path.join(OUT, f))
if os.path.exists(ck):
    os.remove(ck)
log(f"DONE in {(time.time() - T0) / 60:.1f} min -> {OUT}")
print("\nNext: share the folder 'video-editor/results' as 'Anyone with the link' (once), then give Claude Code the link to "
      f"results/{args.slug}.")
