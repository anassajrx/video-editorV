"""Claude stages on a GitHub runner, with real progress in the job's status.json.

  python3 platform/actions/claude_stage.py storyboard <job_folder_id>
  python3 platform/actions/claude_stage.py post <job_folder_id>     (after the user's Omni Flash clips: Kaggle, then storyboard)
  python3 platform/actions/claude_stage.py final <job_folder_id>

With Omni Flash and/or Change background ticked, "storyboard" first runs the "cut" stage (Claude picks the takes,
colab_cut.py renders the ungraded cut + the <=15 s Omni clips) and then either waits for the user's Omni clips
(stage "omni") or goes straight to the Kaggle "post" kernel (Omni join + background swap + grade) and the storyboard.

storyboard: fetch the Kaggle prep results -> Claude (retakes + cut, captions, graphics plan, storyboard.png) ->
            save the work to Drive jobs/<slug>/storyboard/ -> status "waiting_review".
final:      fetch prep + storyboard work + the user's review (review.json) -> Claude applies the notes, SFX, QA ->
            this script renders (real frame progress) -> limiter -> jobs/<slug>/final/<slug>.mp4 + .srt -> email.

Claude reports which step it is on with `python3 platform/actions/progress.py <step>`; its tool calls become the
status message. Every number shown is real (bytes, frames); Claude's own steps have no fake percentage.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "pylib"))
from drive import Drive  # noqa: E402
from status import Status  # noqa: E402

PROGRESS_FILE = "/tmp/ve-progress.json"
OUT = os.path.join(REPO, "platform-out")

STAGES = {
    "cut": [("fetch", "Download the prep results", 10), ("retakes", "Claude: choose the takes", 45),
            ("cut", "Render the cut (+ Omni clips)", 30), ("upload", "Save to Drive", 15)],
    "storyboard": [("fetch", "Download the prep results", 8), ("retakes", "Claude: choose the takes", 14),
                   ("cut", "Cut, loudness, grade", 14), ("captions", "Claude: captions", 18),
                   ("graphics", "Claude: graphics plan + face check", 18), ("storyboard", "Claude: storyboard", 16),
                   ("upload", "Save to Drive", 12)],
    "final": [("fetch", "Download the work", 6), ("notes", "Claude: apply your notes", 20),
              ("sfx", "Claude: music + sound effects", 8), ("qa", "Claude: checks (face rule, stills)", 10),
              ("render", "Render the video", 40), ("master", "Final loudness + preview", 6), ("upload", "Save to Drive", 10)],
}


def sh(cmd, **kw):
    print("+", " ".join(cmd) if isinstance(cmd, list) else cmd, flush=True)
    return subprocess.run(cmd, check=True, cwd=REPO, **kw)


def fetch_folder(d, folder, dest, st, step, skip=()):
    files = [f for f in d.children(folder) if f["mimeType"] != "application/vnd.google-apps.folder" and f["name"] not in skip]
    total = sum(int(f.get("size", 0)) for f in files)
    done = 0
    st.update(step, 0, total, "bytes")
    os.makedirs(dest, exist_ok=True)
    for f in files:
        d.download(f["id"], os.path.join(dest, f["name"]),
                   on_progress=lambda a, b, d0=done: st.update(step, d0 + a, total, "bytes"))
        done += int(f.get("size", 0))
    return {f["name"]: f["id"] for f in files}


def upload_files(d, paths, folder, st, step):
    total = sum(os.path.getsize(p) for p in paths)
    sent = 0
    st.update(step, 0, total, "bytes")
    for p in paths:
        d.upload(p, folder, on_progress=lambda a, b, s0=sent: st.update(step, s0 + a, total, "bytes"))
        sent += os.path.getsize(p)
    st.finish_step(step)


def changed_files():
    """Files Claude created/changed in the repo (the edit), minus raw media and outputs."""
    out = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=REPO, capture_output=True, text=True).stdout
    keep = []
    for line in out.splitlines():
        p = line[3:].strip().strip('"')
        if " -> " in p:
            p = p.split(" -> ")[1]
        if p.startswith(("platform-out/", "out/", "node_modules/", ".whisper/")) or "/raw/" in p:
            continue
        if os.path.isfile(os.path.join(REPO, p)) and os.path.getsize(os.path.join(REPO, p)) < 50e6:
            keep.append(p)
    return keep


def run_claude(prompt, st, first_step, budget_min):
    """claude -p with stream-json; tool calls -> status message; progress.py -> current step."""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    st.update(first_step, message="Claude is starting")
    stop = threading.Event()

    def watch():
        last = None
        while not stop.wait(1):
            try:
                p = json.load(open(PROGRESS_FILE))
            except (OSError, ValueError):
                continue
            key = json.dumps(p, sort_keys=True)
            if key != last:
                last = key
                st.update(p["step"], p.get("done"), p.get("total"), p.get("unit"), message=p.get("message"))

    threading.Thread(target=watch, daemon=True).start()
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--dangerously-skip-permissions"]
    pr = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    result, t0 = None, time.time()
    for line in pr.stdout:
        try:
            ev = json.loads(line)
        except ValueError:
            print(line, end="", flush=True)
            continue
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    inp = c.get("input", {})
                    what = inp.get("description") or os.path.basename(str(inp.get("file_path") or "")) or ""
                    if not what and inp.get("command"):
                        what = str(inp["command"]).strip().split("\n")[0].split("<<")[0][:60]
                    msg = f"Claude: {c['name']} {what}".strip()
                    print(msg, flush=True)  # tool names/commands only, never transcript text
                    st.update(st.st["current"] or first_step, message=msg)
        elif ev.get("type") == "result":
            result = ev
        if time.time() - t0 > budget_min * 60:
            pr.kill()
            raise RuntimeError(f"Claude took more than {budget_min} min")
    pr.wait()
    stop.set()
    if not result or result.get("is_error"):
        sub = (result or {}).get("subtype", "no result")
        txt = str((result or {}).get("result", ""))[-600:]
        if re.search(r"usage limit|rate limit|limit reached|5-hour", txt, re.I):
            raise RuntimeError(f"CLAUDE_LIMIT: your Claude Pro limit was reached. Click Retry after it resets. ({txt[-200:]})")
        raise RuntimeError(f"Claude failed ({sub}): {txt}")
    print(f"Claude done: {result.get('num_turns')} turns, {result.get('duration_ms', 0) / 60000:.1f} min", flush=True)
    return result


def stage_storyboard(d, st, job, slug, folder):
    raw = os.path.join(REPO, "public", "videos", slug, "raw")
    prep = d.find("prep", folder)
    if not prep:
        raise RuntimeError("No prep results in Drive (jobs/<slug>/prep). Run the prep first.")
    post = d.find("post", folder, folder=True)
    if post:  # Omni / background done on Kaggle: edit.mp4 is final length, swapped, graded
        fetch_folder(d, prep, raw, st, "fetch", skip=("preview-720p.mp4", "edit.mp4", "segments.json", "meta.json"))
        fetch_folder(d, post, raw, st, "fetch", skip=("compare-background.mp4", "background_clean.png", "preview-720p.mp4"))
        cut = d.find("cut", folder, folder=True)
        if cut:
            fetch_folder(d, cut, raw, st, "fetch", skip=("edit_cut.mp4",))  # removals.json chosen in the cut stage
    else:
        fetch_folder(d, prep, raw, st, "fetch", skip=("preview-720p.mp4",))
    st.finish_step("fetch")
    os.makedirs(OUT, exist_ok=True)
    ctx = job.get("options", {}).get("context", "")
    script = job.get("options", {}).get("script", "")
    prompt = open(os.path.join(HERE, "prompts", "storyboard.md"), encoding="utf8").read() \
        .replace("{SLUG}", slug).replace("{CONTEXT}", ctx or "(none)").replace("{SCRIPT}", script or "(none)")
    if post:
        prompt = POST_NOTE.replace("{SLUG}", slug) + prompt
    run_claude(prompt, st, "captions" if post else "retakes", budget_min=90)
    need = [os.path.join(OUT, "storyboard.png"), os.path.join(OUT, "storyboard.md")]
    missing = [p for p in need if not os.path.exists(p)]
    if missing:
        raise RuntimeError(f"Claude finished without {', '.join(map(os.path.basename, missing))}")
    tar = os.path.join(OUT, "state.tar.gz")
    with tarfile.open(tar, "w:gz") as t:
        for p in changed_files():
            t.add(os.path.join(REPO, p), arcname=p)
    sb = d.folder("storyboard", folder)
    files = need + [tar] + [p for p in (os.path.join(raw, "edit.mp4"), os.path.join(raw, "segments.json"),
                                        os.path.join(raw, "removals.json")) if os.path.exists(p)]
    for extra in ("storyboard-preview.mp4",):
        if os.path.exists(os.path.join(OUT, extra)):
            files.append(os.path.join(OUT, extra))
    upload_files(d, files, sb, st, "upload")
    st.st["storyboard"] = {"folder_id": sb, "png": d.find("storyboard.png", sb), "md": d.find("storyboard.md", sb)}
    st.done(state="waiting", message="Storyboard ready: Accept or write your notes")
    st.st["stage"] = "review"
    st.flush(force=True)


POST_NOTE = """IMPORTANT, this job already has its FINAL CUT: the takes were chosen earlier and Omni Flash and/or the background
swap were applied on a GPU. `public/videos/{SLUG}/raw/edit.mp4` is final length, graded, -14 LUFS, and
`segments.json` + `removals.json` describe that cut. SKIP steps 1 and 2 below (do not re-cut, do not re-grade, do not
touch edit.mp4): start at step 3 (captions, timed with phrases.json + segments.json). meta.json `backgroundSwapped` /
`omniFlash` say what was done.

"""


def stage_cut(d, st, job, slug, folder):
    """Claude picks the takes; colab_cut.py renders the ungraded cut (+ Omni clips); results -> Drive cut/."""
    raw = os.path.join(REPO, "public", "videos", slug, "raw")
    prep = d.find("prep", folder)
    if not prep:
        raise RuntimeError("No prep results in Drive (jobs/<slug>/prep).")
    fetch_folder(d, prep, raw, st, "fetch", skip=("preview-720p.mp4", "edit.mp4", "segments.json"))
    st.finish_step("fetch")
    os.makedirs(OUT, exist_ok=True)
    opts = job.get("options", {})
    prompt = open(os.path.join(HERE, "prompts", "cut.md"), encoding="utf8").read() \
        .replace("{SLUG}", slug).replace("{CONTEXT}", opts.get("context") or "(none)").replace("{SCRIPT}", opts.get("script") or "(none)")
    run_claude(prompt, st, "retakes", budget_min=45)
    seg = os.path.join(raw, "segments.json")
    if not os.path.exists(seg):
        raise RuntimeError("Claude finished without segments.json")
    # colab_cut.py works on <root>/results/<slug>/ (in.mp4 + final_cut.json)
    root = "/tmp/ve-cut"
    res = os.path.join(root, "results", slug)
    os.makedirs(res, exist_ok=True)
    shutil.copy(os.path.join(raw, "in.mp4"), os.path.join(res, "in.mp4"))
    shutil.copy(seg, os.path.join(res, "final_cut.json"))
    n = len(json.load(open(seg)))
    st.update("cut", 0, None, "", message=f"Rendering {n} kept segments")
    cmd = [sys.executable, os.path.join(REPO, "local", "colab", "colab_cut.py"), "--slug", slug, "--root", root,
           "--work", "/tmp/ve-cut-work"]
    if opts.get("omni"):
        cmd += ["--omni", "--omni-max", "15"]
    subprocess.run(cmd, check=True)
    st.finish_step("cut")
    cutf = d.folder("cut", folder)
    files = [os.path.join(res, "edit_cut.mp4"), os.path.join(res, "segments.json"), os.path.join(raw, "removals.json")]
    files += [p for p in (os.path.join(OUT, "cut-decisions.md"),) if os.path.exists(p)]
    clips = sorted(glob.glob(os.path.join(res, "omni", "to_omni", "*.mp4")))
    total = sum(os.path.getsize(p) for p in files + clips)
    sent = 0
    st.update("upload", 0, total, "bytes")
    for p in files:
        d.upload(p, cutf, on_progress=lambda a, b, s0=sent: st.update("upload", s0 + a, total, "bytes"))
        sent += os.path.getsize(p)
    info = {"folder_id": cutf, "decisions": d.find("cut-decisions.md", cutf)}
    if opts.get("omni"):
        om = d.folder("omni", cutf)
        d.upload(os.path.join(res, "omni", "omni_plan.json"), om)
        to = d.folder("to_omni", om)
        for p in clips:
            d.upload(p, to, on_progress=lambda a, b, s0=sent: st.update("upload", s0 + a, total, "bytes"))
            sent += os.path.getsize(p)
        info.update(omni_folder=om, to_omni=to, from_omni=d.folder("from_omni", om), clips=len(clips))
    st.finish_step("upload")
    st.st["cut"] = info
    if opts.get("omni"):
        st.done(state="waiting", message=f"{len(clips)} clips ready for Omni Flash: edit them, put the results in "
                                         "from_omni (same names), then click Continue")
        st.st["stage"] = "omni"
        st.flush(force=True)
        return "omni"
    st.done(message="Cut done")
    return "post"


def run_kaggle_post(d, slug, folder):
    """Start the Kaggle post kernel (Omni join + background swap + grade) and wait. It writes status.json itself."""
    job = {"slug": slug, "job_folder_id": folder}
    sh([sys.executable, "platform/kaggle/make_kernel.py", "/tmp/kernel-post", json.dumps(job), "post"])
    sh(["kaggle", "kernels", "push", "-p", "/tmp/kernel-post"])
    user = os.environ["KAGGLE_USERNAME"]
    time.sleep(60)
    t0 = time.time()
    while time.time() - t0 < 5 * 3600:
        out = subprocess.run(["kaggle", "kernels", "status", f"{user}/ve-post"], capture_output=True, text=True).stdout.lower()
        print(time.strftime("%H:%M:%S"), out.strip()[-80:], flush=True)
        if "complete" in out or "error" in out or "cancel" in out:
            st = json.loads(d.read_text(d.find("status.json", folder)))
            if "complete" in out and st.get("state") != "error":
                return
            raise RuntimeError("Kaggle (background / Omni) failed: " + str(st.get("error") or out)[-1500:])
        time.sleep(30)
    raise RuntimeError("Kaggle post took more than 5 h")


def stage_final(d, st, job, slug, folder):
    raw = os.path.join(REPO, "public", "videos", slug, "raw")
    prep, sb = d.find("prep", folder), d.find("storyboard", folder)
    if not (prep and sb):
        raise RuntimeError("Missing prep or storyboard folder in Drive.")
    fetch_folder(d, prep, raw, st, "fetch", skip=("preview-720p.mp4", "edit.mp4", "segments.json", "removals.json"))
    names = fetch_folder(d, sb, OUT, st, "fetch")
    for f in ("edit.mp4", "segments.json", "removals.json"):
        if os.path.exists(os.path.join(OUT, f)):
            shutil.move(os.path.join(OUT, f), os.path.join(raw, f))
    with tarfile.open(os.path.join(OUT, "state.tar.gz")) as t:
        t.extractall(REPO, filter="data")
    st.finish_step("fetch")
    rid = d.find("review.json", folder)
    review = json.loads(d.read_text(rid)) if rid else {"accepted": True, "notes": ""}
    notes = review.get("notes", "").strip() or "(no notes: the user accepted the storyboard as is)"
    prompt = open(os.path.join(HERE, "prompts", "final.md"), encoding="utf8").read() \
        .replace("{SLUG}", slug).replace("{NOTES}", notes)
    run_claude(prompt, st, "notes", budget_min=90)
    del names

    # render with real frame progress (render-chunks prints "PROGRESS done/total frames")
    os.makedirs(os.path.join(REPO, "out"), exist_ok=True)
    raw_out = os.path.join(REPO, "out", f"{slug}-final.mp4")
    pr = subprocess.Popen(["node", "scripts/render-chunks.mjs", slug, raw_out, "90", "18"], cwd=REPO,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    tail = []
    st.update("render", 0, None, "frames", message="Bundling the video")
    for line in pr.stdout:
        m = re.match(r"PROGRESS (\d+)/(\d+) frames", line)
        if m:
            st.update("render", int(m.group(1)), int(m.group(2)), "frames")
        elif line.startswith("PROGRESS audio"):
            st.update("render", message="Audio rendered, joining")
        tail = (tail + [line.rstrip()])[-40:]
        print(line, end="", flush=True)
    if pr.wait() != 0:
        raise RuntimeError("Render failed:\n" + "\n".join(tail))
    st.finish_step("render")

    st.update("master", 0, 2, "files")
    final = os.path.join(OUT, f"{slug}.mp4")
    sh(["ffmpeg", "-v", "error", "-y", "-i", raw_out, "-c:v", "copy", "-af",
        "aresample=192000,alimiter=limit=0.82:attack=1:release=50:level=false,aresample=48000",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", final])
    st.update("master", 1, 2, "files")
    prev = os.path.join(OUT, f"{slug}-preview-720p.mp4")
    sh(["ffmpeg", "-v", "error", "-y", "-i", final, "-vf", "scale='if(gt(iw,ih),-2,720)':'if(gt(iw,ih),720,-2)'",
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1500k", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", prev])
    st.finish_step("master")
    fin = d.folder("final", folder)
    files = [final, prev] + glob.glob(os.path.join(REPO, "src", "videos", slug, "*.srt")) + \
        [p for p in (os.path.join(OUT, "report.md"),) if os.path.exists(p)]
    upload_files(d, files, fin, st, "upload")
    st.st["final"] = {"folder_id": fin, "video": d.find(f"{slug}.mp4", fin), "preview": d.find(os.path.basename(prev), fin)}
    st.done(message="Your video is ready")
    st.st["stage"] = "done"
    st.flush(force=True)


def main():
    stage, folder = sys.argv[1], sys.argv[2]
    d = Drive.from_env()
    sid = d.find("status.json", folder)
    base = json.loads(d.read_text(sid)) if sid else {}
    job = base.get("job") or {}
    slug = base.get("slug") or job.get("slug")
    if not slug:
        raise SystemExit("status.json has no slug")
    opts = job.get("options", {})
    needs_post = bool(opts.get("omni") or opts.get("background"))

    def run_stage(name, fn):
        b = json.loads(d.read_text(d.find("status.json", folder)))
        st = Status(d, folder, name, STAGES[name], base=b, worker="github")
        try:
            return fn(d, st, job, slug, folder)
        except BaseException as e:  # noqa: BLE001
            st.fail(str(e))
            raise

    if stage == "final":
        return run_stage("final", stage_final)
    if stage == "storyboard" and needs_post and not d.find("post", folder, folder=True):
        if run_stage("cut", stage_cut) == "omni":
            return  # waits for the user's Omni Flash clips; the website's Continue starts stage "post"
        stage = "post"
    if stage == "post":
        try:
            run_kaggle_post(d, slug, folder)
        except BaseException as e:  # noqa: BLE001
            b = json.loads(d.read_text(d.find("status.json", folder)))
            if b.get("state") != "error":
                b.update(state="error", error=str(e)[-3000:], stage="post")
                d.write_text("status.json", folder, json.dumps(b, ensure_ascii=False, indent=1))
            raise
    run_stage("storyboard", stage_storyboard)


if __name__ == "__main__":
    main()
