"""Dreamverse — webserver.

Serveert de speler uit static/ en drie eindpunten:

    POST   /api/episode      {"dream": "..."}  -> de aflevering
    GET    /api/profile                        -> wie de dromer is
    GET    /api/usage                          -> wat het tot nu toe gekost heeft
    GET    /api/account                        -> pakket, saldo en wat er over is
    POST   /api/account                        -> pakket of saldo zetten (tijdelijk)
    POST   /api/profile      {"name": "..."}   -> naam onthouden
    POST   /api/answer                         -> antwoord op de slotvraag bewaren
    POST   /api/extra                          -> losse aankoop met tokens
    GET    /api/episode/<nr>                   -> een eerdere aflevering terugkijken
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
import plans
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
        if self.path == "/api/account":
            return self.send_json(plans.account())
        if self.path == "/api/archive":
            archive = sorted(dreamverse.load_archive(), key=lambda d: d.get("n", 0), reverse=True)
            return self.send_json({"dreams": archive})
        if self.path == "/api/health":
            return self.send_json({
                "ok": True,
                "key": dreamverse.credentials_available(),
                "kling": kling.enabled(),
                "vera": vera.enabled(),
            })
        if self.path.startswith("/api/episode/"):
            # Terugkijken kost niets: de tekst staat op schijf en de beelden ook.
            try:
                number = int(self.path.rsplit("/", 1)[1])
            except ValueError:
                return self.send_json({"error": "Onbekende aflevering."}, 400)
            episode = dreamverse.load_episode(number)
            if episode is None:
                return self.send_json({"error": "Die aflevering is er niet meer."}, 404)
            return self.send_json({"episode": episode})
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
            types = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
                     ".mp4": "video/mp4", ".mp3": "audio/mpeg"}
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
            except plans.Refused as e:
                return self.send_json({"error": str(e), "need_tokens": e.need_tokens}, 402)
            except vera.VeraError as e:
                return self.send_json({"error": str(e)}, 502)
            except Exception as e:
                self.log_message("vera-sessie mislukte: %s", e)
                return self.send_json({"error": "Vera kon niet opstarten."}, 502)

        if self.path == "/api/profile":
            payload = self.read_json() or {}
            return self.send_json(dreamverse.set_name(payload.get("name", "")))

        if self.path == "/api/extra":
            # Losse aankopen: het kernmoment op het beste model, of de hele
            # aflevering als film. Eerst het saldo, dan pas het werk starten.
            payload = self.read_json() or {}
            soort = payload.get("kind", "")
            try:
                nummer = int(payload.get("dream", 0))
                plans.check_extra(soort)
            except plans.Refused as e:
                return self.send_json({"error": str(e), "need_tokens": e.need_tokens}, 402)
            except (ValueError, TypeError):
                return self.send_json({"error": "Ongeldige aanvraag."}, 400)

            episode = dreamverse.load_episode(nummer)
            if not episode:
                return self.send_json({"error": "Die aflevering is er niet meer."}, 404)

            import video
            if soort == "kernmoment_top":
                gestart = video.render_async(nummer, episode["panels"],
                                             episode.get("key_panel"), plans.VIDEO["top"])
            elif soort == "film_snel":
                gestart = video.film_async(nummer, episode["panels"], plans.VIDEO["snel"])
            elif soort == "film_top":
                gestart = video.film_async(nummer, episode["panels"], plans.VIDEO["top"])
            else:
                gestart = False

            if not gestart:
                return self.send_json({"error": "Dit kon niet gestart worden."}, 500)
            plans.charge_extra(soort)
            return self.send_json({"ok": True, "kind": soort, "account": plans.account()})

        if self.path == "/api/answer":
            payload = self.read_json() or {}
            try:
                return self.send_json(dreamverse.answer_question(
                    int(payload.get("dream", 0)), payload.get("answer", "")))
            except (dreamverse.DreamverseError, ValueError, TypeError) as e:
                return self.send_json({"error": str(e)}, 400)

        if self.path == "/api/account":
            # Zolang er geen betaling is, worden pakket en saldo met de hand
            # gezet. Dit eindpunt moet dicht voordat dit ergens publiek draait.
            payload = self.read_json() or {}
            try:
                if payload.get("plan"):
                    plans.set_plan(payload["plan"])
                if payload.get("tokens") is not None:
                    plans.add_tokens(int(payload["tokens"]))
            except (plans.Refused, ValueError, TypeError) as e:
                return self.send_json({"error": str(e)}, 400)
            return self.send_json(plans.account())

        if self.path != "/api/episode":
            return self.send_json({"error": "Onbekend eindpunt."}, 404)

        payload = self.read_json()
        if payload is None:
            return self.send_json({"error": "Ongeldige aanvraag."}, 400)

        try:
            episode = dreamverse.create(payload.get("dream", ""))
        except plans.Refused as e:
            return self.send_json({"error": str(e), "need_tokens": e.need_tokens}, 402)
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

    def end_headers(self):
        """Pagina, stijl en script moeten na een deploy meteen vernieuwen.

        Zonder dit haalt een browser de nieuwe HTML op maar houdt hij de oude
        stylesheet, en dan verschijnen er elementen zonder de opmaak die erbij
        hoort. Afbeeldingen en video mogen wel lang blijven staan: die krijgen
        bij elke aflevering een nieuwe naam.
        """
        pad = self.path.split("?")[0]
        if pad.endswith((".css", ".js", ".html", "/")):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):
        print("{} {}".format(self.address_string(), fmt % args), flush=True)


def poort_al_bezet():
    """Draait er al een server op deze poort?

    Windows staat toe dat twee processen op dezelfde poort luisteren, en dan
    beantwoordt de oudste de verzoeken — met oude code. Dat heeft hier drie keer
    voor verwarrende uitkomsten gezorgd, dus weigeren we te starten.
    """
    import urllib.error
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:{}/api/health".format(PORT), timeout=2)
        return True
    except urllib.error.HTTPError:
        return True          # antwoordt iets, dus er zit iemand
    except Exception:
        return False


if __name__ == "__main__":
    if poort_al_bezet():
        raise SystemExit("\n".join([
            "Er luistert al iets op poort {}. Stop dat eerst, anders beantwoordt".format(PORT),
            "de oude server je verzoeken met oude code. In PowerShell:",
            "",
            "  Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" |",
            "    Where-Object { $_.CommandLine -like '*server.py*' } | Stop-Process -Force",
        ]))
    if not dreamverse.credentials_available():
        print("let op: geen inloggegevens — elke droom geeft de voorbeeldaflevering.", flush=True)
        print("        zet ANTHROPIC_API_KEY in .env, of draai: ant auth login", flush=True)
    print("panelen: {}".format("Kling" if kling.enabled() else "getekend (geen Kling-sleutels)"), flush=True)
    print("Vera   : {}".format(
        "aangesloten, max {}s per gesprek".format(vera.MAX_DURATION)
        if vera.enabled() else "niet aangesloten"), flush=True)
    print("dreamverse draait op http://{}:{}".format(HOST, PORT), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
