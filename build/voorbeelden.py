"""De voorbeeldanimaties klaarzetten voor de app.

Wie kiest tussen "Eenvoudig" en "Standaard" kiest tussen vijf tekeningen en vijf
tekeningen plus een bewegend kernmoment - en dat verschil kun je niet uitleggen,
dat moet je laten zien. Vandaar drie echte kernmomenten uit het archief, met de
vuurvogel voorop.

Twee dingen die hier moeten kloppen:

**Ze mogen de pagina niet zwaar maken.** De drie clips zijn samen 8,2 MB en er
is hier geen ffmpeg om ze te verkleinen. Dus krijgt elke clip een posterplaatje
van een paar tientallen kB, en staat de video op `preload="none"`: er wordt niets
gedownload tot iemand op play drukt.

**Ze horen niet in data/.** Dat is git-ignored en verdwijnt bij elke deploy. Deze
horen bij de app, dus ze gaan naar static/voorbeelden/.

    python build/voorbeelden.py
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

WORTEL = Path(__file__).resolve().parent.parent
PANELS = WORTEL / "data" / "panels"
DOEL = WORTEL / "static" / "voorbeelden"

# Welke dromen, en hoe ze heten voor de bezoeker. De titel van de dromer zelf
# gebruiken we niet: dat is zijn droom, niet ons reclamemateriaal.
# De raceauto staat er niet bij, en dat is met opzet: die droom is op de live
# server gemaakt, dus zijn panelen staan op de schijf van Render en niet hier.
# Dit script leest `data/panels/` van deze machine. De clip is met de hand
# opgehaald en het posterbeeldje is uit de video zelf gesneden met imageio.
# Draai je dit script, dan blijft raceauto.mp4 en .jpg gewoon staan - er wordt
# niets weggegooid wat er niet in deze lijst staat.
VOORBEELDEN = [
    {"droom": 6, "bestand": "vuurvogel",
     "nl": "De brandende vogel boven de jacuzzi",
     "en": "The burning bird above the hot tub"},
    {"droom": 7, "bestand": "zee",
     "nl": "De zee die rechtop staat",
     "en": "The sea standing upright"},
    {"droom": 12, "bestand": "quaich",
     "nl": "De beker op het gras",
     "en": "The cup on the grass"},
]

BREEDTE = 720   # genoeg voor een tegel op een groot scherm, klein genoeg om snel te laden


def kernpaneel(n):
    """Welk paneel het kernmoment was. Staat in het standbestand."""
    pad = PANELS / "{}.json".format(n)
    try:
        return json.loads(pad.read_text(encoding="utf-8")).get("video_panel")
    except (OSError, ValueError):
        return None


def main():
    DOEL.mkdir(parents=True, exist_ok=True)
    for v in VOORBEELDEN:
        n = v["droom"]
        clip = PANELS / "1_{}-hero.mp4".format(n)
        if not clip.exists():
            print("droom %d: geen animatie op schijf" % n)
            continue
        shutil.copy2(clip, DOEL / (v["bestand"] + ".mp4"))

        i = kernpaneel(n)
        bron = PANELS / "1_{}-{}.png".format(n, i if i is not None else 2)
        if not bron.exists():
            print("droom %d: geen kernpaneel gevonden (%s)" % (n, bron.name))
            continue
        im = Image.open(bron).convert("RGB")
        h = round(im.height * BREEDTE / im.width)
        im.resize((BREEDTE, h), Image.LANCZOS).save(
            DOEL / (v["bestand"] + ".jpg"), "JPEG", quality=82, optimize=True)

        mp4 = (DOEL / (v["bestand"] + ".mp4")).stat().st_size / 1e6
        jpg = (DOEL / (v["bestand"] + ".jpg")).stat().st_size / 1000
        print("%-10s  clip %.1f MB   poster %.0f kB   (%s)" % (
            v["bestand"], mp4, jpg, v["nl"]))

    totaal = sum(p.stat().st_size for p in DOEL.glob("*.mp4")) / 1e6
    poster = sum(p.stat().st_size for p in DOEL.glob("*.jpg")) / 1000
    print("")
    print("Samen: %.1f MB aan clips, %.0f kB aan posters." % (totaal, poster))
    print("De pagina laadt alleen de posters; een clip pas als iemand klikt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
