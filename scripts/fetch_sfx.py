"""Download the curated free sound-effect library into public/sfx/lib/ (git-ignored).

Usage:  python3 -I scripts/fetch_sfx.py            (skips files already downloaded)

Source: Mixkit (https://mixkit.co/free-sound-effects/), "Mixkit Sound Effects Free License": free for commercial and
personal videos, no attribution required. The licence does NOT allow redistributing the files on their own, and this
repo is public, so the WAVs are never committed: every session downloads them with this script (~20 s).
Each sound is cleaned: leading silence trimmed, capped in length with a fade-out, peak-normalised to -3 dBFS,
48 kHz stereo WAV. Names are by ROLE so edit.json stays readable: "sfx/lib/<name>.wav".
"""
import os
import subprocess
import sys
import urllib.request

# name: (mixkit id, max seconds, what it is / where it goes)
CATALOG = {
    # pops / cards appearing (under-chin cards, chips)
    "pop-soft":        (2356, 0.8, "Dry pop up notification alert - comment card / any frosted card in"),
    "pop-bubble":      (2357, 0.8, "Bubble pop up alert - second card, pinned reply"),
    "pop-light":       (3005, 1.2, "Explainer video pops whoosh light pop - light accent"),
    # transitions into full-screen moments
    "whoosh-air":      (1489, 1.2, "Air woosh - into a full-screen moment"),
    "whoosh-sweep":    (166, 1.0, "Fast small sweep transition - out of a moment / softer variant"),
    "whoosh-tech":     (3120, 1.5, "Technology transition slide - into code / tech moments"),
    "swoosh-fast":     (3115, 1.0, "Fast transitions swoosh - quick accent"),
    # interface clicks
    "click-ui":        (2568, 0.6, "Cool interface click tone - chip / button / small UI"),
    "click-select":    (1109, 0.5, "Select click - block landing, list item"),
    "click-modern":    (3124, 0.8, "Modern technology select - slider grab / option"),
    "click-device":    (2577, 0.5, "Interface device click - slider ticks"),
    # typing
    "type-laptop":     (2531, 3.0, "Typing on a laptop keyboard - under code typing"),
    "type-fast":       (1387, 2.5, "Fast keyboard typing - longer code lines"),
    "key-single":      (2541, 0.4, "Single key press in a laptop - one key / enter"),
    # money / counter
    "coin-tick":       (2003, 0.6, "Coins sound - each counter step"),
    "coin-win":        (1992, 1.5, "Coin win notification - counter lands on the big value"),
    "coins-clink":     (1993, 1.5, "Clinking coins - money mention"),
    # success / positive
    "chime-correct":   (2870, 1.5, "Correct answer tone - result / solution word"),
    "chime-positive":  (951, 1.5, "Positive notification - pinned reply / good news"),
    "chime-confirm":   (2867, 1.2, "Confirmation tone - check / done"),
    "bell-notify":     (933, 1.5, "Bell notification - a comment / question arrives"),
    # problems / dead end
    "impact-deep":     (498, 1.8, "Deep heartbeat impact - B&W dead end hit"),
    "error-tone":      (2569, 0.8, "Negative tone interface tap - strike-through / wrong"),
    "glitch-small":    (2595, 0.8, "Small electric glitch - bug / broken"),
    # paper / chapters
    "page-turn":       (1104, 1.0, "Page turn single - chapter chip / chapter blur"),
    "paper-slide":     (1530, 1.0, "Paper slide - file stack / document"),
}

OUT = os.path.join("public", "sfx", "lib")
os.makedirs(OUT, exist_ok=True)
ok = 0
for name, (mid, max_s, _) in CATALOG.items():
    dst = os.path.join(OUT, f"{name}.wav")
    if os.path.exists(dst):
        ok += 1
        continue
    raw = dst + ".src.wav"
    url = f"https://assets.mixkit.co/active_storage/sfx/{mid}/{mid}.wav"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(raw, "wb") as f:
            f.write(r.read())
        fade = max(0.05, min(0.25, max_s * 0.2))
        af = (f"silenceremove=start_periods=1:start_threshold=-50dB,atrim=0:{max_s},"
              f"afade=t=out:st={max_s - fade:.3f}:d={fade:.3f},aresample=48000")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-ac", "2", dst + ".tmp.wav"], check=True)
        peak = subprocess.run(["ffmpeg", "-hide_banner", "-i", dst + ".tmp.wav", "-af", "volumedetect", "-f", "null", "-"],
                              capture_output=True, text=True).stderr
        mx = float(peak.split("max_volume:")[1].split("dB")[0])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", dst + ".tmp.wav", "-af", f"volume={-3 - mx:.2f}dB",
                        "-c:a", "pcm_s16le", dst], check=True)
        ok += 1
    except Exception as e:  # noqa: BLE001
        print(f"!! {name} ({url}): {e}")
    finally:
        for t in (raw, dst + ".tmp.wav"):
            if os.path.exists(t):
                os.remove(t)
print(f"{ok}/{len(CATALOG)} sounds ready in {OUT}")
sys.exit(0 if ok == len(CATALOG) else 1)
