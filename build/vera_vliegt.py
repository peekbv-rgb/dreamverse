"""Twee shots van Vera die vliegt, uit tekst bij Kling.

Alle andere video in dit project komt uit een bestaand beeld: `gids_animaties.py`
laat een gidsbeeld bewegen, `video.py` laat een paneel bewegen. Dit is het eerste
dat uit niets komt - `text2video` in plaats van `image2video`.

    python build/vera_vliegt.py --ja

**Het gezicht is het probleem, en daarom staat ze er niet met haar gezicht op.**
Kling verzint een gezicht, en dat wordt niet het gezicht van de Runway-avatar
(`43e6b2b0…`) die in de app staat. Twee verschillende Vera's is erger dan één.
Dus is ze in beide shots van achteren of ver weg, en staat `face` in de
negative prompt. Haar herkenningstekens - lang donker golvend haar, het gouden
hoofdstuk met muntjes, de donkere mantel - doen dan het werk.

Drie dingen die in beide opdrachten bewust staan:

- **De camera beweegt niet.** Een zwenk of een travelling is waar Kling het
  meest verprutst; in shot twee komt de snelheid uit wolken die de andere kant
  op drijven. Dat leest als vaart zonder dat er iets hoeft te bewegen dat mis
  kan gaan.
- **`wings` staat in de negative prompt.** Bij het woord "vliegen" verzint een
  beeldmodel bijna altijd vleugels erbij, en dan is het een engel.
- **Geen superheldenpose.** Armen los, niet gestrekt. Dit moet een droom blijven
  en geen actiescène.

`kling-v1` en niet `kling-v2-1`: die tweede weigert text2video met "model is not
supported" - nagemeten op 14 september 2026.
"""

import argparse
import sys
import time
import urllib.request
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORTEL))

from dotenv import load_dotenv                                   # noqa: E402
load_dotenv(WORTEL / ".env")

import kling                                                     # noqa: E402

UIT = WORTEL / "data" / "vera-vliegt"

MODEL = "kling-v1"
MODUS = "std"
SECONDEN = 5
VERHOUDING = "9:16"

# `rope, cable, wire, string, kite, parachute, harness` staan erbij sinds de
# eerste poging op "overkomen" een figuurtje aan een lijn opleverde. Een
# beeldmodel dat "trailing in one long line" leest, tekent een lijn.
NEGATIEF = ("face, facial features, portrait, close-up, text, letters, numbers, "
            "watermark, signature, logo, wings, superhero pose, religious "
            "symbol, national flag, extra limbs, distorted hands, rope, cable, "
            "wire, string, kite, parachute, harness, tether, paraglider, "
            "ground, rock, cliff, cliff edge, ledge, standing, walking, footprints")

SHOTS = {
    "opstijgen": (
        "A woman seen from behind, rising slowly through night air above a "
        "wide misty valley. Long dark wavy hair lifting on the wind, a fine "
        "gold headpiece with small hanging coins catching the light, a dark "
        "flowing cloak streaming out behind her. She is small in the frame, "
        "lit from below by a faint amber glow rising off the landscape. Far "
        "beneath her, low cloud drifts over dark hills and a single ribbon of "
        "pale water. Deep indigo sky, scattered stars, faint concentric rings "
        "and soft flowing arcs of light in the background. Her arms are loose "
        "at her sides, she is not straining. The camera holds still while she "
        "rises. Dreamlike illustration, flowing ink and watercolour, soft "
        "luminous glow, painterly. No text, no letters, no logos."
    ),
    # Derde poging, en de twee mislukkingen staan hier omdat ze allebei uit de
    # opdracht zelf kwamen.
    #
    # Eén: er stond "a dark cloak trailing behind her in one long line", en het
    # model tekende een lijn - ze hing aan een kabel. Bij een beeldmodel is een
    # beeldspraak geen beeldspraak.
    #
    # Twee: "gliding across the frame" en "horizontal" werden genegeerd en ze
    # liep over een rotsrand. Dat shot is bewaard als `rand.mp4`, want het is op
    # zichzelf goed - maar het is geen vliegen. Wat ontbrak was de enige regel
    # die het model geen keus laat: **er mag geen grond in beeld zijn.** Zolang
    # er ergens een rand is, zet het er iemand op.
    "overkomen": (
        "A woman flying high in the air, her whole body horizontal and level, "
        "lying flat on the air far above an unbroken sea of cloud. Nothing "
        "beneath her, no ground, no rock, no cliff, no edge anywhere in the "
        "frame - only open sky above and cloud far below. Seen from behind and "
        "slightly above, as if from alongside her, filling about a third of the "
        "frame. Long dark wavy hair streaming back, a dark cloak billowing "
        "around her in loose soft folds, a fine gold headpiece catching the "
        "light. Her arms rest loose at her sides and she is entirely calm, "
        "drifting rather than diving. Warm amber and rose along the horizon, "
        "deep violet above. Thin banks of cloud pass beneath her in the "
        "opposite direction, giving the sense of speed without the camera "
        "moving. Faint concentric rings of light spread outward from where she "
        "passes. Dreamlike illustration, flowing ink and watercolour, soft "
        "luminous glow, painterly. No text, no letters, no logos."
    ),
}


def start(prompt):
    antwoord = kling._call("POST", "/v1/videos/text2video", {
        "model_name": MODEL,
        "prompt": prompt,
        "negative_prompt": NEGATIEF,
        # Laag: hoger laat het model zijn eigen interpretatie doorduwen, en dan
        # verdwijnt de stijl die de rest van het product heeft.
        "cfg_scale": 0.5,
        "mode": MODUS,
        "aspect_ratio": VERHOUDING,
        "duration": str(SECONDEN),
    })
    return (antwoord.get("data") or {}).get("task_id")


def wacht(taak, minuten=12):
    grens = time.time() + minuten * 60
    vorige = None
    while time.time() < grens:
        r = kling._call("GET", "/v1/videos/text2video/" + taak)
        d = r.get("data") or {}
        stand = d.get("task_status")
        if stand != vorige:
            print("      %s" % stand, flush=True)
            vorige = stand
        if stand == "succeed":
            videos = (d.get("task_result") or {}).get("videos") or []
            return videos[0].get("url") if videos else None
        if stand == "failed":
            print("      mislukt:", d.get("task_status_msg"))
            return None
        time.sleep(10)
    print("      nog niet klaar na %d minuten; task_id %s" % (minuten, taak))
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--een", choices=sorted(SHOTS), help="alleen dit shot")
    ap.add_argument("--ja", action="store_true", help="echt versturen")
    ap.add_argument("--opnieuw", action="store_true",
                    help="ook shots die er al staan")
    args = ap.parse_args()

    if not kling.enabled():
        print("Geen Kling-sleutel. Zet KLING_API_KEY in .env.")
        return 1

    namen = [args.een] if args.een else sorted(SHOTS)
    UIT.mkdir(parents=True, exist_ok=True)
    te_doen = [n for n in namen
               if args.opnieuw or not (UIT / (n + ".mp4")).exists()]

    print("%d shots, %s, %s, %d seconden, %s."
          % (len(te_doen), MODEL, MODUS, SECONDEN, VERHOUDING))
    if not args.ja:
        for n in te_doen:
            print("\n  %s\n    %s" % (n, SHOTS[n][:160]))
        print("\nNiets gedaan. Geef --ja mee om ze te maken.")
        return 0

    gelukt = 0
    for i, naam in enumerate(te_doen, 1):
        print("[%d/%d] %s" % (i, len(te_doen), naam), flush=True)
        try:
            taak = start(SHOTS[naam])
            if not taak:
                print("      geen task_id terug")
                continue
            url = wacht(taak)
            if not url:
                continue
            doel = UIT / (naam + ".mp4")
            with urllib.request.urlopen(url, timeout=240) as r:
                doel.write_bytes(r.read())
            print("      %s (%.1f MB)" % (doel.name, doel.stat().st_size / 1e6))
            gelukt += 1
        except kling.KlingError as e:
            print("      %s" % e)

    print("\n%d van de %d gelukt." % (gelukt, len(te_doen)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
