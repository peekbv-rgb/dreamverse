"""Dreamverse — webserver.

Serveert de speler uit static/ en drie eindpunten:

    POST   /api/episode      {"dream": "..."}  -> de aflevering
    GET    /api/profile                        -> wie de dromer is
    GET    /api/usage                          -> wat het tot nu toe gekost heeft
    POST   /api/profile      {"name": "..."}   -> naam onthouden
    GET    /api/panels/<nr>                    -> de stand van het tekenwerk
    POST   /api/vera/session                   -> WebRTC-gegevens voor een gesprek
    DELETE /api/vera/session/<id>              -> gesprek afsluiten
    GET    /api/archive                        -> alle eerdere dromen
    DELETE /api/archive                        -> archief wissen

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
import kling
import vera
import usage

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
        if self.path == "/api/profile":
            return self.send_json(dreamverse.load_profile())
        if self.path == "/api/usage":
            return self.send_json(usage.summary())
        if self.path == "/api/archive":
            archive = sorted(dreamverse.load_archive(), key=lambda d: d.get("n", 0), reverse=True)
            return self.send_json({"dreams": archive})
        if self.path == "/api/health":
            return self.send_json({
                "ok": True,
                "key": bool(os.environ.get("ANTHROPIC_API_KEY")),
                "kling": kling.enabled(),
                "vera": vera.enabled(),
            })
        if self.path.startswith("/api/panels/"):
            try:
                number = int(self.path.rsplit("/", 1)[1])
            except ValueError:
                return self.send_json({"error": "Onbekende aflevering."}, 400)
            state = kling.read_state(number)
            if state is None:
                return self.send_json({"status": "off", "images": {}})
            return self.send_json(state)
        if self.path.startswith("/panels/"):
            # De gegenereerde panelen staan buiten static/, in data/.
            name = os.path.basename(self.path)
            target = kling.PANELS / name
            types = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp"}
            if target.suffix.lower() not in types or not target.is_file():
                return self.send_json({"error": "Niet gevonden."}, 404)
            blob = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", types[target.suffix.lower()])
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(blob)
            return
        super().do_GET()

    def do_POST(self):
        if not self.guard():
            return

        if self.path == "/api/vera/session":
            try:
                return self.send_json(vera.start())
            except vera.VeraError as e:
                return self.send_json({"error": str(e)}, 502)
            except Exception as e:
                self.log_message("vera-sessie mislukte: %s", e)
                return self.send_json({"error": "Vera kon niet opstarten."}, 502)

        if self.path == "/api/profile":
            payload = self.read_json() or {}
            return self.send_json(dreamverse.set_name(payload.get("name", "")))

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
        if self.path.startswith("/api/vera/session/"):
            session_id = self.path.rsplit("/", 1)[1]
            # Alleen de vorm controleren; Runway weigert onbekende ids zelf.
            if not session_id or len(session_id) > 64:
                return self.send_json({"error": "Onbekende sessie."}, 400)
            return self.send_json({"ok": vera.end(session_id)})
        if self.path != "/api/archive":
            return self.send_json({"error": "Onbekend eindpunt."}, 404)
        dreamverse.clear_archive()
        return self.send_json({"ok": True})

    def log_message(self, fmt, *args):
        print("{} {}".format(self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("let op: geen ANTHROPIC_API_KEY — elke droom geeft de voorbeeldaflevering", flush=True)
    print("panelen: {}".format("Kling" if kling.enabled() else "getekend (geen Kling-sleutels)"), flush=True)
    print("Vera   : {}".format(
        "aangesloten, max {}s per gesprek".format(vera.MAX_DURATION)
        if vera.enabled() else "niet aangesloten"), flush=True)
    print("dreamverse draait op http://{}:{}".format(HOST, PORT), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
