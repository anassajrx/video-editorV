"""Build the final kept segments: silence-cut segments MINUS removals (retakes, false starts, junk).

Usage:
  python3 -I scripts/darija/build_cut.py <cuts.json> <removals.json> <out-segments.json> [--phrases=phrases.json]

<removals.json>: [{"s": 0.0, "e": 3.30, "reason": "retake: first '...'"}, ...]  (SOURCE seconds,
                 cut points already checked with cut_points.py)
--phrases: also removes every segment flagged junk by transcribe_phrases.py (breaths, "euh").

Writes [[start, end], ...] (source seconds) for:
  node scripts/render-segments.mjs public/videos/<slug>/raw/in.mp4 <out-segments.json> <edit-raw.mp4>
and <out-segments>.removed.json + a printed table (mm:ss in the ORIGINAL clip) for the report.
"""
import json
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
cuts_path, rem_path, out = args
cuts = json.load(open(cuts_path))["cuts"]
rem = [(r["s"], r["e"], r["reason"]) for r in json.load(open(rem_path))]
if "phrases" in opt:
    for s in json.load(open(opt["phrases"]))["segments"]:
        if s["junk"]:
            rem.append((s["s"], s["e"], "breath / noise / filler, no words"))
rem.sort()

keep = []
for c in cuts:
    pieces = [(c["sourceStart"], c["sourceEnd"])]
    for a, b, _ in rem:
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
    keep += [[round(x, 3), round(y, 3)] for x, y in pieces if y - x >= 0.1]
json.dump(keep, open(out, "w"))

src_dur = max(c["sourceEnd"] for c in cuts)
snap = lambda t: round(t * 30) / 30
dur = sum(snap(b) - snap(a) for a, b in keep if snap(b) - snap(a) >= 1 / 30)
mmss = lambda t: f"{int(t // 60)}:{t % 60:05.2f}"
json.dump([{"from": mmss(a), "to": mmss(b), "reason": r} for a, b, r in rem], open(out.replace(".json", "") + ".removed.json", "w"),
          ensure_ascii=False, indent=1)
for a, b, r in rem:
    print(f"{mmss(a)} - {mmss(b)}  {r}")
print(f"{len(keep)} segments, final duration {dur:.2f}s (silence cut was {sum(c['sourceEnd'] - c['sourceStart'] for c in cuts):.2f}s, raw ~{src_dur:.1f}s+)")
