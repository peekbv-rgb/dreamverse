"""Bewegende scènes voor gidsonderwerpen die van zichzelf stilstaan.

`gids_animaties.py` laat het gidsbeeld bewegen. Dat werkt goed zolang er iets
in dat beeld zit dat kán bewegen - water, rook, vuur, een dier. Bij twaalf van
de drieënveertig zit dat er niet in: een lege zaal, een bank, een bureau, een
perron. Daar komt hoe dan ook een tekening uit.

**Dat is gemeten en niet aangenomen, op 17 september.** Zie *Hoeveel er beweegt
is een getal* in CLAUDE.md. Op `ex` (een lege kamer met twee stoelen):

    oud model, 5 s, timide opdracht      0,49
    kling-v3 pro, 10 s, sterke opdracht  1,44
    datzelfde met cfg_scale 0,85         1,67

De sprong van 0,5 naar 0,85 is bijna een verdubbeling van de vrijheid die het
model krijgt, en levert +0,23 op. **Het model is de grens niet en de instelling
ook niet - het bronbeeld is de grens.** Bij een lege kamer is er niets om te
bewegen, en dan helpt een duurder model daar niets aan.

Dus komt de scène hier **uit tekst** in plaats van uit het beeld, en wordt de
beweging in het onderwerp zelf gezet: een deur die in de tocht slaat, een trein
die doorrijdt zonder te stoppen, papieren die van de tafels waaien, regen op het
glas.

    python build/gids_scenes.py --ja           # alle twaalf
    python build/gids_scenes.py --ja ex train   # een paar

**Wat dit kost, en dat is het echte besluit.** Het beeld in de Reel is niet
langer het beeld op de gidspagina. Tot nu toe was dat één wereld - dezelfde hand
als de panelen, dezelfde stijl, en wie van een Reel naar de pagina ging zag
hetzelfde terug. Ruud heeft die prijs op 17 september bewust betaald, omdat een
Reel die niet beweegt op TikTok niets doet. De gidspagina's blijven ongemoeid:
dit raakt alleen wat er in de Reels beweegt.

De oude versies staan als `<slug>-stil.mp4` in dezelfde map, dus terugdraaien is
een hernoeming.

Drie regels die hetzelfde blijven als bij de gidsbeelden, en waarom:

- **Geen gezichten.** Deze beelden gaan mee als voorvertoning en staan op een
  openbaar kanaal. Een herkenbaar gezicht bij *dromen over je ex* suggereert een
  persoon, en dat is precies wat een droom niet is.
- **De camera beweegt niet.** Een zwenk of een travelling is waar het model het
  meest verprutst; de beweging komt uit de wereld.
- **Niet letterlijk en niet eng.** Wie 's ochtends zoekt op een nachtmerrie is
  er meestal van geschrokken.
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

UIT = WORTEL / "data" / "gids-animatie-staand"

# Dezelfde hoogste categorie als in gids_animaties.py; die twee horen gelijk op
# te lopen. 17 eenheden per clip bij pro en tien seconden - nagemeten, want de
# schatting in het script stond nog op de 3,5 van het opgeheven model.
MODEL = "kling-v3"
MODUS = "pro"
SECONDEN = 10
VERHOUDING = "9:16"

STIJL = ("Dreamlike illustration, flowing ink and watercolour, soft luminous "
         "glow, painterly, deep violet shadows with warm amber light. Faint "
         "concentric rings and soft arcs of light. The camera does not move. "
         "No text, no letters, no logos.")

NEGATIEF = ("face, facial features, portrait, close-up, recognisable person, "
            "text, letters, numbers, watermark, signature, artist signature, "
            "initials, logo, religious symbol, national flag, extra limbs, "
            "distorted hands, gore, blood, horror, jump scare, camera pan, "
            "camera zoom, dolly shot")

# Twaalf scènes met Vera erin, en dat is de oplossing van het probleem in plaats
# van een omweg eromheen: een lege zaal kán niet bewegen, een mens die iets doet
# altijd. Het idee is van Ruud, op 17 september - hij vroeg waarom Vera nergens
# in de gids voorkomt terwijl het Vera's Dream Guide heet.
#
# Twee dingen die dat en passant oplevert. Elke Reel beweegt, want zij beweegt.
# En de gids krijgt één terugkerende figuur: wie drie Reels ziet, ziet drie keer
# dezelfde vrouw met hetzelfde gouden kapje, en dat is precies wat een account
# herkenbaar maakt.
#
# **Dezelfde regel als in vera_vliegt.py: nooit haar gezicht.** Kling verzint een
# gezicht en dat wordt niet dat van de Runway-avatar in de app. Ze is dus altijd
# van achteren of ver weg, en `face` staat in de negatieve prompt. Haar
# herkenningstekens - lang donker golvend haar, het gouden hoofdstuk met
# muntjes, de donkere mantel - doen het werk.
#
# En geen beeldspraak over die mantel. "Trailing behind her in one long line"
# leverde ooit een vrouw aan een kabel op; er staat hier dus wat er letterlijk
# te zien moet zijn.
VERA = ("A woman seen from behind, never her face: long dark wavy hair down her "
        "back, a fine gold headpiece with small hanging coins, a dark cloak "
        "that moves in loose soft folds. ")

SCENES = {
    "being-naked": VERA + (
        "She walks slowly down the aisle of a large bright hall, away from the "
        "camera, between long rows of empty seats, towards a single empty chair "
        "in the middle. Tall windows stand open; curtains billow inward and "
        "broad shafts of light sweep across the floor as she passes."
    ),
    "father": VERA + (
        "She stands at a workbench in an empty workshop at first light, seen "
        "from behind, slowly picking up a worn tool and turning it over in her "
        "hands. Sawdust drifts thickly through the beam from the window, a "
        "jacket on the chair beside her stirs, a lamp on a cord turns overhead."
    ),
    "train": VERA + (
        "She stands alone at the edge of an empty railway platform at dusk, "
        "seen from behind, as a train rushes straight through without stopping. "
        "Carriage after carriage streaks past in a blur of warm light; her hair "
        "and cloak are pulled hard sideways by the wind it makes, and the mist "
        "is dragged along behind it."
    ),
    "being-late": VERA + (
        "She stands on an empty station platform at dusk, seen from behind, "
        "watching the last carriage of a train move steadily further away down "
        "the track. Above her a large station clock turns visibly. Loose papers "
        "blow past her along the platform and her cloak lifts in the draught."
    ),
    "exam": VERA + (
        "She walks slowly between long rows of empty desks in a large hall, "
        "away from the camera. Wind pours through the high open windows, "
        "lifting blank sheets of paper off the desks so they turn and drift "
        "through the air all around her while the curtains billow."
    ),
    "getting-lost": VERA + (
        "Seen from high above and very small, she walks through a maze of "
        "narrow streets at night and turns a corner, then another. Rain falls "
        "steadily and shines on the cobbles, warm windows light up and go dark "
        "in slow waves across the rooftops, mist rolls through the alleys."
    ),
    "mother": VERA + (
        "She sits at a kitchen table at early morning, seen from behind, and "
        "slowly lifts a warm cup with both hands. Steam pours and curls upward "
        "in thick ribbons, a curtain at the window lifts and falls, and low "
        "golden light moves across the table as clouds pass outside."
    ),
    "ex": VERA + (
        "She stands still in an open doorway at dusk, seen from behind, looking "
        "into a room with two empty chairs facing each other. A draught swings "
        "the door slowly wider and then part way back; light sweeps across the "
        "floor as it moves, dust swirls thickly through the beam, her cloak "
        "stirs."
    ),
    "falling": VERA + (
        "She falls slowly through soft layered clouds lit from below by golden "
        "light, seen from far above and small, arms open, more like floating "
        "than dropping, turning very slowly as she goes. The clouds rush upward "
        "past her continuously and tear apart and reform."
    ),
    "flying": VERA + (
        "She glides through open air far above a sleeping landscape at dawn, "
        "with nothing beneath her - no ground, no rock, no ridge, no edge "
        "anywhere in the frame, only sky and cloud. Seen from behind "
        "and very small against the sky, arms loose at her sides. Layered "
        "clouds stream steadily past beneath her catching the first light, the "
        "horizon glows and shifts, thin mist tears apart and reforms."
    ),
    "cat": VERA + (
        "She sits on the floor by a window at night, seen from behind, with a "
        "cat on the sill beside her looking out at a dark garden. Rain runs "
        "steadily down the glass; the cat's tail flicks and its head turns to "
        "follow something outside, and the branches sway in the wind beyond."
    ),
    "stairs": VERA + (
        "She climbs a wide stone staircase that curves upward into soft light, "
        "seen from behind and below, moving steadily away from the camera, the "
        "top out of sight. Light from above pulses and pours down the steps, "
        "dust swirls thickly in the shaft, shadows sweep across the treads."
    ),
}


# Twee scènes gaan over zweven, en daar geldt de regel uit `vera_vliegt.py`:
# **er mag geen grond in beeld zijn.** Zonder die regel zet het model haar op de
# eerste rand die het kan bedenken - bij `flying` gebeurde dat op 17 september
# precies zo, ze stond op een richel boven de wolken. Bij de tien andere scènes
# mag dit er juist niet in: een trap, een perron en een keukenvloer zijn grond.
GEEN_GROND = (", ground, land, rock, cliff, cliff edge, ledge, hill, ridge, "
              "mountain top, standing on something, walking on something, "
              "footprints, rope, cable, wire, harness, wings")

ZWEVEND = ("falling", "flying")


def start(prompt, extra=""):
    antwoord = kling._call("POST", "/v1/videos/text2video", {
        "model_name": MODEL,
        "prompt": prompt + " " + STIJL,
        "negative_prompt": NEGATIEF + extra,
        # Hoger dan de 0,5 van image2video: daar moest een bestaand beeld
        # herkenbaar blijven, hier is er geen beeld om te bewaren en mag het
        # model de scène zelf opbouwen.
        "cfg_scale": 0.7,
        "mode": MODUS,
        "aspect_ratio": VERHOUDING,
        "duration": str(SECONDEN),
    })
    return (antwoord.get("data") or {}).get("task_id")


def wacht(taak, minuten=15):
    grens = time.time() + minuten * 60
    vorige = None
    while time.time() < grens:
        d = (kling._call("GET", "/v1/videos/text2video/" + taak).get("data") or {})
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
    ap.add_argument("slugs", nargs="*", help="welke onderwerpen")
    ap.add_argument("--ja", action="store_true", help="echt versturen")
    ap.add_argument("--opnieuw", action="store_true",
                    help="ook wat er al staat")
    args = ap.parse_args()

    if not kling.enabled():
        print("Geen Kling-sleutel in .env.")
        return 1

    namen = args.slugs or sorted(SCENES)
    zonder = [n for n in namen if n not in SCENES]
    if zonder:
        print("Geen scène voor: %s" % ", ".join(zonder))
        return 1

    # Hervatbaar, net als gids_animaties.py: wat er al ligt wordt overgeslagen,
    # dus een afgebroken ronde kost geen tegoed. Dat telt hier dubbel, want een
    # clip is 17 eenheden.
    te_doen = [n for n in namen
               if args.opnieuw or not (UIT / (n + ".mp4")).exists()]

    print("%d scènes, %s, %s, %d seconden, %s.  Ongeveer %d eenheden."
          % (len(te_doen), MODEL, MODUS, SECONDEN, VERHOUDING, 17 * len(te_doen)))
    if not args.ja:
        for n in te_doen:
            print("\n  %s\n    %s" % (n, SCENES[n][:150]))
        print("\nNiets gedaan. Geef --ja mee.")
        return 0

    UIT.mkdir(parents=True, exist_ok=True)
    gelukt = 0
    for i, naam in enumerate(te_doen, 1):
        print("[%d/%d] %s" % (i, len(te_doen), naam), flush=True)
        try:
            taak = start(SCENES[naam],
                         GEEN_GROND if naam in ZWEVEND else "")
            if not taak:
                print("      geen task_id terug")
                continue
            url = wacht(taak)
            if not url:
                continue
            doel = UIT / (naam + ".mp4")
            with urllib.request.urlopen(url, timeout=300) as r:
                doel.write_bytes(r.read())
            print("      %s (%.1f MB)" % (doel.name, doel.stat().st_size / 1e6))
            gelukt += 1
        except kling.KlingError as e:
            print("      %s" % e)

    print("\n%d van de %d gelukt, ongeveer %d eenheden."
          % (gelukt, len(te_doen), 17 * gelukt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
