"""Local companion routes. Bind is loopback only."""

import json
import multiprocessing
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web import frames, game_session, keys
from web.mods_store import ModError, store_mod
from web.multipart import UploadError, read_file
from web.paths import USER_ID, ensure_user
from web.saves import MAX_SAVE_BYTES, SaveError, read_save_bytes, store_save

HOST = "127.0.0.1"
PORT = 8765
STATIC = Path(__file__).resolve().parent / "static"
_UPLOAD_EXTRA = 64_000

NOTICES = {
    "mod-ok": "Mod stored. It is not run by this page.",
    "save-ok": "Save stored.",
    "play-started": "Game started.",
    "play-running": "The game is already running.",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._static("index.html", "text/html; charset=utf-8")
        elif path == "/companion.js":
            self._static("companion.js", "text/javascript; charset=utf-8")
        elif path == "/save":
            self._download_save()
        elif path == "/frame":
            self._text(frames.get_frame(), "text/plain; charset=utf-8")
        elif path == "/session":
            self._json(game_session.status())
        elif path == "/notices":
            self._json(NOTICES)
        else:
            self._text("Not found", "text/plain; charset=utf-8", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/mods":
                self._upload_mod()
            elif path == "/save":
                self._upload_save()
            elif path == "/key":
                self._key()
            elif path == "/play":
                self._play()
            else:
                self._text("Not found", "text/plain; charset=utf-8", 404)
        except (UploadError, ModError, SaveError, ValueError) as err:
            self._text(str(err), "text/plain; charset=utf-8", 400)

    def _upload_mod(self):
        name, payload = read_file(
            self.headers.get("Content-Type", ""),
            self._body(256_000 + _UPLOAD_EXTRA),
        )
        store_mod(name, payload, USER_ID)
        self._redirect("mod-ok")

    def _upload_save(self):
        _name, payload = read_file(
            self.headers.get("Content-Type", ""),
            self._body(MAX_SAVE_BYTES + _UPLOAD_EXTRA),
        )
        store_save(payload, USER_ID)
        self._redirect("save-ok")

    def _play(self):
        result = game_session.start(USER_ID)
        self._redirect("play-started" if result == "started" else "play-running")

    def _key(self):
        raw = self._body(1024)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as err:
            raise ValueError("key body must be JSON") from err
        token = data.get("key") if isinstance(data, dict) else None
        if not isinstance(token, str) or not keys.push(token):
            self._text("dropped", "text/plain; charset=utf-8", 400)
            return
        self.send_response(204)
        self.end_headers()

    def _download_save(self):
        payload = read_save_bytes(USER_ID)
        if payload is None:
            self._text("No save stored.", "text/plain; charset=utf-8", 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header(
            "Content-Disposition", 'attachment; filename="pokete.json"'
        )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _redirect(self, code: str):
        self.send_response(303)
        self.send_header("Location", "/?notice=" + code)
        self.end_headers()

    def _static(self, name: str, content_type: str):
        payload = (STATIC / name).read_bytes()
        self._bytes(payload, content_type)

    def _json(self, data: dict):
        self._bytes(json.dumps(data).encode("utf-8"), "application/json")

    def _text(self, text: str, content_type: str, status: int = 200):
        self._bytes(text.encode("utf-8"), content_type, status)

    def _bytes(self, payload: bytes, content_type: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _body(self, limit: int) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as err:
            raise ValueError("bad content length") from err
        if length < 0 or length > limit:
            raise ValueError("upload is too large")
        return self.rfile.read(length)

    def log_message(self, fmt: str, *args):
        if self.path.startswith("/frame"):
            return
        super().log_message(fmt, *args)


def main():
    ensure_user(USER_ID)
    multiprocessing.set_start_method("spawn")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
