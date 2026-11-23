"""Claude reports where it is (read by claude_stage.py -> status.json -> the website's progress bar).

  python3 platform/actions/progress.py <step> [done total unit] [--msg "short text"]
Steps: storyboard stage = retakes, cut, captions, graphics, storyboard; final stage = notes, sfx, qa.
"""
import json
import sys

a = sys.argv[1:]
msg = None
if "--msg" in a:
    i = a.index("--msg")
    msg = a[i + 1] if i + 1 < len(a) else None
    a = a[:i] + a[i + 2:]
p = {"step": a[0]}
if len(a) >= 3:
    p.update(done=float(a[1]), total=float(a[2]), unit=a[3] if len(a) > 3 else "")
if msg:
    p["message"] = msg[:200]
json.dump(p, open("/tmp/ve-progress.json", "w"))
print("progress:", p)
