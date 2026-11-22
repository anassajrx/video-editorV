"""Small job helpers for the GitHub Actions orchestrator.

  python3 platform/actions/job.py create <video_file_id> [slug]   -> prints job JSON (creates My Drive/video-editor/jobs/<slug>/)
  python3 platform/actions/job.py set <job_folder_id> '<json patch>' -> merges the patch into status.json
  python3 platform/actions/job.py fail <job_folder_id> '<message>'  -> marks the job as failed (kernel died, etc.)
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pylib"))
from drive import Drive  # noqa: E402
from status import now_iso  # noqa: E402


def root_folder(d):
    top = d.req("GET", "https://www.googleapis.com/drive/v3/files/root", params={"fields": "id"}).json()["id"]
    return d.folder("jobs", d.folder("video-editor", top))


def read_status(d, folder):
    fid = d.find("status.json", folder)
    return (json.loads(d.read_text(fid)) if fid else {}), fid


def main():
    d = Drive.from_env()
    cmd = sys.argv[1]
    if cmd == "create":
        vid = sys.argv[2]
        name = d.meta(vid)["name"]
        slug = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else \
            re.sub(r"[^a-z0-9]+", "-", os.path.splitext(name)[0].lower()).strip("-")[:40] + time.strftime("-%m%d-%H%M")
        folder = d.folder(slug, root_folder(d))
        st = {"slug": slug, "video": {"id": vid, "name": name}, "stage": "queued", "state": "waiting",
              "message": "Waiting for a Kaggle GPU", "percent": 0, "created": now_iso(), "heartbeat": now_iso(), "history": []}
        d.write_text("status.json", folder, json.dumps(st, ensure_ascii=False, indent=1))
        print(json.dumps({"slug": slug, "job_folder_id": folder, "video_file_id": vid}))
    elif cmd in ("set", "fail"):
        folder = sys.argv[2]
        st, fid = read_status(d, folder)
        if cmd == "set":
            st.update(json.loads(sys.argv[3]))
        else:
            st.update({"state": "error", "error": sys.argv[3][-4000:]})
            st.setdefault("history", []).append({"stage": st.get("stage"), "finished": now_iso(), "state": "error"})
        st["heartbeat"] = now_iso()
        d.write_text("status.json", folder, json.dumps(st, ensure_ascii=False, indent=1), fid=fid)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
