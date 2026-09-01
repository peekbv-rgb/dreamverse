"""Dreamverse — webserver.

Serveert de speler uit static/ en drie eindpunten:

    POST   /api/episode   {"dream": "..."}  -> de aflevering
    GET    /api/archive                     -> alle eerdere dromen
    DELETE /api/archive                     -> archief wissen

Geen framework: de standaardbibliotheek doet dit prima en het houdt de deploy
op één bestand. Basic auth gaat aan zodra AUTH_USER en AUTH_PASSWORD allebei
gevuld zijn — tijdens het testen laat je ze leeg.
"""

import base64
import hmac
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from dotenv import load_dotenv

import dreamverse

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

load_dotenv(ROOT / ".env")

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
AUTH_USER = os.environ.get("AUTH_USER", "")
AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "")
MAX_BODY = 64 * 1024


def auth_ok(header):
    """Basic auth. Uit zolang een van beide waarden leeg is."""
    if not (AUTH_USER and AUTH_PASSWORD):
        return True
    if not header or not header.startswith("Basic "):
        return False
    try:
        user, _, password = base64.b64decode(header[6:]).decode().partition(":")
    except Exception:
        return False
    # compare_digest op beide helften: een gewone == lekt de lengte via timing.
    return hmac.compare_digest(user, AUTH_USER) and hmac.compare_digest(password, AUTH_PASSWORD)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    # -- helpers ------------------------------------------------------------ #

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def guard(self):
        if auth_ok(self.headers.get("Authorization")):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="dreamverse"')
        self.end_headers()
        return False

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    # -- routes ------------------------------------------------------------- #

    def do_GET(self):
        if not self.guard():
            return
        if self.path == "/api/archive":
            archive = sorted(dreamverse.load_archive(), key=lambda d: d.get("n", 0), reverse=True)
            return self.send_json({"dreams": archive})
        if self.path == "/api/health":
            return self.send_json({"ok": True, "key": bool(os.environ.get("ANTHROPIC_API_KEY"))})
        super().do_GET()

    def do_POST(self):
        if not self.guard():
            return
        if self.path != "/api/episode":
            return self.send_json({"error": "Onbekend eindpunt."}, 404)

        payload = self.read_json()
        if payload is None:
            return self.send_json({"error": "Ongeldige aanvraag."}, 400)

        try:
            episode = dreamverse.create(payload.get("dream", ""))
        except dreamverse.DreamverseError as e:
            return self.send_json({"error": str(e)}, 400)
        except Exception:
            # Nooit een stacktrace naar de browser; wel naar de log.
            self.log_message("onverwachte fout bij het schrijven", )
            raise

        return self.send_json({"episode": episode})

    def do_DELETE(self):
        if not self.guard():
            return
        if self.path != "/api/archive":
            return self.send_json({"error": "Onbekend eindpunt."}, 404)
        dreamverse.clear_archive()
        return self.send_json({"ok": True})

    def log_message(self, fmt, *args):
        print("{} {}".format(self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("let op: geen ANTHROPIC_API_KEY — elke droom geeft de voorbeeldaflevering", flush=True)
    print("dreamverse draait op http://{}:{}".format(HOST, PORT), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
