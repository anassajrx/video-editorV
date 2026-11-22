"""Stage 1 (Kaggle, T4 GPU): Drive video -> colab_prep.py (convert, silence cut, transcription MoulSot + Whisper
timings, junk removal, loudness, preview) -> results uploaded to the job's Drive folder. Real progress in status.json.

Started by the GitHub Actions orchestrator with `kaggle kernels push` (see make_kernel.py). The kernel's code is a
tiny bootstrap that defines JOB and downloads this file + its helpers from the public repo.

Google credentials (never in the kernel code): Kaggle Secrets GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET /
GOOGLE_REFRESH_TOKEN if they are attached, else the private Kaggle dataset `<user>/ve-secrets` (file ve-secrets.json),
which the workflow `kaggle-secrets.yml` creates from the GitHub secrets.
"""
import glob
import json
import os
import subprocess
import sys
import time
import traceback

from drive import Drive
from status import Status

STEPS = [
    ("download", "Download the video from Drive", 5),
    ("convert", "Convert to 1080p 30 fps", 10),
    ("silence", "Silence cut", 2),
    ("timings", "Transcription: word timings (Darija Whisper)", 25),
    ("text", "Transcription: text (MoulSot)", 20),
    ("render", "Remove junk + render the cut", 15),
    ("loudness", "Loudness -14 LUFS", 5),
    ("preview", "720p preview", 5),
    ("upload", "Save the results to Drive", 13),
]
VIDEO_EXT = (".mov", ".mp4", ".m4v", ".mkv")


def creds():
    try:
        from kaggle_secrets import UserSecretsClient
        u = UserSecretsClient()
        c = {k: u.get_secret(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")}
        if all(c.values()):
            print("credentials: Kaggle Secrets", flush=True)
            return c
    except Exception as e:  # noqa: BLE001
        print(f"(Kaggle Secrets not available: {str(e)[:120]})", flush=True)
    for f in glob.glob("/kaggle/input/**/ve-secrets.json", recursive=True):
        print("credentials: private dataset ve-secrets", flush=True)
        return json.load(open(f))
    raise SystemExit("No Google credentials: attach the Kaggle secrets or create the ve-secrets dataset (see platform/SETUP.md).")


def main(job):
    here = os.path.dirname(os.path.abspath(__file__))
    c = creds()
    d = Drive(c["GOOGLE_CLIENT_ID"], c["GOOGLE_CLIENT_SECRET"], c["GOOGLE_REFRESH_TOKEN"])
    folder = job["job_folder_id"]
    base = None
    sid = d.find("status.json", folder)
    if sid:
        try:
            base = json.loads(d.read_text(sid))
        except Exception:  # noqa: BLE001
            base = None
    st = Status(d, folder, "prep", STEPS, base=base, worker="kaggle")
    try:
        run(job, d, st, here)
    except BaseException as e:  # noqa: BLE001
        st.fail(f"{e}\n{traceback.format_exc()[-1500:]}" if not isinstance(e, SystemExit) else str(e))
        raise


def run(job, d, st, here):
    root, work = "/kaggle/working/ve", "/kaggle/working/work"
    raw = os.path.join(root, "raw footage")
    os.makedirs(raw, exist_ok=True)
    folder, slug = job["job_folder_id"], job["slug"]

    # 1. download (real bytes)
    m = d.meta(job["video_file_id"])
    name = m["name"] if m["name"].lower().endswith(VIDEO_EXT) else m["name"] + ".mp4"
    st.update("download", 0, int(m.get("size", 0)), "bytes", message=m["name"])
    d.download(job["video_file_id"], os.path.join(raw, name), on_progress=lambda a, b: st.update("download", a, b, "bytes"))
    st.finish_step("download")

    # 2-8. colab_prep.py, its "@@P" lines are the real progress
    cmd = [sys.executable, os.path.join(here, "colab_prep.py"), "--slug", slug, "--root", root, "--work", work,
           "--video", name, "--no-retakes", "--no-grade"]
    opts = job.get("options", {})
    if opts.get("context"):
        cmd += ["--context", opts["context"]]
    if opts.get("text_model"):
        cmd += ["--text-model", opts["text_model"]]
    tail = []
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                          env=dict(os.environ, PYTHONUNBUFFERED="1"))
    known = {s[0] for s in STEPS}
    for line in pr.stdout:
        if line.startswith("@@P "):
            try:
                p = json.loads(line[4:])
            except ValueError:
                continue
            if p["step"] in known:
                st.update(p["step"], p.get("done"), p.get("total"), p.get("unit") or "")
            continue
        print(line, end="", flush=True)
        tail = (tail + [line.rstrip()])[-60:]
        if "] " in line and line.startswith("["):  # colab_prep log() lines -> short message for the website
            st.update(st.st["current"] or "convert", message=line.split("] ", 1)[1].strip()[:200])
    if pr.wait() != 0:
        raise RuntimeError("colab_prep.py failed:\n" + "\n".join(tail))

    # 9. upload (real bytes)
    out = os.path.join(root, "results", slug)
    files = sorted(f for f in glob.glob(os.path.join(out, "*")) if os.path.isfile(f))
    total = sum(os.path.getsize(f) for f in files)
    sent = 0
    st.update("upload", 0, total, "bytes")
    res = d.folder("prep", folder)
    for f in files:
        size = os.path.getsize(f)
        d.upload(f, res, on_progress=lambda a, b, s0=sent: st.update("upload", s0 + a, total, "bytes"))
        sent += size
    st.finish_step("upload")
    meta = json.load(open(os.path.join(out, "meta.json")))
    st.st["prep"] = {"folder_id": res, "duration_s": meta.get("finalDurationS"), "orientation": meta.get("orientation"),
                     "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    st.done(next_stage="storyboard", message="Prep done")


if __name__ == "__main__":
    main(json.loads(sys.argv[1]))
