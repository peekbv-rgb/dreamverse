"""Dreamverse — webserver.

Serveert de speler uit static/ en drie eindpunten:

    POST   /api/episode      {"dream": "..."}  -> de verbeelding
    GET    /api/profile                        -> wie de dromer is
    GET    /api/usage                          -> wat het tot nu toe gekost heeft
    GET    /api/account                        -> pakket, saldo en wat er over is
    POST   /api/account                        -> pakket of saldo zetten (tijdelijk)
    POST   /api/profile      {"name": "..."}   -> naam onthouden
    POST   /api/answer                         -> antwoord op de slotvraag bewaren
    POST   /api/extra                          -> losse aankoop met tokens
    GET    /api/episode/<nr>                   -> een eerdere verbeelding terugkijken
    POST   /api/episode/<nr>/herstel           -> de duiding opnieuw schrijven bij oude panelen
    POST   /api/dream/<nr>/vooruitblik         -> de dromer zegt of de vooruitblik uitkwam
    GET    /api/panels/<nr>                    -> de stand van het tekenwerk
    POST   /api/kopen        {"soort", "welk"}  -> betaal-url van Stripe
    POST   /api/portaal                        -> Stripe-pagina om op te zeggen
    POST   /api/stripe/webhook                 -> Stripe meldt een betaling
    POST   /api/vera/session                   -> WebRTC-gegevens voor een gesprek
    DELETE /api/vera/session/<id>              -> gesprek afsluiten
    GET    /api/archive                        -> alle eerdere dromen
    GET    /api/spectrum                       -> welk kleurveld elke droom koos
    GET    /api/mijn-gegevens                  -> alles wat we bewaren, als zip
    POST   /api/account-verwijderen            -> alles weg, onomkeerbaar
    DELETE /api/dream/<nr>                     -> een droom en al zijn beelden wissen
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

import accounts
import betalen
import mail
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

# Pakket en tokensaldo met de hand zetten kan alleen met deze sleutel. Staat hij
# niet in de omgeving, dan kan het helemaal niet - dat is de veilige stand.
# Zonder dit kon iedereen die de app kon bereiken zichzelf Ultra geven met tien
# avatarminuten erbij, en dat is echt geld.
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

# E-mailverificatie. Uit, tenzij je het aanzet. Het mechanisme staat er - een
# code per account, een eindpunt om hem in te wisselen - maar versturen vraagt
# SMTP-gegevens, en een extra stap tussen iemand en zijn eerste droom kost je
# testpersonen. Zolang dit uit staat wordt de code naar de log geschreven.
VERIFICATIE_NODIG = os.environ.get("VERIFICATIE_NODIG", "").lower() in ("1", "ja", "true")
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


# Wat je mag zien zonder in te loggen: de pagina zelf, de opmaak, Vera's
# introductiefilmpje, en de twee eindpunten die je nodig hebt om in te loggen.
# Al het andere hoort bij iemand.
VRIJ = ("/api/health", "/api/registreren", "/api/inloggen", "/api/uitloggen",
        "/api/bevestigen", "/api/stripe/webhook",
        "/api/wachtwoord-vergeten", "/api/wachtwoord-herstellen")

# Paden waar basic auth nooit voor mag staan, ook niet als AUTH_USER en
# AUTH_PASSWORD gevuld zijn.
#
# De webhook: Stripe stuurt geen wachtwoord mee en kan dat ook niet. Staat basic
# auth ervoor, dan krijgt elke betaalmelding een 401 en slaat er nooit een pakket
# om - stil, want de klant heeft wél betaald.
#
# De privacyverklaring: die moet leesbaar zijn zonder account. Een verklaring
# achter een wachtwoord beschermt niemand.
ZONDER_BASIC = ("/api/stripe/webhook", "/privacy.html", "/herstel.html")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.gebruiker = None
        super().__init__(*args, directory=str(STATIC), **kwargs)

    # -- helpers ------------------------------------------------------------ #

    def send_json(self, payload, status=200, cookie=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def sessie_cookie(self, token):
        """HttpOnly, zodat JavaScript er niet bij kan; SameSite=Lax tegen
        verzoeken die een andere site namens jou verstuurt. Secure alleen als we
        via https draaien - anders werkt hij niet op localhost."""
        veilig = "; Secure" if os.environ.get("RENDER") else ""
        return ("{}={}; Path=/; Max-Age={}; HttpOnly; SameSite=Lax{}".format(
            accounts.SESSIE_COOKIE, token, accounts.SESSIE_DAGEN * 86400, veilig))

    def wis_cookie(self):
        return "{}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax".format(accounts.SESSIE_COOKIE)

    def sessietoken(self):
        rauw = self.headers.get("Cookie") or ""
        for stuk in rauw.split(";"):
            naam, _, waarde = stuk.strip().partition("=")
            if naam == accounts.SESSIE_COOKIE:
                return waarde
        return ""

    def guard(self):
        kaal = self.path.split("?")[0]
        if kaal not in ZONDER_BASIC and not auth_ok(self.headers.get("Authorization")):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="dreamverse"')
            self.end_headers()
            return False

        # Wie is er aan de lijn? Dit staat in een thread-lokale plek, want de
        # server draait één thread per verzoek en de rest van de code zou anders
        # een gebruikers-id door twintig functies heen moeten doorgeven.
        self.gebruiker = accounts.uit_sessie(self.sessietoken())
        accounts.zet_huidige(self.gebruiker)

        # /panels/ hoort er ook bij: dat zijn andermans dromen als plaatje.
        # Zonder deze regel viel de route erbuiten en klapte hij op een gebruiker
        # die None was, in plaats van netjes te weigeren.
        pad = self.path.split("?")[0]
        beschermd = pad.startswith("/api/") or pad.startswith("/panels/")
        if self.gebruiker or not beschermd or pad in VRIJ:
            return True
        self.send_json({"error": "Log eerst in.", "login": True}, 401)
        return False

    def read_raw(self):
        """De onbewerkte body. De webhook van Stripe heeft die letterlijk nodig:
        de handtekening gaat over precies deze bytes, dus parsen en opnieuw
        samenstellen maakt hem ongeldig."""
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return b""
        return self.rfile.read(length)

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
            return self.send_json(dreamverse.public_profile())
        if self.path == "/api/mijn-gegevens":
            # Het recht op inzage en overdraagbaarheid: alles wat we bewaren,
            # in één zip, inclusief het beeld.
            blob = dreamverse.uitvoer()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Content-Disposition",
                             'attachment; filename="dreamverse-mijn-gegevens.zip"')
            self.end_headers()
            self.wfile.write(blob)
            return

        if self.path == "/api/spectrum":
            return self.send_json(dreamverse.spectrum())
        if self.path == "/api/usage":
            return self.send_json(usage.summary())
        if self.path == "/api/account":
            a = plans.account()
            a["kwaliteiten"] = plans.kwaliteiten(
                dreamverse.load_profile().get("language", "nl"))
            return self.send_json(a)
        if self.path == "/api/archive":
            return self.send_json({"dreams": dreamverse.archive_with_media(),
                                   "samen": dreamverse.latest_together()})
        if self.path == "/api/health":
            return self.send_json({
                "ok": True,
                "key": dreamverse.credentials_available(),
                "kling": kling.enabled(),
                "vera": vera.enabled(),
                "betalen": betalen.enabled(),
                "mail": mail.enabled(),
            })
        if self.path.startswith("/api/episode/"):
            # Terugkijken kost niets: de tekst staat op schijf en de beelden ook.
            try:
                number = int(self.path.rsplit("/", 1)[1])
            except ValueError:
                return self.send_json({"error": "Onbekende verbeelding."}, 400)
            episode = dreamverse.load_episode(number)
            if episode is None:
                return self.send_json({"error": "Die verbeelding is er niet meer."}, 404)
            return self.send_json({"episode": episode})
        if self.path.startswith("/api/panels/"):
            try:
                number = int(self.path.rsplit("/", 1)[1])
            except ValueError:
                return self.send_json({"error": "Onbekende verbeelding."}, 400)
            state = kling.read_state(dreamverse.sleutel(number))
            if state is None:
                return self.send_json({"status": "off", "images": {}})
            return self.send_json(state)
        if self.path.startswith("/panels/"):
            # De gegenereerde panelen staan buiten static/, in data/. De naam
            # begint met het gebruikersnummer, en dat moet het jouwe zijn -
            # anders kun je met een gokje in andermans dromen kijken.
            name = os.path.basename(self.path.split("?")[0])
            if not name.startswith("{}_".format(self.gebruiker["id"])):
                return self.send_json({"error": "Niet gevonden."}, 404)
            target = kling.PANELS / name
            types = {".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
                     ".mp4": "video/mp4", ".mp3": "audio/mpeg"}
            if target.suffix.lower() not in types or not target.is_file():
                return self.send_json({"error": "Niet gevonden."}, 404)
            return self.send_file(target, types[target.suffix.lower()],
                                  "public, max-age=31536000, immutable")

        # Video's in static/ gaan ook langs send_file: zonder Range-antwoord kan
        # de browser niet spoelen, en dan is video.currentTime zetten zinloos.
        if self.path.split("?")[0].endswith((".mp4", ".mp3")):
            doel = STATIC / os.path.basename(self.path.split("?")[0])
            if doel.is_file():
                soort = "video/mp4" if doel.suffix == ".mp4" else "audio/mpeg"
                return self.send_file(doel, soort, "no-cache")

        super().do_GET()

    def send_file(self, target, content_type, cache):
        """Een bestand uitserveren, met Range als de browser erom vraagt.

        SimpleHTTPRequestHandler kent geen Range. Zonder dat meldt de browser
        seekable = [0, 0] en kan hij niet naar een ander punt in de video: geen
        scrubben, en geen terugspoelen naar de stille staart van Vera's
        begroeting.
        """
        omvang = target.stat().st_size
        bereik = self.headers.get("Range", "")
        begin, eind = 0, omvang - 1
        deel = False
        if bereik.startswith("bytes="):
            stukken = bereik[6:].split(",")[0].split("-")
            try:
                if stukken[0]:
                    begin = int(stukken[0])
                    if stukken[1]:
                        eind = min(int(stukken[1]), omvang - 1)
                elif stukken[1]:
                    begin = max(0, omvang - int(stukken[1]))   # laatste N bytes
                deel = 0 <= begin <= eind < omvang
            except ValueError:
                deel = False
            if not deel and begin >= omvang:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */{}".format(omvang))
                self.end_headers()
                return

        with target.open("rb") as f:
            f.seek(begin)
            blob = f.read(eind - begin + 1)

        self.send_response(206 if deel else 200)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(blob)))
        if deel:
            self.send_header("Content-Range", "bytes {}-{}/{}".format(begin, eind, omvang))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(blob)

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

        if self.path == "/api/registreren":
            payload = self.read_json() or {}
            try:
                u = accounts.registreer(payload.get("email"), payload.get("wachtwoord"),
                                        payload.get("naam"))
            except accounts.AccountError as e:
                return self.send_json({"error": str(e)}, 400)
            # Meteen inloggen: een bevestigingsmail mag niet tussen iemand en
            # zijn eerste droom in staan. Bevestigen kan later.
            token = accounts.nieuwe_sessie(u["id"])
            accounts.zet_huidige(accounts.gebruiker(u["id"]))
            if not VERIFICATIE_NODIG:
                print("dreamverse: nieuw account {} (bevestigingscode {})".format(
                    u["email"], u["bevestig_code"]), flush=True)
            return self.send_json({"ok": True, "profile": dreamverse.public_profile()},
                                  cookie=self.sessie_cookie(token))

        if self.path == "/api/wachtwoord-vergeten":
            payload = self.read_json() or {}
            # Staat e-mail niet aan, dan hetzelfde antwoord voor iedereen -
            # ook voor een adres dat niet bestaat. Anders verschilt de melding
            # tussen wel en niet bestaand, en is dit alsnog een manier om uit te
            # zoeken wie er een account heeft.
            if not mail.enabled():
                gebruiker, code = accounts.vraag_herstel(payload.get("email"))
                if gebruiker and code:
                    # De link gaat naar de log, niet naar het antwoord. Hem hier
                    # teruggeven zou betekenen dat iedereen met een e-mailadres
                    # een wachtwoord kan wijzigen.
                    mail.herstelbericht(gebruiker["email"],
                                        "{}/herstel.html?code={}".format(
                                            betalen.basis_url(), code))
                return self.send_json({"ok": True, "melding":
                    "Het versturen van e-mail staat nog niet aan. Vraag de "
                    "beheerder om een nieuwe link."})

            gebruiker, code = accounts.vraag_herstel(payload.get("email"))
            if gebruiker and code:
                mail.herstelbericht(gebruiker["email"],
                                    "{}/herstel.html?code={}".format(
                                        betalen.basis_url(), code))
            return self.send_json({"ok": True, "melding":
                "Als dit adres bij een account hoort, staat er een link in je "
                "mail. Kijk ook in je spam."})

        if self.path == "/api/wachtwoord-herstellen":
            payload = self.read_json() or {}
            try:
                token = accounts.herstel(payload.get("code"), payload.get("nieuw"))
            except accounts.AccountError as e:
                return self.send_json({"error": str(e)}, 400)
            accounts.zet_huidige(accounts.uit_sessie(token))
            return self.send_json({"ok": True, "profile": dreamverse.public_profile()},
                                  cookie=self.sessie_cookie(token))

        if self.path == "/api/inloggen":
            payload = self.read_json() or {}
            try:
                token = accounts.inloggen(payload.get("email"), payload.get("wachtwoord"))
            except accounts.AccountError as e:
                return self.send_json({"error": str(e)}, 401)
            accounts.zet_huidige(accounts.uit_sessie(token))
            return self.send_json({"ok": True, "profile": dreamverse.public_profile()},
                                  cookie=self.sessie_cookie(token))

        if self.path == "/api/uitloggen":
            accounts.sessie_weg(self.sessietoken())
            accounts.zet_huidige(None)
            return self.send_json({"ok": True}, cookie=self.wis_cookie())

        if self.path == "/api/wachtwoord":
            payload = self.read_json() or {}
            try:
                token = accounts.zet_wachtwoord(self.gebruiker["id"],
                                                payload.get("oud"), payload.get("nieuw"))
            except accounts.AccountError as e:
                return self.send_json({"error": str(e)}, 400)
            return self.send_json({"ok": True}, cookie=self.sessie_cookie(token))

        if self.path == "/api/stripe/webhook":
            # Geen sessie: Stripe belt aan zonder cookie. De handtekening is hier
            # het enige bewijs, en zonder die controle kan iedereen die dit adres
            # kent zichzelf Ultra geven.
            try:
                gebeurtenis = betalen.lees_gebeurtenis(
                    self.read_raw(), self.headers.get("Stripe-Signature") or "")
            except betalen.BetaalError as e:
                self.log_message("webhook geweigerd: %s", e)
                return self.send_json({"error": str(e)}, 400)
            try:
                wat = betalen.verwerk(gebeurtenis)
            except Exception as e:
                # Een 500 laat Stripe het opnieuw proberen, en dat is wat je wilt
                # als het aan onze kant misging.
                self.log_message("webhook %s mislukte: %s", gebeurtenis.get("type"), e)
                return self.send_json({"error": "niet verwerkt"}, 500)
            self.log_message("webhook %s: %s", gebeurtenis.get("type"), wat)
            return self.send_json({"ok": True, "wat": wat})

        if self.path == "/api/kopen":
            payload = self.read_json() or {}
            soort = payload.get("soort")
            welk = payload.get("welk") or ""
            try:
                if soort == "pakket":
                    url = betalen.koop_pakket(self.gebruiker, welk)
                elif soort == "tokens":
                    url = betalen.koop_tokens(self.gebruiker, welk)
                else:
                    return self.send_json({"error": "Onbekende aankoop."}, 400)
            except betalen.BetaalError as e:
                return self.send_json({"error": str(e)}, 400)
            except Exception as e:
                self.log_message("afrekenen mislukte: %s", e)
                return self.send_json({"error": "Afrekenen lukte niet."}, 502)
            return self.send_json({"url": url})

        if self.path == "/api/portaal":
            try:
                return self.send_json({"url": betalen.portaal(self.gebruiker)})
            except betalen.BetaalError as e:
                return self.send_json({"error": str(e)}, 400)
            except Exception as e:
                self.log_message("portaal mislukte: %s", e)
                return self.send_json({"error": "Dat lukte niet."}, 502)

        if self.path == "/api/account-verwijderen":
            # Met het wachtwoord erbij. Dit is onomkeerbaar, en een verdwaalde
            # klik of een openstaand tabblad op een gedeelde computer mag niet
            # iemands hele archief kosten.
            payload = self.read_json() or {}
            if not accounts.klopt_wachtwoord(payload.get("wachtwoord") or "",
                                             self.gebruiker["wachtwoord"]):
                return self.send_json({"error": "Je wachtwoord klopt niet."}, 401)
            try:
                uit = dreamverse.verwijder_account()
            except dreamverse.DreamverseError as e:
                return self.send_json({"error": str(e)}, 409)
            return self.send_json(uit, cookie=self.wis_cookie())

        if self.path == "/api/profile":
            payload = self.read_json() or {}
            return self.send_json(dreamverse.set_profile(payload))

        if self.path.startswith("/api/dream/") and self.path.endswith("/vooruitblik"):
            try:
                number = int(self.path.split("/")[3])
            except (ValueError, IndexError):
                return self.send_json({"error": "Onbekende droom."}, 400)
            payload = self.read_json() or {}
            try:
                return self.send_json({"dream": dreamverse.judge_future(
                    number, payload.get("verdict"))})
            except dreamverse.DreamverseError as e:
                return self.send_json({"error": str(e)}, 400)

        if self.path.startswith("/api/episode/") and self.path.endswith("/herstel"):
            # Dromen van voor het bewaren hebben wel beeld maar geen tekst meer.
            # Opnieuw schrijven kost geen beeld, dus ook geen tokens.
            try:
                number = int(self.path.split("/")[3])
            except (ValueError, IndexError):
                return self.send_json({"error": "Onbekende verbeelding."}, 400)
            try:
                return self.send_json({"episode": dreamverse.repair_episode(number)})
            except dreamverse.DreamverseError as e:
                return self.send_json({"error": str(e)}, 400)

        if self.path == "/api/extra":
            # Losse aankopen: het kernmoment op het beste model, of de hele
            # verbeelding als film. Eerst het saldo, dan pas het werk starten.
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
                return self.send_json({"error": "Die verbeelding is er niet meer."}, 404)

            # Bewegend beeld heeft een getekend paneel nodig als startframe.
            # Zonder die controle start de achtergrondtaak wel, wordt er
            # afgerekend, en pas daarna blijkt dat er niets te animeren viel.
            beelden = [b for b in kling.PANELS.glob("{}-[0-9].*".format(
                           dreamverse.sleutel(nummer)))
                       if b.suffix.lower() in (".png", ".jpg", ".webp")]
            if not beelden:
                return self.send_json({
                    "error": "Bij deze droom zijn geen panelen gemaakt, en bewegend beeld "
                             "heeft een getekend paneel nodig om mee te beginnen. Maak de "
                             "droom opnieuw met beeld erbij.",
                }, 409)

            import video
            if soort == "kernmoment_top":
                gestart = video.render_async(dreamverse.sleutel(nummer), episode["panels"],
                                             episode.get("key_panel"), plans.VIDEO["top"])
            elif soort == "film_snel":
                gestart = video.film_async(dreamverse.sleutel(nummer), episode["panels"],
                                           plans.VIDEO["snel"])
            elif soort == "film_top":
                gestart = video.film_async(dreamverse.sleutel(nummer), episode["panels"],
                                           plans.VIDEO["top"])
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
            # gezet - maar alleen door wie de beheerderssleutel heeft.
            if not ADMIN_TOKEN:
                return self.send_json({
                    "error": "Pakket en saldo aanpassen staat uit. Zet ADMIN_TOKEN in "
                             "de omgeving als je dit wilt kunnen.",
                }, 403)
            gegeven = (self.headers.get("X-Admin-Token") or "").strip()
            if not hmac.compare_digest(gegeven, ADMIN_TOKEN):
                self.log_message("account-aanpassing geweigerd: verkeerde sleutel")
                return self.send_json({"error": "Geen toegang."}, 403)
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
            episode = dreamverse.create(payload.get("dream", ""), payload.get("quality"))
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
        if self.path.startswith("/api/dream/"):
            try:
                nummer = int(self.path.rsplit("/", 1)[1])
            except ValueError:
                return self.send_json({"error": "Onbekende droom."}, 400)
            try:
                return self.send_json(dreamverse.delete_dream(nummer))
            except dreamverse.DreamverseError as e:
                return self.send_json({"error": str(e)}, 404)

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
        bij elke verbeelding een nieuwe naam.
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
        print("let op: geen inloggegevens — elke droom geeft het voorbeeld.", flush=True)
        print("        zet ANTHROPIC_API_KEY in .env, of draai: ant auth login", flush=True)
    print("panelen: {}".format("Kling" if kling.enabled() else "getekend (geen Kling-sleutels)"), flush=True)
    print("Vera   : {}".format(
        "aangesloten, max {}s per gesprek".format(vera.MAX_DURATION)
        if vera.enabled() else "niet aangesloten"), flush=True)
    print("dreamverse draait op http://{}:{}".format(HOST, PORT), flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
