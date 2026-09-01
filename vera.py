"""Vera als pratende avatar — de live sessie bij Runway.

De volgorde is vast en elke stap kan misgaan, dus ze staan hier los van elkaar:

    create   -> een sessie voor ons personage, geeft een id
    wait     -> pollen tot READY, want daarvoor bestaat de worker nog niet
    consume  -> de sessionKey inwisselen voor WebRTC-gegevens. Eenmalig.
    end      -> afsluiten, anders loopt de teller door

De browser krijgt alleen wat `consume` teruggeeft: een serveradres en een token
dat een paar minuten geldig is. RUNWAYML_API_SECRET verlaat dit proces nooit.

Let op bij `consume`: die is eenmalig. Loopt de WebRTC-verbinding daarna stuk,
dan is de sessie op en moet er een nieuwe komen — opnieuw consumen kan niet.
"""

import json
import os
import threading
import time
import urllib.error
import urllib.request

from runwayml import RunwayML

import plans
import usage

RUNWAY_VERSION = "2024-11-06"
POLL_TIMEOUT = 60
POLL_INTERVAL = 1.0

# Harde bovengrens per gesprek. Een avatar die blijft draaien kost geld, en een
# droom vertellen duurt geen half uur. Runway kapt zelf af op deze waarde; de
# klok in de browser is alleen om het zichtbaar te maken, geen beveiliging.
MAX_DURATION = max(60, min(1800, int(os.environ.get("VERA_MAX_DURATION", "300"))))

_client = None
_lock = threading.Lock()
_begroeting = None   # welke openingszin er nu bij Runway staat


class VeraError(Exception):
    """Melding die de bezoeker te zien mag krijgen."""


def character_id():
    return (os.environ.get("RUNWAY_CHARACTER_ID") or "").strip()


def enabled():
    """Alleen aan als er een sleutel én een geldig personage-id staat."""
    cid = character_id()
    return bool(os.environ.get("RUNWAYML_API_SECRET")) and len(cid) == 36


def client():
    global _client
    with _lock:
        if _client is None:
            _client = RunwayML()
        return _client


def begroeting_voor(naam):
    """De openingszin, met de naam erin als we die kennen."""
    basis = ("Vertel me wat je vannacht zag, voordat het wegzakt — "
             "het hoeft niet op volgorde en het hoeft niet te kloppen.")
    if naam:
        kop = "Goedemorgen {}. Heb je lekker geslapen?".format(naam)
    else:
        kop = "Goedemorgen. Hier is Vera, heb je lekker geslapen?"
    return kop + "\n" + basis


def zet_begroeting(naam):
    """Werk Vera's openingszin bij zodat ze de dromer bij naam begroet.

    Alleen als hij veranderd is: elke aanroep kost tijd, en het inhoudsfilter van
    Runway weigert regelmatig een tekst die er niets mis mee heeft. Lukt het niet,
    dan gaat het gesprek gewoon door met de oude zin — een begroeting is het niet
    waard om een gesprek voor af te blazen.
    """
    global _begroeting
    nieuw = begroeting_voor(naam)
    if nieuw == _begroeting:
        return True
    for poging in range(4):
        try:
            client().avatars.update(character_id(), start_script=nieuw)
            _begroeting = nieuw
            return True
        except Exception as e:
            if "cannot be used for an avatar" not in str(e):
                print("vera: openingszin bijwerken mislukte: {}".format(str(e)[:120]), flush=True)
                return False
            time.sleep(2)
    print("vera: het filter weigerde de openingszin vier keer; oude zin blijft staan", flush=True)
    return False


def create(duur=None):
    duur = duur or MAX_DURATION
    c = client()
    created = c.realtime_sessions.create(
        model="gwm1_avatars",
        avatar={"type": "custom", "avatar_id": character_id()},
        max_duration=duur,
    )
    return created.id


def wait_until_ready(session_id):
    """Pollen tot READY. Geeft de sessionKey terug of legt uit waarom niet."""
    c = client()
    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        session = c.realtime_sessions.retrieve(session_id)
        status = session.status
        if status == "READY":
            return session.session_key
        if status == "FAILED":
            raise VeraError("Vera kon niet starten: {}".format(
                getattr(session, "failure", None) or getattr(session, "failure_code", "onbekend")))
        if status in ("CANCELLED", "COMPLETED"):
            raise VeraError("De sessie was al afgelopen voordat je verbond.")
        time.sleep(POLL_INTERVAL)
    raise VeraError("Vera reageerde niet binnen een minuut. Probeer het opnieuw.")


def consume(session_id, session_key):
    """Wissel de sessionKey in voor WebRTC-gegevens. Eenmalig."""
    c = client()
    req = urllib.request.Request(
        "{}/v1/realtime_sessions/{}/consume".format(c.base_url, session_id),
        # Een lege body wordt geweigerd met "Incorrect content type", dus een
        # expliciet leeg JSON-object.
        data=b"{}",
        method="POST",
        headers={
            "Authorization": "Bearer {}".format(session_key),
            "X-Runway-Version": RUNWAY_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise VeraError("Verbinden mislukte ({}): {}".format(
            e.code, e.read().decode("utf-8", "replace")[:200]))
    except urllib.error.URLError as e:
        raise VeraError("Runway niet bereikbaar: {}".format(e.reason))


def end(session_id):
    """Sessie afsluiten zodat de teller stopt. Faalt stil: het is opruimwerk."""
    rec = usage.session_ended(session_id, MAX_DURATION)
    # Afrekenen op werkelijk gesproken tijd, pas als het gesprek voorbij is.
    try:
        plans.charge_call(rec.get("seconds", 0))
    except Exception as e:
        print("vera: afrekenen mislukte voor {}: {}".format(session_id, e), flush=True)
    try:
        client().realtime_sessions.delete(session_id)
        return True
    except Exception as e:
        print("vera: afsluiten van {} mislukte: {}".format(session_id, e), flush=True)
        return False


def start():
    """De hele keten. Geeft terug wat de browser mag weten, en niets meer."""
    if not enabled():
        raise VeraError("Vera is niet aangesloten: zet RUNWAYML_API_SECRET en "
                        "RUNWAY_CHARACTER_ID in .env.")
    # Hoeveel mag deze beller? Weigeren gebeurt hier, vóór er een worker draait.
    toegestaan, uit_tokens = plans.check_call()
    duur = max(60, min(MAX_DURATION, int(toegestaan)))

    # Ken je de naam, laat haar die dan uitspreken. Gebeurt vóór het aanmaken
    # van de sessie, want daarna leest de worker de openingszin niet meer.
    try:
        import dreamverse
        zet_begroeting((dreamverse.load_profile().get("name") or "").strip())
    except Exception as e:
        print("vera: naam ophalen mislukte: {}".format(str(e)[:100]), flush=True)

    session_id = create(duur)
    try:
        session_key = wait_until_ready(session_id)
        creds = consume(session_id, session_key)
    except Exception:
        end(session_id)  # nooit een sessie laten hangen die niemand gebruikt
        raise
    usage.session_started(session_id)
    return {
        "session_id": session_id,
        # Het veld heet `url` in de consume-respons, niet serverUrl. De rest
        # staat erbij voor het geval een volgende versie het anders noemt.
        "server_url": creds.get("url") or creds.get("serverUrl") or creds.get("server_url"),
        "token": creds.get("token"),
        "room": creds.get("roomName"),
        "max_duration": duur,
        "uit_tokens": uit_tokens,
    }
