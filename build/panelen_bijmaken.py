"""Ontbrekende panelen bijmaken bij dromen die er geen hebben.

Waarom dit bestaat: er staan dromen in het archief met een duiding en met
ingesproken tekst, maar zonder één paneel - die zijn geschreven toen er geen
Kling-sleutel was, of met "alleen de duiding". De verbeelding is er dus wel, het
beeld niet.

En er is haast: de proefpakketten bij Kling verlopen. Wat er niet op tijd
gebruikt wordt, verdampt.

    python build/panelen_bijmaken.py                 # laat zien wat er zou gebeuren
    python build/panelen_bijmaken.py --echt          # doe het, alle ontbrekende
    python build/panelen_bijmaken.py --echt --droom 8

Maakt uitsluitend panelen. Geen animatie: die kost bij Runway echt geld, en dat
is een andere beslissing dan deze.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import accounts   # noqa: E402
import kling      # noqa: E402


def eenheden():
    """Hoeveel Kling-eenheden staan er nog? Geeft (beeld, video) terug."""
    d = kling._call("GET", "/account/costs?start_time=%d&end_time=%d" % (
        int(time.time() * 1000) - 30 * 24 * 3600 * 1000, int(time.time() * 1000)))
    beeld = video = 0.0
    for p in d["data"]["resource_pack_subscribe_infos"]:
        if "Image" in p["resource_pack_name"]:
            beeld += p["remaining_quantity"]
        elif "Video" in p["resource_pack_name"]:
            video += p["remaining_quantity"]
    return beeld, video


def ontbreekt(uid):
    """Dromen met een bewaarde verbeelding maar minder dan vijf panelen."""
    uit = []
    for r in accounts.db().execute(
            "SELECT n, titel FROM dromen WHERE user_id = ? ORDER BY n", (uid,)):
        n, titel = r[0], r[1]
        ep = accounts.verbeelding(uid, n)
        if not ep or not ep.get("panels"):
            continue
        sleutel = "{}_{}".format(uid, n)
        beelden = [p for p in kling.PANELS.glob(sleutel + "-[0-9].*")
                   if p.suffix.lower() in (".png", ".jpg", ".webp")]
        if len(beelden) < 5:
            uit.append((n, titel, ep, len(beelden)))
    return uit


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--uid", type=int, default=1)
    ap.add_argument("--droom", type=int, help="alleen deze droom")
    ap.add_argument("--echt", action="store_true")
    args = ap.parse_args()

    if not kling.enabled():
        print("Geen Kling-sleutel ingesteld.")
        return 1

    accounts.zet_huidige(accounts.gebruiker(args.uid))
    beeld_voor, video_voor = eenheden()
    print("Kling-eenheden over: %.1f beeld, %.1f video" % (beeld_voor, video_voor))
    print("")

    werk = ontbreekt(args.uid)
    if args.droom:
        werk = [w for w in werk if w[0] == args.droom]
    if not werk:
        print("Niets te doen: elke droom heeft zijn panelen.")
        return 0

    te_maken = sum(5 - w[3] for w in werk)
    for n, titel, ep, hebben in werk:
        print("  droom %-3d %d van 5 aanwezig   %s" % (n, hebben, titel))
    print("")
    print("Te maken: %d panelen." % te_maken)

    if not args.echt:
        print("")
        print("Proefdraai. Geef --echt om het echt te doen.")
        return 0

    for n, titel, ep, _ in werk:
        print("")
        print("--- droom %d: %s ---" % (n, titel))
        # Zonder video_instelling: alleen panelen, geen animatie. De sleutel is
        # de bestandsnaam met het gebruikersnummer erin, net als in de app.
        kling.render_async(dreamverse_sleutel(args.uid, n), ep["panels"])
        # Wachten tot deze droom klaar is voordat de volgende begint: vijf
        # tegelijk is al de gelijktijdigheidsgrens van het proefpakket.
        wacht_op(args.uid, n)

    beeld_na, video_na = eenheden()
    print("")
    print("Verbruikt: %.1f beeldeenheden (%.1f -> %.1f)" % (
        beeld_voor - beeld_na, beeld_voor, beeld_na))
    if te_maken:
        print("Dat is %.1f per paneel." % ((beeld_voor - beeld_na) / te_maken))
    return 0


def dreamverse_sleutel(uid, n):
    import dreamverse
    return dreamverse.sleutel(n) if accounts.huidige()["id"] == uid else "{}_{}".format(uid, n)


def wacht_op(uid, n, minuten=10):
    """Wachten tot de vijf panelen op schijf staan of de tijd om is."""
    sleutel = "{}_{}".format(uid, n)
    grens = time.time() + minuten * 60
    vorige = -1
    while time.time() < grens:
        beelden = [p for p in kling.PANELS.glob(sleutel + "-[0-9].*")
                   if p.suffix.lower() in (".png", ".jpg", ".webp")]
        if len(beelden) != vorige:
            print("   %d van 5" % len(beelden), flush=True)
            vorige = len(beelden)
        if len(beelden) >= 5:
            return True
    print("   niet compleet binnen %d minuten" % minuten)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
