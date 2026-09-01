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

import os
import threading
import time

import httpx
from runwayml import RunwayML

RUNWAY_VERSION = "2024-11-06"
POLL_TIMEOUT = 60
POLL_INTERVAL = 1.0

# Harde bovengrens per gesprek. Een avatar die blijft draaien kost geld, en een
# droom vertellen duurt geen half uur. Runway kapt zelf af op deze waarde; de
# klok in de browser is alleen om het zichtbaar te maken, geen beveiliging.
MAX_DURATION = max(60, min(1800, int(os.environ.get("VERA_MAX_DURATION", "300"))))

_client = None
_lock = threading.Lock()


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


def create():
    c = client()
    created = c.realtime_sessions.create(
        model="gwm1_avatars",
        avatar={"type": "custom", "avatar_id": character_id()},
        max_duration=MAX_DURATION,
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
    response = httpx.post(
        "{}/v1/realtime_sessions/{}/consume".format(c.base_url, session_id),
        headers={
            "Authorization": "Bearer {}".format(session_key),
            "X-Runway-Version": RUNWAY_VERSION,
        },
        # Zonder expliciete body stuurt httpx niets en weigert de API het
        # verzoek met "Incorrect content type".
        json={},
        timeout=30,
    )
    if response.status_code >= 400:
        raise VeraError("Verbinden mislukte ({}): {}".format(
            response.status_code, response.text[:200]))
    return response.json()


def end(session_id):
    """Sessie afsluiten zodat de teller stopt. Faalt stil: het is opruimwerk."""
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
    session_id = create()
    try:
        session_key = wait_until_ready(session_id)
        creds = consume(session_id, session_key)
    except Exception:
        end(session_id)  # nooit een sessie laten hangen die niemand gebruikt
        raise
    return {
        "session_id": session_id,
        # Het veld heet `url` in de consume-respons, niet serverUrl. De rest
        # staat erbij voor het geval een volgende versie het anders noemt.
        "server_url": creds.get("url") or creds.get("serverUrl") or creds.get("server_url"),
        "token": creds.get("token"),
        "room": creds.get("roomName"),
        "max_duration": MAX_DURATION,
    }
