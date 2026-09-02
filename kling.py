"""Kling — de panelen als echte illustraties.

Optioneel. Zonder KLING_ACCESS_KEY en KLING_SECRET_KEY gebeurt hier niets en
blijft de speler de getekende composities tonen. Dat is geen noodgreep maar het
ontwerp: beeld is een verrijking, geen voorwaarde, en een storing bij Kling mag
nooit betekenen dat iemand zijn verbeelding niet krijgt.

Hoe het loopt:

    verbeelding klaar  ->  achtergrondthread  ->  vijf taken bij Kling
                                              ->  afbeeldingen downloaden
                                              ->  data/panels/<nr>-<i>.jpg
    de browser vraagt intussen /api/panels/<nr> en schuift ze in beeld

De afbeeldingen worden bewust gedownload: de URL's van Kling verlopen, en een
verbeelding die je over een maand terugkijkt hoort er nog te zijn.

Geschreven tegen de officiele documentatie op kling.ai/document-api (gelezen op
1 september 2026), maar niet uitgevoerd tegen de echte API - er was hier geen
sleutel. Draai daarom eerst `python kling.py --check`: die maakt een afbeelding
en drukt af wat er terugkomt.

Kling wist gegenereerde afbeeldingen na dertig dagen. Daarom halen we ze binnen
en bewaren we ze zelf; een droom van vorige maand hoort er over een jaar nog te
zijn.
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

import usage

ROOT = Path(__file__).parent
PANELS = ROOT / "data" / "panels"

BASE = os.environ.get("KLING_BASE", "https://api-singapore.klingai.com")
# Twee manieren om je te legitimeren, afhankelijk van waar je sleutel vandaan komt:
#   Kuaishou zelf  -> KLING_ACCESS_KEY + KLING_SECRET_KEY, waarmee we een JWT maken
#   een tussenpartij -> KLING_API_KEY, één bearer-token dat we onveranderd meesturen
# Staat het allebei ingevuld, dan wint de bearer: die is expliciet gekozen.
# Keuze uit kling-v1, kling-v1-5, kling-v2, kling-v2-new, kling-v2-1, kling-v3.
# v2-1 is wat Kling zelf in hun voorbeeld gebruikt; v3 is nieuwer en duurder.
MODEL = os.environ.get("KLING_MODEL", "kling-v2-1")
RESOLUTION = os.environ.get("KLING_RESOLUTION", "1k")  # 1k of 2k

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
    bearer = os.environ.get("KLING_API_KEY", "").strip()
    if bearer:
        return ("bearer", bearer)
    ak = os.environ.get("KLING_ACCESS_KEY", "").strip()
    sk = os.environ.get("KLING_SECRET_KEY", "").strip()
    if ak and sk:
        return ("jwt", ak, sk)
    return None


def auth_header():
    creds = credentials()
    if not creds:
        raise KlingError("Geen Kling-sleutel ingesteld.")
    if creds[0] == "bearer":
        return "Bearer " + creds[1]
    return "Bearer " + token(creds[1], creds[2])


def mode():
    creds = credentials()
    return creds[0] if creds else "uit"


def enabled():
    return credentials() is not None


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #

def _call(method, path, body=None):
    header = auth_header()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": header,
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
    body = {
        "model_name": MODEL,          # het oude veld heette `model` en betekent nu v1
        "prompt": prompt[:2500],      # harde grens van de API
        "aspect_ratio": aspect_ratio,
        "resolution": RESOLUTION,
        "n": 1,
    }
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


def download(url, stem):
    """Haal de afbeelding op en bewaar hem met de extensie die bij de inhoud past.

    Kling levert PNG waar de URL soms iets anders suggereert, dus we kijken naar
    de eerste bytes in plaats van naar de naam. Geeft het pad terug.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "dreamverse/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        blob = r.read()
    if len(blob) < 1024:
        raise KlingError("De afbeelding kwam leeg terug.")

    # Magische bytes in hex, zodat er geen escapes in deze bron hoeven te staan.
    if blob.startswith(bytes.fromhex("89504e470d0a1a0a")):
        suffix = ".png"
    elif blob.startswith(bytes.fromhex("ffd8")):
        suffix = ".jpg"
    elif blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        suffix = ".webp"
    else:
        raise KlingError("Onbekend beeldformaat; niet opgeslagen.")

    target = stem.with_suffix(suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = stem.with_suffix(".part")
    tmp.write_bytes(blob)
    tmp.replace(target)
    return target


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
    """De eigen velden wegschrijven zonder die van de anderen te wissen.

    Drie schrijvers delen dit bestand: het tekenwerk hier, de verteller in
    stem.py en de video in video.py. Wie zijn hele woordenboek wegschrijft, gooit
    het werk van de andere twee weg - en dat gebeurde: de stem was klaar en de
    stand meldde daarna dat er geen stem was.
    """
    PANELS.mkdir(parents=True, exist_ok=True)
    pad = state_path(number)
    try:
        with pad.open(encoding="utf-8") as f:
            heel = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        heel = {}
    heel.update(state)
    tmp = pad.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(heel, f, ensure_ascii=False, indent=2)
    tmp.replace(pad)


def _render_all(number, panels, key_index=None, video_instelling=None):
    state = {"status": "busy", "images": {}, "errors": {}}
    _write_state(number, state)

    for i, panel in enumerate(panels):
        stem = PANELS / "{}-{}".format(number, i)
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
            target = download(url, stem)
            state["images"][str(i)] = "/panels/{}".format(target.name)
            usage.panel(number, i, ok=True)
        except KlingError as e:
            # Eén mislukt paneel is geen ramp: dat blijft gewoon de tekening.
            state["errors"][str(i)] = str(e)
            usage.panel(number, i, ok=False)
            print("kling: paneel {} van droom {} mislukt: {}".format(i, number, e), flush=True)
        _write_state(number, state)

    state["status"] = "done"
    _write_state(number, state)

    # De panelen staan er; nu mag het kernmoment gaan bewegen.
    if video_instelling and key_index is not None:
        import video
        video.render_async(number, panels, key_index, video_instelling)


def render_async(number, panels, key_index=None, video_instelling=None):
    """Start het tekenwerk op de achtergrond. Geeft meteen terug."""
    if not enabled():
        # Stil weigeren kostte een keer een hele droom: de gebruiker betaalde,
        # kreeg geen panelen, en nergens stond waarom.
        print("kling: geen sleutel, dus geen panelen voor droom {}".format(number),
              flush=True)
        _write_state(number, {"status": "off", "images": {}, "errors": {}})
        return False
    if not panels:
        print("kling: droom {} heeft geen panelen om te tekenen".format(number), flush=True)
        return False
    threading.Thread(target=_render_all,
                     args=(number, panels, key_index, video_instelling), daemon=True).start()
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
    print("modus   :", mode(), "(bearer = losse sleutel, jwt = access+secret)")
    print("header  :", auth_header()[:40] + "…")
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
                target = download(url, PANELS / "check")
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
