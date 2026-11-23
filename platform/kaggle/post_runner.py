"""Stage "post" (Kaggle, T4 GPU), only when the user ticked Omni Flash and/or Change background:
cut/edit_cut.mp4 (Claude's retake cut, -14 LUFS, ungraded) -> join the Omni Flash clips (original voice back)
-> background swap (MatAnyone 2) -> soft grade -> Drive jobs/<slug>/post/ (edit.mp4 = what Claude animates).
Same code as the tested Colab Part C (colab_finish.py + the B1-B5 cells), with real progress in status.json.
"""
import glob
import json
import os
import subprocess
import sys
import traceback

from drive import Drive
from prep_runner import creds
from status import Status

STEPS = [
    ("download", "Download the cut (+ Omni clips, background)", 6),
    ("omni_join", "Join the Omni Flash clips + your voice", 6),
    ("bg_setup", "Background: install + clean the image", 8),
    ("cutout", "Background: cut you out (MatAnyone 2)", 45),
    ("composite", "Background: put you in the new room", 20),
    ("grade", "Soft grade + preview", 6),
    ("upload", "Save to Drive", 9),
]


def main(job):
    here = os.path.dirname(os.path.abspath(__file__))
    c = creds()
    d = Drive(c["GOOGLE_CLIENT_ID"], c["GOOGLE_CLIENT_SECRET"], c["GOOGLE_REFRESH_TOKEN"])
    folder = job["job_folder_id"]
    sid = d.find("status.json", folder)
    base = json.loads(d.read_text(sid)) if sid else {}
    job["options"] = {**(base.get("job") or {}).get("options", {}), **(job.get("options") or {})}
    st = Status(d, folder, "post", STEPS, base=base, worker="kaggle")
    try:
        run(job, d, st, here)
    except BaseException as e:  # noqa: BLE001
        st.fail(f"{e}\n{traceback.format_exc()[-1500:]}" if not isinstance(e, SystemExit) else str(e))
        raise


def fetch(d, files, dest, st, done0, total):
    os.makedirs(dest, exist_ok=True)
    got = done0
    for f in files:
        d.download(f["id"], os.path.join(dest, f["name"]), on_progress=lambda a, b, g=got: st.update("download", g + a, total, "bytes"))
        got += int(f.get("size", 0))
    return got


def run(job, d, st, here):
    slug, folder, opts = job["slug"], job["job_folder_id"], job["options"]
    omni, bg = bool(opts.get("omni")), bool(opts.get("background"))
    root = "/kaggle/working/ve"
    RES = os.path.join(root, "results", slug)
    os.makedirs(RES, exist_ok=True)

    # ---- download (real bytes) ----
    cut, prep = d.find("cut", folder, folder=True), d.find("prep", folder, folder=True)
    if not cut:
        raise RuntimeError("No cut/ folder in Drive: the retake cut was not made.")
    lst = [(f, RES) for f in d.children(cut) if f["name"] in ("edit_cut.mp4", "segments.json")]
    lst += [(f, RES) for f in d.children(prep) if f["name"] in ("meta.json", "report.md")] if prep else []
    if omni:
        om = d.find("omni", cut, folder=True)
        if not om:
            raise RuntimeError("No cut/omni folder in Drive.")
        lst += [(f, os.path.join(RES, "omni")) for f in d.children(om) if f["name"] == "omni_plan.json"]
        for sub in ("to_omni", "from_omni"):
            sf = d.find(sub, om, folder=True)
            if sf:
                lst += [(f, os.path.join(RES, "omni", sub)) for f in d.children(sf) if not f["mimeType"].endswith("folder")]
    bg_file = None
    if bg:
        bid = opts.get("background_file_id")
        if not bid:
            raise RuntimeError("Change background is ticked but no background image was given.")
        m = d.meta(bid)
        bg_file = os.path.join(RES, "background" + (os.path.splitext(m["name"])[1] or ".png"))
        lst.append(({"id": bid, "name": os.path.basename(bg_file), "size": m.get("size", 0)}, RES))
    total = sum(int(f.get("size", 0)) for f, _ in lst)
    st.update("download", 0, total, "bytes")
    got = 0
    for f, dest in lst:
        got = fetch(d, [f], dest, st, got, total)
    st.finish_step("download")
    os.makedirs(os.path.join(RES, "omni", "from_omni"), exist_ok=True)

    finish = os.path.join(here, "colab_finish.py")
    cur = os.path.join(RES, "edit_cut.mp4")
    if omni:
        n = len(glob.glob(os.path.join(RES, "omni", "from_omni", "*")))
        st.update("omni_join", 0, 1, "", message=f"{n} Omni Flash clip(s) received")
        subprocess.run([sys.executable, finish, "join", "--slug", slug, "--root", root, "--work", "/kaggle/working/finish"], check=True)
        cur = os.path.join(RES, "edit_omni.mp4")
        st.finish_step("omni_join")

    swapped, extra = False, []
    if bg:
        from bg_swap import swap
        out, compare = swap(cur, bg_file, os.path.join(RES, "background_files"),
                            has_me=bool(opts.get("background_has_me", True)),
                            progress=lambda s, a=None, b=None, u="": st.update(s, a, b, u))
        cur, swapped = str(out), True
        extra = [str(compare), os.path.join(RES, "background_files", "background_clean.png")]

    st.update("grade", 0, 1, "")
    cmd = [sys.executable, finish, "finish", "--slug", slug, "--root", root, "--work", "/kaggle/working/finish", "--input", cur]
    cmd += (["--swapped"] if swapped else []) + (["--omni"] if omni else [])
    subprocess.run(cmd, check=True)
    st.finish_step("grade")

    files = [os.path.join(RES, f) for f in ("edit.mp4", "segments.json", "meta.json", "preview-720p.mp4", "report.md")]
    files = [f for f in files + extra if os.path.exists(f)]
    total = sum(os.path.getsize(f) for f in files)
    post = d.folder("post", folder)
    sent = 0
    st.update("upload", 0, total, "bytes")
    for f in files:
        d.upload(f, post, on_progress=lambda a, b, s0=sent: st.update("upload", s0 + a, total, "bytes"))
        sent += os.path.getsize(f)
    st.finish_step("upload")
    st.st["post"] = {"folder_id": post, "compare": d.find("compare-background.mp4", post) if swapped else None}
    st.done(next_stage="storyboard", message="Background / Omni done")


if __name__ == "__main__":
    main(json.loads(sys.argv[1]))
