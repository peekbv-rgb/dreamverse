"""Minimal web app: serves static/ and a small JSON API.

No framework on purpose - the other projects here run on the standard
library's http.server and deploy to Render unchanged. Add FastAPI or Flask
the day something actually needs it, not before.

Secrets stay in this process. Anything the browser must know goes through an
endpoint that returns only what that page needs.
"""

import base64
import hmac
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

load_dotenv(ROOT / ".env")

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
AUTH_USER = os.environ.get("AUTH_USER", "")
AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "")


def auth_ok(header: str | None) -> bool:
    """Basic auth. Disabled entirely when either credential is blank."""
    if not (AUTH_USER and AUTH_PASSWORD):
        return True
    if not header or not header.startswith("Basic "):
        return False
    try:
        user, _, password = base64.b64decode(header[6:]).decode().partition(":")
    except Exception:
        return False
    # compare_digest on both halves: a plain == leaks length through timing.
    return hmac.compare_digest(user, AUTH_USER) and hmac.compare_digest(
        password, AUTH_PASSWORD
    )


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def do_GET(self):
        if not auth_ok(self.headers.get("Authorization")):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="app"')
            self.end_headers()
            return
        if self.path == "/api/health":
            return self.send_json({"ok": True})
        super().do_GET()

    def send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    print(f"serving on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
