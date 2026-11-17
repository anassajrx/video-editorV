# ============================================================================
# CELL 2 — English + French pass on the same phrases (recovers foreign words in Latin letters)
# Run it in the SAME notebook, AFTER cell 1 (colab_transcribe.py) finished.
# Uses the plain Whisper large-v3-turbo (not the Darija fine-tune), forced to English, then to French.
# Output in the same Drive folder: second.json  [{s, e, darija, en, fr}]  + second.txt (easy to read)
# Claude then merges: Darija words from the Darija model, foreign words from these passes.
# ============================================================================

import json, os, subprocess, sys
import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor, pipeline

# reuse what cell 1 left in memory (OUT, a, SR); if the session restarted, set OUT by hand and reload the audio
try:
    OUT, a, SR  # noqa: B018
except NameError:
    raise SystemExit("Run cell 1 first in this same session (it defines the video and the output folder).")

phrases = json.load(open(f"{OUT}/phrases.json", encoding="utf-8"))["phrases"]
BASE_MODEL = "openai/whisper-large-v3-turbo"
proc = WhisperProcessor.from_pretrained(BASE_MODEL)
base = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL, torch_dtype=torch.float16).to("cuda").eval()
asr_base = pipeline("automatic-speech-recognition", model=base, tokenizer=proc.tokenizer,
                    feature_extractor=proc.feature_extractor, torch_dtype=torch.float16, device="cuda")


def run(s, e, lang):
    clip = a[int(s * SR):int(e * SR)].copy()
    if len(clip) < SR * 0.15:
        return ""
    out = asr_base({"raw": clip, "sampling_rate": SR}, generate_kwargs={"language": lang, "task": "transcribe"})
    return out["text"].strip()


rows = []
for i, p in enumerate(phrases):
    en = run(p["s"], p["e"], "english")
    fr = run(p["s"], p["e"], "french")
    rows.append({"s": p["s"], "e": p["e"], "darija": p["text"], "en": en, "fr": fr})
    print(f"{i + 1:3d}/{len(phrases)} {p['s']:7.2f} | AR: {p['text']}\n                | EN: {en}\n                | FR: {fr}", flush=True)

json.dump(rows, open(f"{OUT}/second.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
with open(f"{OUT}/second.txt", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(f"[{r['s']:7.2f}] AR: {r['darija']}\n          EN: {r['en']}\n          FR: {r['fr']}\n")
print("\nDONE. Saved in your Drive:", OUT, "(second.json, second.txt)")
