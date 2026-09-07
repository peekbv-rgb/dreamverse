"""Kan Runway een hele set van vijf panelen in één stijl maken?

Op 1 september is `muse_image` afgewezen: het ene paneel kwam op wit papier, het
volgende in een nachtblauwe wereld. Maar dat model kreeg toen geen
referentiebeeld mee, en `gen4_image_turbo` werd afgeschreven omdat het er juist
een eist. Dat "eist" is hier geen bezwaar maar precies het mechanisme: paneel 1
maken, en dat beeld als stijlreferentie meegeven aan paneel 2 tot 5.

Waarom het uitmaakt: Kling's proefpakket verloopt, en het kleinste betaalde
pakket is $350 voor 100.000 eenheden - beeld voor 5.000 dromen, binnen 180 dagen
op te maken. Houdt Runway de stijl vast, dan is er één leverancier, geen
minimumafname en geen klok. Runway-credits verlopen niet.

    python build/runway_panelen.py --droom 12          # laat zien wat hij zou doen
    python build/runway_panelen.py --droom 12 --echt

Zet de vijf beelden in data/vergelijk/runway-<droom>-<n>.png, naast Kling's set
van dezelfde droom, en meet het creditverbruik voor en na.
"""

import argparse
import base64
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import accounts   # noqa: E402
import kling      # noqa: E402

UIT = Path(__file__).resolve().parent.parent / "data" / "vergelijk"
RATIO = "1920:1080"   # 16:9, dezelfde verhouding als Kling levert


def klant():
    from runwayml import RunwayML
    return RunwayML()


def credits(c):
    o = c.organization.retrieve()
    d = o.model_dump() if hasattr(o, "model_dump") else dict(o)
    return d.get("credit_balance")


def wacht(c, taak_id, minuten=6):
    grens = time.time() + minuten * 60
    vorige = None
    while time.time() < grens:
        t = c.tasks.retrieve(taak_id)
        stand = getattr(t, "status", None)
        if stand != vorige:
            print("     %s" % stand, flush=True)
            vorige = stand
        if stand == "SUCCEEDED":
            uit = getattr(t, "output", None) or []
            return uit[0] if uit else None
        if stand in ("FAILED", "CANCELLED"):
            print("     reden:", getattr(t, "failure", None) or getattr(t, "failure_code", None))
            return None
        time.sleep(5)
    print("     niet klaar binnen %d minuten" % minuten)
    return None


def haal(url, doel):
    import urllib.request
    with urllib.request.urlopen(url, timeout=180) as r, open(doel, "wb") as f:
        f.write(r.read())
    return doel


def data_uri(pad):
    soort = "image/png" if pad.suffix.lower() == ".png" else "image/jpeg"
    return "data:%s;base64,%s" % (soort, base64.b64encode(pad.read_bytes()).decode())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--droom", type=int, default=12)
    ap.add_argument("--uid", type=int, default=1)
    ap.add_argument("--model", default="gen4_image")
    ap.add_argument("--echt", action="store_true")
    args = ap.parse_args()

    accounts.zet_huidige(accounts.gebruiker(args.uid))
    ep = accounts.verbeelding(args.uid, args.droom)
    if not ep or not ep.get("panels"):
        print("Droom %d heeft geen bewaarde panelen." % args.droom)
        return 1
    panelen = ep["panels"][:5]

    print("droom %d: %s" % (args.droom, ep.get("title")))
    print("model : %s, verhouding %s" % (args.model, RATIO))
    print("")
    for i, p in enumerate(panelen):
        print("  %d. %s" % (i + 1, kling.panel_prompt(p)[:110]))
    print("")
    print("Paneel 1 wordt gewoon geschreven; 2 tot 5 krijgen paneel 1 mee als")
    print("stijlreferentie onder de naam @stijl.")

    if not args.echt:
        print("")
        print("Proefdraai. Geef --echt om het echt te doen.")
        return 0

    c = klant()
    voor = credits(c)
    print("")
    print("Credits voor: %s" % voor)
    UIT.mkdir(parents=True, exist_ok=True)

    eerste = None
    for i, p in enumerate(panelen):
        print("")
        print("--- paneel %d ---" % (i + 1))
        prompt = kling.panel_prompt(p)
        body = {"model": args.model, "prompt_text": prompt, "ratio": RATIO}
        if eerste is not None:
            # De verwijzing moet in de tekst staan, anders doet Runway er niets mee.
            body["prompt_text"] = prompt + " Same visual style, palette and technique as @stijl."
            body["reference_images"] = [{"uri": data_uri(eerste), "tag": "stijl"}]
        taak = c.text_to_image.create(**body)
        url = wacht(c, taak.id)
        if not url:
            print("     mislukt; hier stopt de proef")
            break
        doel = UIT / ("runway-%d-%d.png" % (args.droom, i))
        haal(url, doel)
        print("     %s  %.1f MB" % (doel.name, doel.stat().st_size / 1e6))
        if eerste is None:
            eerste = doel

    na = credits(c)
    print("")
    print("Credits na: %s   verbruikt: %s" % (na, (voor - na) if voor and na else "?"))
    if voor and na:
        print("Per paneel: %.1f credits, ofwel EUR %.3f" % (
            (voor - na) / 5.0, (voor - na) / 5.0 * 0.01 * 0.92))
    print("")
    print("Kling's set van dezelfde droom staat in data/panels als %s_%d-*.png"
          % (args.uid, args.droom))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
