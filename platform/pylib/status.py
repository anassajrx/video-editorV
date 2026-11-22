"""Job status file `status.json` in the job's Drive folder: what the website's progress bar reads every 3 s.

Every number in it is a real count (bytes, seconds of video, phrases, frames...). A background thread writes the
file at most every 3 s when something changed, and every 20 s otherwise (heartbeat: the website shows "stalled"
when the heartbeat is older than 2 min).
"""
import json
import threading
import time
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Status:
    def __init__(self, drive, job_folder, stage, steps, base=None, worker=""):
        """steps: list of (id, label, weight). base: existing status dict to continue (keeps history)."""
        self.d, self.folder = drive, job_folder
        self.fid = drive.find("status.json", job_folder)
        st = dict(base or {})
        st.update({"stage": stage, "state": "running", "worker": worker, "error": None, "message": "",
                   "steps": [{"id": i, "label": lb, "weight": w, "state": "pending", "done": None, "total": None, "unit": "",
                              "started": None, "finished": None} for i, lb, w in steps],
                   "current": None, "percent": 0.0, "eta_s": None, "stage_started": now_iso()})
        st.setdefault("history", [])
        self.st, self.lock, self.dirty, self.last_write = st, threading.Lock(), True, 0.0
        self._t0 = {}
        self._stop = threading.Event()
        self.flush(force=True)
        threading.Thread(target=self._loop, daemon=True).start()

    # ---------- updates ----------
    def _step(self, sid):
        return next(s for s in self.st["steps"] if s["id"] == sid)

    def update(self, sid, done=None, total=None, unit=None, message=None):
        with self.lock:
            s = self._step(sid)
            for prev in self.st["steps"]:  # earlier running steps are finished once a later one starts
                if prev is s:
                    break
                if prev["state"] in ("pending", "running"):
                    prev["state"] = "done" if prev["state"] == "running" else "skipped"
                    prev["finished"] = prev["finished"] or now_iso()
            if s["state"] != "running":
                s["state"], s["started"] = "running", s["started"] or now_iso()
                self._t0[sid] = (time.time(), done or 0)
            if done is not None:
                s["done"] = done
            if total is not None:
                s["total"] = total
            if unit is not None:
                s["unit"] = unit
            if message is not None:
                self.st["message"] = message
            self.st["current"] = sid
            self._recompute()
            self.dirty = True

    def finish_step(self, sid):
        with self.lock:
            s = self._step(sid)
            s["state"], s["finished"] = "done", now_iso()
            if s["total"]:
                s["done"] = s["total"]
            self._recompute()
            self.dirty = True

    def _recompute(self):
        tot = sum(s["weight"] for s in self.st["steps"]) or 1
        acc = 0.0
        for s in self.st["steps"]:
            if s["state"] in ("done", "skipped"):
                acc += s["weight"]
            elif s["state"] == "running" and s["total"]:
                acc += s["weight"] * min(1.0, (s["done"] or 0) / s["total"])
        self.st["percent"] = round(100 * acc / tot, 1)
        cur = self.st["current"]
        s = self._step(cur) if cur else None
        self.st["eta_s"] = None
        if s and s["state"] == "running" and s["total"] and cur in self._t0:
            t0, d0 = self._t0[cur]
            dt, dd = time.time() - t0, (s["done"] or 0) - d0
            if dt > 5 and dd > 0:
                self.st["eta_s"] = round((s["total"] - s["done"]) * dt / dd)

    def done(self, next_stage=None, state="done", message=""):
        with self.lock:
            for s in self.st["steps"]:
                if s["state"] == "running":
                    s["state"], s["finished"] = "done", now_iso()
                elif s["state"] == "pending":
                    s["state"] = "skipped"
            self.st.update({"state": state, "message": message, "percent": 100.0, "eta_s": None, "current": None})
            self.st["history"].append({"stage": self.st["stage"], "finished": now_iso(), "state": state})
            if next_stage:
                self.st["next_stage"] = next_stage
        self.close()

    def fail(self, error):
        with self.lock:
            for s in self.st["steps"]:
                if s["state"] == "running":
                    s["state"] = "error"
            self.st.update({"state": "error", "error": str(error)[-4000:], "eta_s": None})
            self.st["history"].append({"stage": self.st["stage"], "finished": now_iso(), "state": "error"})
        self.close()

    # ---------- writing ----------
    def flush(self, force=False):
        with self.lock:
            self.st["heartbeat"] = now_iso()
            text = json.dumps(self.st, ensure_ascii=False, indent=1)
            self.dirty = False
        try:
            self.fid = self.d.write_text("status.json", self.folder, text, fid=self.fid)
            self.last_write = time.time()
        except Exception as e:  # noqa: BLE001  a failed status write must never kill the job
            print(f"(status write failed: {str(e)[:200]})", flush=True)
            if force:
                raise

    def _loop(self):
        while not self._stop.wait(1.0):
            age = time.time() - self.last_write
            if (self.dirty and age >= 3) or age >= 20:
                self.flush()

    def close(self):
        self._stop.set()
        self.flush(force=True)
