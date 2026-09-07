"""Kling's image-to-video naast die van Runway zetten.

Waarom dit bestaat: het bewegende kernmoment is de duurste schakel van de hele
keten. Runway rekent EUR 0,55 voor vier seconden op veo3.1_fast en EUR 1,47 op
veo3.1, tegen EUR 0,02 voor een paneel bij Kling en EUR 0,04 voor de hele tekst
bij Anthropic. Bij een supreme-droom is die ene animatie dus 91% van de
kostprijs, en dat is precies waar Ultra's marge in verdwijnt.

Kan Kling datzelfde paneel laten bewegen, en ziet het er goed uit, dan verdwijnt
de duurste schakel en een hele leverancier uit de keten.

Dit script neemt een paneel dat Kling al getekend heeft, geeft Kling dezelfde
bewegingsopdracht die Runway kreeg, en zet het resultaat naast de bestaande
Runway-animatie van dezelfde droom.

    python build/kling_vergelijk.py --droom 12 --paneel 2

Zonder --echt doet hij niets: hij drukt alleen af wat hij zou versturen en wat
het aan eenheden kost. Met --echt gaat de aanvraag er daadwerkelijk uit.
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import accounts          # noqa: E402
import kling             # noqa: E402
import video             # noqa: E402

UIT = Path(__file__).resolve().parent.parent / "data" / "vergelijk"


def paneel_bestand(uid, droom, index):
    """Het getekende paneel op schijf. Met en zonder gebruikersnummer zoeken:
    dromen van voor de accounts hebben nog de oude naam."""
    voor = kling.PANELS
    for naam in ("{}_{}-{}".format(uid, droom, index), "{}-{}".format(droom, index)):
        for ext in (".png", ".jpg", ".webp"):
            p = voor / (naam + ext)
            if p.exists():
                return p
    return None


def start(bestand, prompt, model, mode, seconden):
    """Een image-to-video-taak bij Kling starten. Geeft het task_id terug."""
    rauw = base64.b64encode(bestand.read_bytes()).decode()
    body = {
        "model_name": model,
        "mode": mode,               # std of pro
        "duration": str(seconden),  # Kling wil dit als tekst
        "image": rauw,              # base64 zonder data-uri-kop
        "prompt": prompt,
        "cfg_scale": 0.5,
    }
    antwoord = kling._call("POST", "/v1/videos/image2video", body)
    return (antwoord.get("data") or {}).get("task_id")


def wacht(task_id, minuten=8):
    """Wachten tot de taak klaar is. Geeft de url terug, of None."""
    grens = time.time() + minuten * 60
    vorige = None
    while time.time() < grens:
        r = kling._call("GET", "/v1/videos/image2video/" + task_id)
        d = r.get("data") or {}
        stand = d.get("task_status")
        if stand != vorige:
            print("   %s" % stand, flush=True)
            vorige = stand
        if stand == "succeed":
            videos = ((d.get("task_result") or {}).get("videos") or [])
            return videos[0].get("url") if videos else None
        if stand == "failed":
            print("   reden:", d.get("task_status_msg"))
            return None
        time.sleep(10)
    print("   nog niet klaar na %d minuten; task_id %s" % (minuten, task_id))
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--droom", type=int, default=12)
    ap.add_argument("--paneel", type=int, default=2)
    ap.add_argument("--uid", type=int, default=1)
    ap.add_argument("--model", default="kling-v2-1")
    ap.add_argument("--mode", default="pro", choices=("std", "pro"))
    ap.add_argument("--seconden", type=int, default=5, choices=(5, 10))
    ap.add_argument("--echt", action="store_true", help="de aanvraag echt versturen")
    args = ap.parse_args()

    if not kling.enabled():
        print("Geen Kling-sleutel ingesteld.")
        return 1

    accounts.zet_huidige(accounts.gebruiker(args.uid))
    ep = accounts.verbeelding(args.uid, args.droom)
    if not ep or not ep.get("panels"):
        print("Droom %d heeft geen bewaarde panelen." % args.droom)
        return 1
    paneel = ep["panels"][args.paneel]
    bestand = paneel_bestand(args.uid, args.droom, args.paneel)
    if bestand is None:
        print("Het getekende paneel staat niet op schijf.")
        return 1

    prompt = video.beweging_voor(paneel)
    print("droom %d, paneel %d - %s" % (args.droom, args.paneel, ep.get("title")))
    print("bestand : %s (%.1f MB)" % (bestand.name, bestand.stat().st_size / 1e6))
    print("model   : %s, mode %s, %d seconden" % (args.model, args.mode, args.seconden))
    print("prompt  : %s" % prompt)
    print("")

    runway = None
    for naam in ("{}_{}-hero.mp4".format(args.uid, args.droom),
                 "{}-hero.mp4".format(args.droom)):
        p = kling.PANELS / naam
        if p.exists():
            runway = p
            break
    print("Runway's versie van hetzelfde paneel: %s" % (
        "%s (%.1f MB)" % (runway.name, runway.stat().st_size / 1e6) if runway else "niet gevonden"))
    print("")

    if not args.echt:
        print("Proefdraai. Geef --echt om de aanvraag echt te versturen.")
        return 0

    print("Aanvraag versturen...")
    task_id = start(bestand, prompt, args.model, args.mode, args.seconden)
    if not task_id:
        print("Geen task_id terug.")
        return 1
    print("task_id: %s" % task_id)
    url = wacht(task_id)
    if not url:
        return 1

    UIT.mkdir(parents=True, exist_ok=True)
    doel = UIT / "kling-{}-{}-{}-{}.mp4".format(args.droom, args.paneel, args.model, args.mode)
    import urllib.request
    with urllib.request.urlopen(url, timeout=180) as r, open(doel, "wb") as f:
        f.write(r.read())
    print("")
    print("Kling  : %s (%.1f MB)" % (doel, doel.stat().st_size / 1e6))
    if runway:
        print("Runway : %s (%.1f MB)" % (runway, runway.stat().st_size / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
