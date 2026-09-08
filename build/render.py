"""De omgeving op Render lezen en bijwerken, vanaf deze machine.

Waarom dit er is: de prijs-id's van Stripe, `PUBLIEKE_URL`, een webhookgeheim -
dat zijn regels die hier worden bedacht en daar moeten staan. Zolang dat met de
hand ging, was er altijd een moment waarop de code al klopte en de omgeving nog
niet. Dat is precies het soort verschil waar je een halve dag naar zoekt.

**Dit raakt de productieomgeving.** Vandaar drie remmen die er bewust in zitten:

- Alleen `PUT /env-vars/<sleutel>` wordt gebruikt, nooit de variant die de hele
  set vervangt. Die laatste wist alles wat je niet meestuurt, en dan staat de app
  zonder API-sleutel stil.
- Zetten vraagt om bevestiging, tenzij je `--ja` meegeeft. Er wordt eerst
  getoond wat er verandert.
- Waarden worden nooit voluit afgedrukt. Een sleutel die in de terminal staat,
  staat in de scrollback en soms in de shellgeschiedenis.

Render start de service opnieuw op zodra een variabele verandert - reken op een
paar minuten waarin de app 502 geeft.

    python build/render.py --check                 # sleutel goed? welke service?
    python build/render.py --env                   # wat staat er nu
    python build/render.py --zet SLEUTEL=waarde    # er een bijwerken
    python build/render.py --uit-env STRIPE_PRICE_TOKENS20 ...   # uit .env overnemen
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
API = "https://api.render.com/v1"


def laden():
    from dotenv import load_dotenv
    load_dotenv(WORTEL / ".env")


def sleutel():
    return os.environ.get("RENDER_API_KEY", "").strip()


def dienst_id():
    return os.environ.get("RENDER_SERVICE_ID", "").strip()


def verhuld(waarde):
    """Genoeg om te herkennen, te weinig om te misbruiken."""
    w = str(waarde or "")
    if not w:
        return "(leeg)"
    if len(w) <= 8:
        return w[0] + "*" * (len(w) - 1)
    return "{}...{}  ({} tekens)".format(w[:6], w[-4:], len(w))


def roep(pad, methode="GET", lichaam=None):
    k = sleutel()
    if not k:
        raise SystemExit("Geen RENDER_API_KEY in .env. Zie de uitleg in .env.example.")
    data = json.dumps(lichaam).encode() if lichaam is not None else None
    verzoek = urllib.request.Request(API + pad, data=data, method=methode)
    verzoek.add_header("Authorization", "Bearer " + k)
    verzoek.add_header("Accept", "application/json")
    if data:
        verzoek.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(verzoek, timeout=30) as r:
            rauw = r.read().decode()
            return json.loads(rauw) if rauw.strip() else {}
    except urllib.error.HTTPError as e:
        tekst = e.read().decode()[:300]
        if e.code == 401:
            raise SystemExit("Render weigert de sleutel (401). Is hij verlopen "
                             "of van een ander account?")
        raise SystemExit("Render gaf {}: {}".format(e.code, tekst))
    except urllib.error.URLError as e:
        raise SystemExit("Render niet bereikbaar: {}".format(e.reason))


def diensten():
    """De lijst komt terug als [{"service": {...}}, ...]."""
    uit = roep("/services?limit=100")
    return [r.get("service", r) for r in uit] if isinstance(uit, list) else []


def kies_dienst():
    """Het id uit .env, of - staat er maar een - die ene."""
    d = dienst_id()
    if d:
        return d
    lijst = [s for s in diensten() if s.get("type") == "web_service"]
    if len(lijst) == 1:
        return lijst[0]["id"]
    raise SystemExit("Zet RENDER_SERVICE_ID in .env; er zijn er {}.".format(len(lijst)))


def variabelen(sid):
    uit = roep("/services/{}/env-vars?limit=100".format(sid))
    paren = {}
    for r in uit if isinstance(uit, list) else []:
        v = r.get("envVar", r)
        paren[v.get("key", "")] = v.get("value", "")
    return paren


def check():
    if not sleutel():
        print("RENDER_API_KEY staat niet in .env.")
        print("")
        print("Maken kan alleen jij: Render -> Account Settings -> API Keys ->")
        print("Create API Key. Plak hem daarna in .env achter RENDER_API_KEY=.")
        print(".env is git-ignored, dus hij komt nergens terecht.")
        return 1
    print("Sleutel: %s" % verhuld(sleutel()))
    lijst = diensten()
    print("Diensten op dit account: %d" % len(lijst))
    for s in lijst:
        merk = " <- RENDER_SERVICE_ID" if s.get("id") == dienst_id() else ""
        print("  %-22s %-14s %s%s" % (s.get("name"), s.get("type"), s.get("id"), merk))
    if not dienst_id():
        print("")
        print("RENDER_SERVICE_ID staat niet in .env; met een enkele webdienst")
        print("wordt die vanzelf gekozen.")
    return 0


def toon():
    sid = kies_dienst()
    paren = variabelen(sid)
    print("Omgeving van %s - %d variabelen" % (sid, len(paren)))
    print("")
    for k in sorted(paren):
        print("  %-28s %s" % (k, verhuld(paren[k])))
    return 0


def zet(paren, bevestigd):
    """Per sleutel bijwerken. Nooit de hele set vervangen."""
    sid = kies_dienst()
    huidig = variabelen(sid)

    werk = []
    for k, v in paren.items():
        oud = huidig.get(k)
        if oud == v:
            print("  %-28s ongewijzigd" % k)
            continue
        werk.append((k, oud, v))

    if not werk:
        print("")
        print("Niets te doen; alles stond er al zo in.")
        return 0

    print("")
    print("Dit verandert er op %s:" % sid)
    for k, oud, nieuw in werk:
        print("  %-28s %s" % (k, verhuld(oud) if oud is not None else "(nieuw)"))
        print("  %-28s -> %s" % ("", verhuld(nieuw)))
    print("")
    print("Render start de service hierna opnieuw op; reken op een paar minuten 502.")

    if not bevestigd:
        print("")
        print("Niets gedaan. Geef --ja mee om het echt te doen.")
        return 0

    for k, _, nieuw in werk:
        roep("/services/{}/env-vars/{}".format(sid, k), "PUT", {"value": nieuw})
        print("  gezet: %s" % k)
    return 0


def main(argv):
    laden()
    if "--check" in argv:
        return check()
    if "--env" in argv:
        return toon()

    bevestigd = "--ja" in argv
    paren = {}

    for a in argv:
        if a.startswith("--zet="):
            k, _, v = a[6:].partition("=")
            paren[k.strip()] = v
    if "--zet" in argv:
        i = argv.index("--zet")
        for a in argv[i + 1:]:
            if a.startswith("--"):
                break
            k, _, v = a.partition("=")
            paren[k.strip()] = v

    if "--uit-env" in argv:
        i = argv.index("--uit-env")
        for naam in argv[i + 1:]:
            if naam.startswith("--"):
                break
            waarde = os.environ.get(naam)
            if waarde is None:
                print("  %-28s staat niet in .env - overgeslagen" % naam)
                continue
            paren[naam] = waarde

    if paren:
        return zet(paren, bevestigd)

    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
