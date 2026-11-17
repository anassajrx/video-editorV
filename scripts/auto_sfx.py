"""Add sound effects to a Purple Room edit.json, timed to each graphic's own animation.

Usage:  python3 -I scripts/auto_sfx.py src/videos/<slug>/edit.json [--dry]

Needs the library first: python3 -I scripts/fetch_sfx.py  (public/sfx/lib/, free Mixkit sounds, git-ignored).
Replaces only the sounds it added before (src starting with "sfx/lib/"); hand-placed sounds are kept.
Principle: the sound comes FROM the object (coins on the counter, keys under the code, a page turn on chapters,
a deep hit at the dead end), soft volumes (0.15-0.45) so the voice always stays on top, never two sounds closer
than 0.12 s. Timings mirror src/components/purple (Moments.tsx, Cards*.tsx, FootageFx.tsx): if an animation's
timing changes there, change it here too.
"""
import json
import sys

path = sys.argv[1]
dry = "--dry" in sys.argv
spec = json.load(open(path, encoding="utf8"))
L = lambda n: f"sfx/lib/{n}.wav"  # noqa: E731
out = []


def add(t_s, name, vol):
    out.append({"src": L(name), "atMs": max(0, round(t_s * 1000)), "volume": vol})


for o in spec.get("overlays", []):
    t, s0 = o.get("type"), o.get("startMs", 0) / 1000
    if t == "comment":
        add(s0, "pop-soft", 0.35); add(s0 + 0.5, "bell-notify", 0.16)
    elif t == "chapterChip":
        add(s0, "page-turn", 0.35); add(s0 + 0.45, "click-ui", 0.2)
    elif t == "gapBars":
        add(s0, "pop-soft", 0.3); add(s0 + 0.6, "whoosh-sweep", 0.2); add(s0 + 1.4, "chime-confirm", 0.18)
    elif t == "pinnedReply":
        add(s0, "pop-bubble", 0.3); add(s0 + 0.5, "chime-positive", 0.26)
    elif t == "chapterBlur":
        add(s0, "whoosh-sweep", 0.3); add(s0 + 0.45, "page-turn", 0.3)
    elif t == "bwStrike":
        strike = o.get("strikeAtMs", o["startMs"] + 500) / 1000
        add(s0, "impact-deep", 0.45); add(strike, "error-tone", 0.28)
    elif t == "momentBlocks":
        add(s0 - 0.1, "whoosh-air", 0.35)
        for i in range(4):
            add(s0 + 0.3 + i * 0.25 + 0.55, "click-select", 0.3)
        add(s0 + 0.3 + 3 * 0.25 + 0.85, "chime-confirm", 0.22)
    elif t == "momentCounter":
        add(s0 - 0.1, "whoosh-air", 0.35)
        n = len(o.get("steps", []))
        for i in range(n):
            add(s0 + 0.2 + i * 0.25, "coin-tick", 0.28)
        add(s0 + 0.2 + n * 0.25, "coin-win", 0.4)
    elif t == "momentSlider":
        add(s0 - 0.1, "whoosh-sweep", 0.3); add(s0 + 0.3, "click-modern", 0.3)
        for k in range(1, 4):
            add(s0 + 0.3 + k * 0.3, "click-device", 0.16)
        add(s0 + 1.55, "chime-confirm", 0.22)
    elif t == "momentCode":
        n = len(o.get("code", ""))
        add(s0 - 0.1, "whoosh-tech", 0.3)
        if n:
            add(s0 + 0.3, "type-laptop" if n * 0.04 <= 3 else "type-fast", 0.3)
            add(s0 + 0.3 + n * 0.04 + 0.1, "key-single", 0.35)
    elif t == "momentFlow":
        add(s0 - 0.1, "whoosh-air", 0.3)
        for i in range(len(o.get("words", []))):
            add(s0 + 0.3 + i * 0.6, "pop-light", 0.22)
    elif t in ("endCard", "ctaEndCard"):
        add(s0, "whoosh-tech", 0.3); add(s0 + 0.6, "chime-correct", 0.3)
    elif t == "fileStack":
        for i in range(len(o.get("lines", []))):
            add(s0 + 0.3 + i * o.get("every", 0.5), "paper-slide", 0.22)
    elif t == "progressCard":
        add(s0, "click-ui", 0.25); add(s0 + 1.2, "chime-confirm", 0.24)
    elif t == "creditRows":
        for i in range(len(o.get("rows", []))):
            add(s0 + 0.3 + i * o.get("every", 0.4), "click-ui", 0.2)
    # legacy (cyan) overlays, in case an old-style edit is used
    elif t == "icon":
        add(s0, "pop-light", 0.3)
    elif t == "card":
        add(s0, "whoosh-sweep", 0.3)
    elif t == "terminal":
        add(s0, "type-laptop", 0.25)

# never two auto sounds closer than 120 ms (keep the earlier one), stay inside the video
out.sort(key=lambda x: x["atMs"])
dur = spec.get("durationMs", 10 ** 9)
kept = []
for x in out:
    if x["atMs"] >= dur - 100:
        continue
    if kept and x["atMs"] - kept[-1]["atMs"] < 120:
        continue
    kept.append(x)
manual = [x for x in spec.get("sfx", []) if not x["src"].startswith("sfx/lib/")]
spec["sfx"] = sorted(manual + kept, key=lambda x: x["atMs"])
print(f"{len(kept)} auto sounds (+{len(manual)} hand-placed kept)")
if not dry:
    json.dump(spec, open(path, "w", encoding="utf8"), ensure_ascii=False, indent=2)
    print("wrote", path)
