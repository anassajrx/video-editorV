"""Check retake/mistake cut points BEFORE cutting: never cut mid-word.

Usage:
  python3 -I scripts/darija/cut_points.py <in.mp4> <t1> [<t2> ...]      (source seconds)

For each time it prints a 10 ms energy profile (+-0.3 s) and the quietest 20 ms point within
+-0.15 s. A good cut point is a real valley (around -45 dB or lower). If there is no valley
(continuous speech, everything around -30 dB), look for a consonant closure (short dip to about
-37 dB) at the word boundary, or keep the take rather than cut through a word.
Every cut also gets an 8 ms audio fade from render-segments.mjs, so a tight cut does not click.
"""
import subprocess
import sys

import numpy as np

SR = 16000
src = sys.argv[1]
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"],
                     check=True, capture_output=True).stdout
a = np.frombuffer(pcm, dtype=np.float32)


def db(t, w=0.01):
    x = a[int(t * SR):int((t + w) * SR)]
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9) if len(x) else -99


for arg in sys.argv[2:]:
    c = float(arg)
    best = min(np.arange(c - 0.15, c + 0.15, 0.005), key=lambda t: db(t - 0.01, 0.02))
    print(f"\n== {c:.3f}s  -> quietest point {best:.3f}s ({db(best - 0.01, 0.02):.1f} dB)")
    for t in np.arange(c - 0.3, c + 0.3, 0.02):
        v = db(t, 0.02)
        mark = " <" if abs(t - best) < 0.011 else ""
        print(f"  {t:8.2f} {v:6.1f} " + "#" * int(max(0, v + 65)) + mark)
