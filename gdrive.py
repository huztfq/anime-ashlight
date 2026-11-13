"""Google Drive access with only the standard library (no venv needed).
Reads GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN / DRIVE_ROOT_ID from .env. Never prints them.
Scope is drive.file: the app only sees folders and files it created itself."""
import json, os, pathlib, time, urllib.error, urllib.parse, urllib.request

ENV = pathlib.Path(__file__).with_name(".env")
SCOPE = "https://www.googleapis.com/auth/drive.file"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"


def env():
    out = {}
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def set_env(key, value):
    """Add or replace one key in .env and keep the file private (chmod 600)."""
    lines = [l for l in (ENV.read_text().splitlines() if ENV.exists() else []) if not l.startswith(key + "=")]
    lines.append(f"{key}={value}")
    ENV.write_text("\n".join(lines) + "\n")
    os.chmod(ENV, 0o600)


def _req(url, data=None, headers=None, method=None):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(r, timeout=300) as resp:
        body = resp.read()
        return json.loads(body) if body else {}, resp.headers


class Drive:
    def __init__(self):
        e = env()
        missing = [k for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN") if not e.get(k)]
        if missing:
            raise SystemExit(f"Missing in .env: {', '.join(missing)}. Run google_auth.py first.")
        self.e = e
        self._token, self._exp = None, 0

    def token(self):
        if time.time() > self._exp - 60:
            data = urllib.parse.urlencode({
                "client_id": self.e["GOOGLE_CLIENT_ID"], "client_secret": self.e["GOOGLE_CLIENT_SECRET"],
                "refresh_token": self.e["GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
            j, _ = _req("https://oauth2.googleapis.com/token", data)
            self._token, self._exp = j["access_token"], time.time() + j.get("expires_in", 3600)
        return self._token

    def call(self, path, params=None, body=None, method=None):
        url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
        h = {"Authorization": f"Bearer {self.token()}"}
        data = None
        if body is not None:
            data, h["Content-Type"] = json.dumps(body).encode(), "application/json"
        return _req(url, data, h, method)[0]

    def find(self, name, parent, mime=None):
        q = f"name = '{name.replace(chr(39), chr(92) + chr(39))}' and '{parent}' in parents and trashed = false"
        if mime:
            q += f" and mimeType = '{mime}'"
        files = self.call("files", {"q": q, "fields": "files(id,name,size)"})["files"]
        return files[0] if files else None

    def folder(self, name, parent="root"):
        """Return the id of folder `name` under `parent`, creating it if needed."""
        f = self.find(name, parent, FOLDER)
        if f:
            return f["id"]
        return self.call("files", {"fields": "id"}, {"name": name, "mimeType": FOLDER, "parents": [parent]})["id"]

    def root(self):
        """The 'After the Hum' folder in My Drive (created once, id kept in .env as DRIVE_ROOT_ID)."""
        rid = self.e.get("DRIVE_ROOT_ID")
        if rid:
            try:
                if not self.call(f"files/{rid}", {"fields": "trashed"}).get("trashed"):
                    return rid
            except urllib.error.HTTPError:
                pass
        rid = self.folder("After the Hum")
        set_env("DRIVE_ROOT_ID", rid)
        self.e["DRIVE_ROOT_ID"] = rid
        return rid

    def upload(self, path, parent, chunk=32 * 1024 * 1024):
        """Resumable upload in chunks; skips a file already there with the same name and size."""
        path = pathlib.Path(path)
        size = path.stat().st_size
        old = self.find(path.name, parent)
        if old and int(old.get("size", -1)) == size:
            return "skipped (already there)"
        mime = {".mp4": "video/mp4", ".jpg": "image/jpeg", ".png": "image/png", ".srt": "text/plain",
                ".md": "text/markdown", ".pdf": "application/pdf", ".txt": "text/plain",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                }.get(path.suffix.lower(), "application/octet-stream")
        for attempt in range(4):
            try:
                _, hdr = _req(f"{UPLOAD}?uploadType=resumable",
                              json.dumps({"name": path.name, "parents": [parent]}).encode(),
                              {"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json",
                               "X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)})
                session = hdr["Location"]
                with path.open("rb") as fh:
                    pos = 0
                    while pos < size:
                        fh.seek(pos)
                        data = fh.read(chunk)
                        end = pos + len(data) - 1
                        h = {"Authorization": f"Bearer {self.token()}", "Content-Length": str(len(data)),
                             "Content-Range": f"bytes {pos}-{end}/{size}"}
                        try:
                            _req(session, data, h, "PUT")
                            pos = size
                        except urllib.error.HTTPError as err:
                            if err.code != 308:  # 308 = chunk stored, keep going
                                raise
                            rng = err.headers.get("Range")
                            pos = int(rng.split("-")[1]) + 1 if rng else 0
                return "uploaded"
            except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
                if attempt == 3:
                    raise
                print(f"  retry {path.name} ({err})", flush=True)
                time.sleep(5 * (attempt + 1))
