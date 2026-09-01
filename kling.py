"""Kling — de panelen als echte illustraties.

Optioneel. Zonder KLING_ACCESS_KEY en KLING_SECRET_KEY gebeurt hier niets en
blijft de speler de getekende composities tonen. Dat is geen noodgreep maar het
ontwerp: beeld is een verrijking, geen voorwaarde, en een storing bij Kling mag
nooit betekenen dat iemand zijn aflevering niet krijgt.

Hoe het loopt:

    aflevering klaar  ->  achtergrondthread  ->  vijf taken bij Kling
                                              ->  afbeeldingen downloaden
                                              ->  data/panels/<nr>-<i>.jpg
    de browser vraagt intussen /api/panels/<nr> en schuift ze in beeld

De afbeeldingen worden bewust gedownload: de URL's van Kling verlopen, en een
aflevering die je over een maand terugkijkt hoort er nog te zijn.

LET OP - deze client is geschreven op de publieke documentatie, niet getest
tegen de echte API; er was hier geen sleutel. Klopt een veldnaam niet, dan zie
je dat meteen: draai `python kling.py --check` en de volledige respons komt in
beeld. Het model heet in oudere documentatie `model` in plaats van `model_name`;
staat allebei in KLING_FIELD hieronder.
"""

import base64
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
PANELS = ROOT / "data" / "panels"

BASE = os.environ.get("KLING_BASE", "https://api.klingai.com")
MODEL = os.environ.get("KLING_MODEL", "kling-v2")
# Sommige versies van de API heten het veld `model_name`, oudere `model`.
# We sturen ze allebei; een onbekend veld wordt genegeerd.
KLING_FIELD = ("model_name", "model")

TIMEOUT = 30
POLL_EVERY = 3
POLL_MAX = 40  # ~2 minuten; daarna geven we het op en blijft de tekening staan

# De stijl is per gebruiker vast: dat is precies wat een reeks tot een reeks maakt.
STYLE = os.environ.get(
    "KLING_STYLE",
    "dreamlike illustration, flowing ink and watercolour, soft luminous glow, "
    "sacred geometry faintly in the background, painterly, no text, no letters, no logos",
)

FIELD_LIGHT = {
    "root": "deep red light", "sacral": "warm orange light", "solar": "golden yellow light",
    "heart": "soft green light", "throat": "clear blue light", "third_eye": "indigo light",
    "crown": "violet light",
}


class KlingError(Exception):
    pass


# --------------------------------------------------------------------------- #
# Authenticatie
# --------------------------------------------------------------------------- #

def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def token(access_key, secret_key):
    """JWT met HS256. Handmatig, want het is tien regels en scheelt een pakket."""
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    now = int(time.time())
    payload = _b64(json.dumps(
        {"iss": access_key, "exp": now + 1800, "nbf": now - 5}, separators=(",", ":")
    ).encode())
    signing_input = header + b"." + payload
    signature = _b64(hmac.new(secret_key.encode(), signing_input, hashlib.sha256).digest())
    return (signing_input + b"." + signature).decode()


def credentials():
    ak = os.environ.get("KLING_ACCESS_KEY", "").strip()
    sk = os.environ.get("KLING_SECRET_KEY", "").strip()
    return (ak, sk) if ak and sk else None


def enabled():
    return credentials() is not None


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #

def _call(method, path, body=None):
    creds = credentials()
    if not creds:
        raise KlingError("Geen Kling-sleutels ingesteld.")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token(*creds),
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise KlingError("Kling gaf {} op {}: {}".format(e.code, path, detail))
    except urllib.error.URLError as e:
        raise KlingError("Kling niet bereikbaar: {}".format(e.reason))
    except json.JSONDecodeError:
        raise KlingError("Kling gaf geen JSON terug op {}".format(path))

    if payload.get("code") not in (0, None):
        raise KlingError("Kling meldt fout {}: {}".format(payload.get("code"), payload.get("message")))
    return payload


def submit(prompt, aspect_ratio="16:9"):
    body = {"prompt": prompt[:2400], "aspect_ratio": aspect_ratio, "n": 1}
    for field in KLING_FIELD:
        body[field] = MODEL
    payload = _call("POST", "/v1/images/generations", body)
    task_id = (payload.get("data") or {}).get("task_id")
    if not task_id:
        raise KlingError("Geen task_id in het antwoord: {}".format(json.dumps(payload)[:300]))
    return task_id


def result(task_id):
    """None zolang hij bezig is, anders de URL. Faalt de taak, dan een fout."""
    payload = _call("GET", "/v1/images/generations/" + task_id)
    data = payload.get("data") or {}
    status = data.get("task_status")
    if status in ("submitted", "processing", None):
        return None
    if status != "succeed":
        raise KlingError("Taak mislukt: {}".format(data.get("task_status_msg") or status))
    images = (data.get("task_result") or {}).get("images") or []
    if not images or not images[0].get("url"):
        raise KlingError("Taak geslaagd maar zonder afbeelding.")
    return images[0]["url"]


def download(url, target):
    req = urllib.request.Request(url, headers={"User-Agent": "dreamverse/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        blob = r.read()
    if len(blob) < 1024:
        raise KlingError("De afbeelding kwam leeg terug.")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    tmp.write_bytes(blob)
    tmp.replace(target)


# --------------------------------------------------------------------------- #
# Panelen
# --------------------------------------------------------------------------- #

def panel_prompt(panel):
    """Wat er te zien is, plus het kleurveld, plus de vaste stijl."""
    seen = (panel.get("image") or panel.get("narration") or "").strip()
    light = FIELD_LIGHT.get(panel.get("palette"), "soft light")
    return "{}. Lit by {}. {}".format(seen, light, STYLE)


def state_path(number):
    return PANELS / "{}.json".format(number)


def read_state(number):
    try:
        with state_path(number).open(encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_state(number, state):
    PANELS.mkdir(parents=True, exist_ok=True)
    tmp = state_path(number).with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(state_path(number))


def _render_all(number, panels):
    state = {"status": "busy", "images": {}, "errors": {}}
    _write_state(number, state)

    for i, panel in enumerate(panels):
        target = PANELS / "{}-{}.jpg".format(number, i)
        try:
            task_id = submit(panel_prompt(panel))
            url = None
            for _ in range(POLL_MAX):
                time.sleep(POLL_EVERY)
                url = result(task_id)
                if url:
                    break
            if not url:
                raise KlingError("Duurde te lang; overgeslagen.")
            download(url, target)
            state["images"][str(i)] = "/panels/{}".format(target.name)
        except KlingError as e:
            # Eén mislukt paneel is geen ramp: dat blijft gewoon de tekening.
            state["errors"][str(i)] = str(e)
            print("kling: paneel {} van droom {} mislukt: {}".format(i, number, e), flush=True)
        _write_state(number, state)

    state["status"] = "done"
    _write_state(number, state)


def render_async(number, panels):
    """Start het tekenwerk op de achtergrond. Geeft meteen terug."""
    if not enabled():
        return False
    threading.Thread(target=_render_all, args=(number, panels), daemon=True).start()
    return True


# --------------------------------------------------------------------------- #
# Controle vanaf de opdrachtregel
# --------------------------------------------------------------------------- #

def check():
    """Eén afbeelding maken en alles tonen wat er terugkomt."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    if not enabled():
        print("Geen KLING_ACCESS_KEY / KLING_SECRET_KEY in .env — niets te controleren.")
        return 1

    print("basis   :", BASE)
    print("model   :", MODEL)
    print("token   :", token(*credentials())[:32] + "…")
    prompt = panel_prompt({
        "image": "a figure gliding high above dark mountain ridges at night",
        "palette": "crown",
    })
    print("prompt  :", prompt[:120] + "…")

    try:
        task_id = submit(prompt)
        print("task_id :", task_id)
        for attempt in range(POLL_MAX):
            time.sleep(POLL_EVERY)
            url = result(task_id)
            print("  poging {}: {}".format(attempt + 1, url or "nog bezig"))
            if url:
                target = PANELS / "check.jpg"
                download(url, target)
                print("gelukt  :", target)
                return 0
        print("time-out: de taak werd niet op tijd klaar.")
        return 1
    except KlingError as e:
        print("FOUT    :", e)
        print("\nKlopt een veldnaam niet, pas dan KLING_FIELD of het pad in kling.py aan.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(check() if "--check" in sys.argv else print(__doc__) or 0)
