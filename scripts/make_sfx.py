"""Synthesize the brand's soft UI sound effects (original, royalty-free).

Usage: python3 scripts/make_sfx.py <out_dir>
Writes whoosh.wav, pop.wav, click.wav, chime.wav, type.wav (48 kHz, mono, peak -6 dBFS).
"""
import sys, os, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)
out = sys.argv[1]
os.makedirs(out, exist_ok=True)

def save(name, x):
    x = x / (np.abs(x).max() + 1e-9) * 0.5  # -6 dBFS peak
    fade = min(len(x), 240)
    x[-fade:] *= np.linspace(1, 0, fade)
    with wave.open(os.path.join(out, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())

def t(d): return np.arange(int(d * SR)) / SR

def lowpass(x, fc):
    # one-pole low-pass with time-varying cutoff (fc: array or float)
    fc = np.broadcast_to(fc, x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x); s = 0.0
    for i in range(len(x)):
        s = (1 - a[i]) * x[i] + a[i] * s; y[i] = s
    return y

# whoosh: noise through a sweeping low-pass, swell in and out
d = 0.55; tt = t(d)
env = np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 2
sweep = 300 + 3500 * np.sin(np.pi * tt / d)
n = rng.standard_normal(len(tt))
w = lowpass(n, sweep) - lowpass(n, sweep * 0.25)
save("whoosh.wav", w * env)

# pop: short downward sine blip + tiny transient (glass bubble)
d = 0.14; tt = t(d)
f = 1100 * np.exp(-tt * 18) + 520
ph = 2 * np.pi * np.cumsum(f) / SR
p = np.sin(ph) * np.exp(-tt * 32) + 0.3 * np.sin(2 * ph) * np.exp(-tt * 60)
save("pop.wav", p)

# click: two tight filtered transients (mouse button down/up)
d = 0.09; tt = t(d)
c = np.zeros_like(tt)
for at, g in ((0.0, 1.0), (0.045, 0.6)):
    i = int(at * SR); k = 300
    c[i:i + k] += g * rng.standard_normal(k) * np.exp(-np.arange(k) / 40)
c = c - lowpass(c, 1500)
save("click.wav", c)

# chime: two soft bell notes (E6 then B6) with gentle decay
d = 0.9; tt = t(d)
ch = np.zeros_like(tt)
for at, f0 in ((0.0, 1318.5), (0.09, 1975.5)):
    m = tt >= at; x = tt[m] - at
    ch[m] += (np.sin(2*np.pi*f0*x) + 0.35*np.sin(2*np.pi*2.01*f0*x) + 0.15*np.sin(2*np.pi*3.02*f0*x)) * np.exp(-x * 6) * (1 - np.exp(-x * 400))
save("chime.wav", ch)

# type: ~10 soft key presses over 1 s
d = 1.0; tt = t(d)
ty = np.zeros_like(tt)
at = 0.02
while at < 0.92:
    i = int(at * SR); k = 500
    body = rng.standard_normal(k) * np.exp(-np.arange(k) / 70)
    ty[i:i + k] += rng.uniform(0.5, 1.0) * (body - lowpass(body, 800))
    at += rng.uniform(0.06, 0.12)
save("type.wav", ty)
print("ok")
