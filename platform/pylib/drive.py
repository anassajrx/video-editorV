"""Minimal Google Drive v3 client (requests only) used by the Kaggle runner and the GitHub Actions jobs.

Auth: the user's OAuth client id/secret + refresh token (Drive scope). Access tokens are refreshed automatically.
"""
import json
import os
import time

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
CHUNK = 32 * 1024 * 1024  # multiple of 256 KiB


class Drive:
    def __init__(self, client_id, client_secret, refresh_token):
        self.cid, self.secret, self.refresh = client_id, client_secret, refresh_token
        self._tok, self._exp = None, 0.0
        self.s = requests.Session()

    @classmethod
    def from_env(cls):
        return cls(os.environ["GOOGLE_CLIENT_ID"], os.environ["GOOGLE_CLIENT_SECRET"], os.environ["GOOGLE_REFRESH_TOKEN"])

    def token(self):
        if not self._tok or time.time() > self._exp - 120:
            r = requests.post(TOKEN_URL, data={"client_id": self.cid, "client_secret": self.secret,
                                               "refresh_token": self.refresh, "grant_type": "refresh_token"}, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"Google token refresh failed ({r.status_code}): {r.text[:300]}")
            j = r.json()
            self._tok, self._exp = j["access_token"], time.time() + int(j.get("expires_in", 3600))
        return self._tok

    def req(self, method, url, tries=6, ok=(200, 201), **kw):
        for k in range(tries):
            h = dict(kw.pop("headers", {}) or {})
            h["Authorization"] = f"Bearer {self.token()}"
            try:
                r = self.s.request(method, url, headers=h, timeout=kw.pop("timeout", 120), **kw)
            except requests.RequestException:
                if k == tries - 1:
                    raise
                time.sleep(2 ** k)
                kw["headers"] = h
                continue
            if r.status_code in ok or r.status_code == 308:
                return r
            if r.status_code in (401,):
                self._tok = None
            if r.status_code in (401, 403, 429, 500, 502, 503, 504) and k < tries - 1 and not (
                    r.status_code == 403 and "rateLimit" not in r.text and "userRateLimit" not in r.text):
                time.sleep(2 ** k)
                kw["headers"] = h
                continue
            raise RuntimeError(f"Drive {method} {url.split('?')[0]} -> {r.status_code}: {r.text[:400]}")

    # ---------- metadata ----------
    def meta(self, fid, fields="id,name,size,mimeType,parents"):
        return self.req("GET", f"{API}/files/{fid}", params={"fields": fields, "supportsAllDrives": "true"}).json()

    def find(self, name, parent, folder=None):
        q = f"name = '{name.replace(chr(92), chr(92) * 2).replace(chr(39), chr(92) + chr(39))}' and '{parent}' in parents and trashed = false"
        if folder is True:
            q += f" and mimeType = '{FOLDER}'"
        r = self.req("GET", f"{API}/files", params={"q": q, "fields": "files(id,name,size,mimeType)", "pageSize": 10,
                                                    "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}).json()
        return r["files"][0]["id"] if r["files"] else None

    def folder(self, name, parent):
        fid = self.find(name, parent, folder=True)
        if fid:
            return fid
        return self.req("POST", f"{API}/files", params={"supportsAllDrives": "true", "fields": "id"},
                        json={"name": name, "mimeType": FOLDER, "parents": [parent]}).json()["id"]

    def children(self, parent):
        out, tok = [], None
        while True:
            r = self.req("GET", f"{API}/files", params={"q": f"'{parent}' in parents and trashed = false", "pageToken": tok,
                                                        "fields": "nextPageToken,files(id,name,size,mimeType)", "pageSize": 1000,
                                                        "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}).json()
            out += r["files"]
            tok = r.get("nextPageToken")
            if not tok:
                return out

    # ---------- content ----------
    def download(self, fid, dest, on_progress=None):
        size = int(self.meta(fid, "size").get("size", 0))
        done = 0
        with self.req("GET", f"{API}/files/{fid}", params={"alt": "media", "supportsAllDrives": "true"}, stream=True,
                      timeout=600) as r, open(dest, "wb") as fh:
            for block in r.iter_content(8 * 1024 * 1024):
                fh.write(block)
                done += len(block)
                if on_progress:
                    on_progress(done, size)
        return dest

    def upload(self, path, parent, name=None, mime="application/octet-stream", on_progress=None):
        """Resumable upload; replaces the content if a file with that name already exists in `parent`."""
        name = name or os.path.basename(path)
        size = os.path.getsize(path)
        fid = self.find(name, parent)
        if fid:
            r = self.req("PATCH", f"{UPLOAD}/files/{fid}", params={"uploadType": "resumable", "supportsAllDrives": "true"},
                         json={}, headers={"X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)})
        else:
            r = self.req("POST", f"{UPLOAD}/files", params={"uploadType": "resumable", "supportsAllDrives": "true"},
                         json={"name": name, "parents": [parent]},
                         headers={"X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)})
        url, pos = r.headers["Location"], 0
        with open(path, "rb") as fh:
            while True:
                fh.seek(pos)
                data = fh.read(CHUNK)
                end = pos + len(data) - 1
                rng = f"bytes {pos}-{end}/{size}" if data else f"bytes */{size}"
                r = self.req("PUT", url, data=data, headers={"Content-Range": rng}, ok=(200, 201, 308), timeout=600)
                if r.status_code in (200, 201):
                    if on_progress:
                        on_progress(size, size)
                    return r.json()["id"]
                got = r.headers.get("Range")
                pos = int(got.split("-")[1]) + 1 if got else 0
                if on_progress:
                    on_progress(pos, size)

    def write_text(self, name, parent, text, mime="application/json", fid=None):
        """Small file write (multipart). Pass `fid` to skip the name lookup."""
        fid = fid or self.find(name, parent)
        body = text.encode("utf8")
        if fid:
            self.req("PATCH", f"{UPLOAD}/files/{fid}", params={"uploadType": "media", "supportsAllDrives": "true"},
                     data=body, headers={"Content-Type": mime})
            return fid
        bnd = "vebnd" + str(int(time.time() * 1000))
        payload = (f"--{bnd}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
                   + json.dumps({"name": name, "parents": [parent]})
                   + f"\r\n--{bnd}\r\nContent-Type: {mime}\r\n\r\n").encode() + body + f"\r\n--{bnd}--".encode()
        return self.req("POST", f"{UPLOAD}/files", params={"uploadType": "multipart", "supportsAllDrives": "true", "fields": "id"},
                        data=payload, headers={"Content-Type": f"multipart/related; boundary={bnd}"}).json()["id"]

    def read_text(self, fid):
        return self.req("GET", f"{API}/files/{fid}", params={"alt": "media", "supportsAllDrives": "true"}).content.decode("utf8")
