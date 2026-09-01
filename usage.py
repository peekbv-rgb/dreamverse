"""Wat een gebruiker werkelijk kost — meten, niet schatten.

Elke dure handeling schrijft hier één regel weg: een aflevering, een getekend
paneel, een gesprek met Vera. Geen betaling, geen limieten, alleen tellen. Pas
als hier twee weken echte cijfers in staan, is er iets zinnigs te zeggen over
€4,99 per maand of over wat een token waard is.

    data/usage.jsonl    append-only, één JSON-object per regel

Bewust append-only: een verbruiksadministratie die je kunt overschrijven is geen
administratie. Het bestand is klein (een paar honderd bytes per droom) en blijft
leesbaar met het blote oog.

Tarieven staan onderin en zijn te overschrijven via .env. Runway's avatartarief
zit er precies in zoals zij het rekenen: 2 credits bij het starten en 2 credits
per aangebroken zes seconden, met een credit van $0,01. Dat is een traptarief,
geen prijs per seconde, en het verschil is groot bij korte gesprekken.
"""

import json
import os
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
LOG = DATA / "usage.jsonl"

_lock = threading.Lock()

# Tarieven in euro. Overschrijven kan via .env.
def _rate(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return default


def rates():
    return {
        # Anthropic, per miljoen tokens, omgerekend van dollar naar euro.
        "eur_per_m_input": _rate("PRIJS_INPUT_PER_M", 4.60),
        "eur_per_m_output": _rate("PRIJS_OUTPUT_PER_M", 23.00),
        # Kling rekent in credits; wat een paneel kost hangt van je pakket af.
        # Vul in wat je bij de eerste factuur ziet.
        "eur_per_panel": _rate("PRIJS_PER_PANEEL", 0.02),
        # Runway rekent in credits van $0,01. Voor gwm1_avatars: 2 credits bij
        # het starten, daarna 2 credits per aangebroken zes seconden. Dat is een
        # traptarief, geen prijs per seconde, dus we rekenen het precies uit.
        "usd_per_credit": _rate("PRIJS_PER_CREDIT", 0.01),
        "eur_per_usd": _rate("EURO_PER_DOLLAR", 0.92),
    }


def avatar_credits(seconds):
    """Runway's traptarief voor een avatargesprek, in credits.

    Twee vooraf, plus twee per aangebroken zes seconden. Iemand die opstart en
    meteen ophangt kost dus al credits — dat is precies waarom een gratis laag
    met onbeperkt bellen niet kan.
    """
    import math
    if seconds <= 0:
        return 2
    return 2 + 2 * math.ceil(seconds / 6)


def avatar_euro(seconds, r=None):
    r = r or rates()
    return avatar_credits(seconds) * r["usd_per_credit"] * r["eur_per_usd"]


def _append(record):
    DATA.mkdir(exist_ok=True)
    record["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _lock:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _who():
    # Nu één gebruiker. Het veld staat er alvast in, zodat de cijfers straks
    # niet opnieuw verzameld hoeven te worden als er accounts komen.
    try:
        import dreamverse
        return dreamverse.load_profile().get("name") or "onbekend"
    except Exception:
        return "onbekend"


def episode(number, input_tokens=0, output_tokens=0, demo=False):
    return _append({
        "kind": "episode", "who": _who(), "dream": number, "demo": bool(demo),
        "input_tokens": int(input_tokens or 0), "output_tokens": int(output_tokens or 0),
    })


def panel(number, index, ok=True):
    return _append({"kind": "panel", "who": _who(), "dream": number,
                    "index": index, "ok": bool(ok)})


def hero_video(number, index, instelling):
    return _append({"kind": "hero_video", "who": _who(), "dream": number, "index": index,
                    "model": instelling.get("model"), "seconds": instelling.get("seconden"),
                    "eur": instelling.get("kost")})


_sessions = {}


def session_started(session_id):
    _sessions[session_id] = time.monotonic()
    return _append({"kind": "session_start", "who": _who(), "session": session_id})


def session_ended(session_id, cap):
    started = _sessions.pop(session_id, None)
    if started is None:
        # Geen starttijd bekend: reken het volle gesprek, want dat is de
        # veilige aanname als iemand het tabblad dichtgooit.
        seconds = cap
        gemeten = False
    else:
        seconds = min(cap, max(0, round(time.monotonic() - started)))
        gemeten = True
    return _append({"kind": "session_end", "who": _who(), "session": session_id,
                    "seconds": seconds, "measured": gemeten})


def read():
    try:
        with LOG.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except (FileNotFoundError, OSError):
        return []
    except json.JSONDecodeError:
        # Eén kapotte regel mag het overzicht niet slopen.
        out = []
        with LOG.open(encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out


def summary():
    r = rates()
    records = read()
    dagen = {}
    totaal = {"dreams": 0, "panels": 0, "panels_failed": 0, "sessions": 0,
              "avatar_seconds": 0, "input_tokens": 0, "output_tokens": 0, "videos": 0}

    for rec in records:
        dag = (rec.get("at") or "")[:10] or str(date.today())
        d = dagen.setdefault(dag, {"dreams": 0, "panels": 0, "sessions": 0, "avatar_seconds": 0})
        kind = rec.get("kind")
        if kind == "episode":
            totaal["dreams"] += 1; d["dreams"] += 1
            totaal["input_tokens"] += rec.get("input_tokens", 0)
            totaal["output_tokens"] += rec.get("output_tokens", 0)
        elif kind == "panel":
            if rec.get("ok"):
                totaal["panels"] += 1; d["panels"] += 1
            else:
                totaal["panels_failed"] += 1
        elif kind == "hero_video":
            totaal["videos"] += 1
        elif kind == "session_start":
            totaal["sessions"] += 1; d["sessions"] += 1
        elif kind == "session_end":
            totaal["avatar_seconds"] += rec.get("seconds", 0)
            d["avatar_seconds"] += rec.get("seconds", 0)

    # Per gesprek apart uitrekenen: het opstarttarief geldt per sessie, dus de
    # som van alle seconden zou het onderschatten.
    avatar = sum(avatar_euro(rec.get("seconds", 0), r)
                 for rec in records if rec.get("kind") == "session_end")

    kosten = {
        "tekst": round(totaal["input_tokens"] / 1e6 * r["eur_per_m_input"]
                       + totaal["output_tokens"] / 1e6 * r["eur_per_m_output"], 4),
        "panelen": round(totaal["panels"] * r["eur_per_panel"], 4),
        "video": round(sum(rec.get("eur") or 0 for rec in records
                           if rec.get("kind") == "hero_video"), 4),
        "avatar": round(avatar, 4),
    }
    kosten["totaal"] = round(sum(kosten.values()), 4)

    per_droom = round(kosten["totaal"] / totaal["dreams"], 4) if totaal["dreams"] else None

    return {
        "totals": totaal,
        "by_day": [dict(date=k, **v) for k, v in sorted(dagen.items(), reverse=True)],
        "rates": r,
        "costs": kosten,
        "cost_per_dream": per_droom,
        "avatar_rate_known": True,
        # Wat een gesprek van vijf minuten kost, het cijfer waar je model op staat of valt.
        "avatar_per_5min": round(avatar_euro(300, r), 4),
        "avatar_per_minute": round(avatar_euro(60, r) - avatar_euro(0, r), 4),
    }
