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

**Het model verandert onder je handen, en dat is hier twee keer gebeurd.** Op
14 september was `kling-v1` de enige die text2video deed en weigerde
`kling-v2-1` met "model is not supported". Op 17 september geeft `kling-v1`
zelf `1203 discontinued`, net als `kling-v1-5`, `kling-v1-6`, `kling-v2-master`
en `kling-v2-1-master`. Wat er dan nog overblijft is **`kling-v2-5-turbo`**.

Zoeken kost niets: een verzoek met een onbekend model wordt geweigerd voordat
er iets gerenderd wordt, dus een lijstje kandidaten langslopen is gratis. Dat
is de manier om dit op te lossen als het over een maand weer verschoven is -
niet de documentatie lezen maar het eindpunt het zelf laten zeggen.
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

# `kling-v3` in `pro`, gelijk met gids_scenes.py en gids_animaties.py.
# Die drie horen gelijk op te lopen; zie CLAUDE.md over modellen die
# onder je handen verdwijnen.
MODEL = "kling-v3"
MODUS = "pro"
# Tien en niet vijf, sinds 17 september. `kling-v2-5-turbo` accepteert allebei,
# en een Reel voor TikTok wil 12 tot 18 seconden - dat komt uit monteren, en dan
# is tien seconden per shot twee keer zoveel om uit te kiezen. De drie
# vliegshots blijven op vijf staan zoals ze zijn; die zijn af.
SECONDEN = 10
VERHOUDING = "9:16"

# De negatieve prompt staat per shot, en dat moest.
#
# Eerst was het één lijst voor alles, en die was gebouwd om *vliegen* af te
# dwingen: `ground, walking, footprints` erin om te voorkomen dat het model haar
# ergens op neerzet, en `rope, cable, wire, string` omdat een eerdere opdracht
# een figuurtje aan een kabel opleverde.
#
# Zodra er shots bijkomen die niet over vliegen gaan, werkt diezelfde lijst
# tegen je: een paard op het strand *heeft* grond nodig en loopt, en een
# zeilboot *heeft* touwen. Eén lijst die voor het ene shot de oplossing is, is
# voor het andere de fout - en het is het soort fout dat je pas ziet als het
# beeld terugkomt en er iets ontbreekt dat je nooit hebt weggevraagd.
#
# Dus: `BASIS` geldt altijd, en elk shot zegt er zelf bij wat het verder niet
# wil. Wat in `BASIS` staat is wat voor Vera als personage geldt en niet voor
# een scène.
BASIS = ("face, facial features, portrait, close-up, text, letters, numbers, "
         "watermark, signature, logo, wings, superhero pose, religious symbol, "
         "national flag, extra limbs, distorted hands")

# Wat de drie vliegshots nodig hadden. Zie de les hieronder bij `overkomen`.
GEEN_GROND = (", rope, cable, wire, string, kite, parachute, harness, tether, "
              "paraglider, ground, rock, cliff, cliff edge, ledge, standing, "
              "walking, footprints")

SHOTS = {
    "opstijgen": {"negatief": BASIS + GEEN_GROND, "prompt": (
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
    )},
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
    # Het slotbeeld, en het idee komt uit Ruuds eigen montage: een lange boog
    # door de lucht. Sterk, want het toont de reis in plaats van de reiziger.
    #
    # Wel de val van de eerste poging omzeilen: een spoor dat "trailing" of
    # "line" heet wordt een kabel. Hier staat er expliciet dat het uit licht en
    # nevel bestaat, en `rope, cable, wire` staan al in de negative prompt. Zij
    # is klein en ver weg - het spoor is het onderwerp, niet zij.
    "boog": {"negatief": BASIS + GEEN_GROND, "prompt": (
        "A vast golden dawn sky above an unbroken sea of cloud. A long, slow, "
        "luminous arc of light curves across the whole frame, like the trail of "
        "a comet made of light and mist, softly glowing and gradually fading at "
        "its far end. At the leading edge of the arc, very small and far away, "
        "the silhouette of a woman gliding with a dark cloak, barely larger than "
        "a bird. Warm amber and rose along the horizon, deep violet above. The "
        "arc drifts and shimmers slowly; the camera does not move. Faint "
        "concentric rings spread outward from the arc. Dreamlike illustration, "
        "flowing ink and watercolour, soft luminous glow, painterly. No text, "
        "no letters, no logos."
    )},
    "overkomen": {"negatief": BASIS + GEEN_GROND, "prompt": (
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
    )},
    # Drie shots die niet over vliegen gaan, van 17 september. Ruuds idee: Vera
    # die gewone, prettige dingen doet, als losse beelden om promo's mee te
    # maken. Ze delen dezelfde regel als de rest - geen gezicht - maar elk heeft
    # een eigen negatieve prompt, want wat je bij vliegen wegvraagt heb je hier
    # juist nodig.
    "strand": {"negatief": BASIS + (
        # Geen `walking` en geen `ground` hier: het paard loopt en er is strand.
        # Wel weg: een tweede ruiter en alles wat er modern uitziet, want dan
        # wordt het een vakantiefoto in plaats van een droom.
        ", front view, facing camera, second rider, crowd, buildings, houses, "
        "modern clothing, jeans, sunglasses, helmet, saddle branding, galloping, "
        "rearing horse, motion blur"
    ), "prompt": (
        "A woman riding a dark horse along a wide empty beach at sunrise, seen "
        "from directly behind and slightly above, small in the frame. Long dark "
        "wavy hair falling down her back, a fine gold headpiece with small "
        "hanging coins, a dark cloak over her shoulders. The horse walks calmly "
        "through the shallow edge of the surf; water lifts softly around its "
        "hooves. Wet sand mirrors the sky. Warm amber and rose along the "
        "horizon, deep violet above, low mist further out over the water. Faint "
        "concentric rings of light spread outward across the wet sand. The "
        "camera holds still while she rides slowly away from it. Dreamlike "
        "illustration, flowing ink and watercolour, soft luminous glow, "
        "painterly. No text, no letters, no logos."
    )},
    # Let op: `rope` en `string` staan hier met opzet **niet** in de negatieve
    # prompt. Een zeilboot heeft touwen, en die wegvragen levert een schip op
    # waarvan het tuig niet klopt.
    "zeilen": {"negatief": BASIS + (
        # `rowing boat, oars, distant sailboat` staan erbij sinds de eerste
        # poging: die leverde haar in een roeiboot op met het zeil op een
        # bootje in de verte. Het model maakte iets ernaast, net als destijds
        # bij `rand.mp4` - en dan moet je wegvragen wat het in plaats daarvan
        # koos, niet nog eens vragen om wat je al vroeg.
        ", front view, facing camera, other boats, second boat, distant "
        "sailboat, rowing boat, rowboat, oars, paddles, harbour, motor, "
        "engine, outboard, flag, pennant, modern yacht, life jacket, choppy "
        "waves, storm"
    ), "prompt": (
        "A woman alone in a small wooden sailing boat on calm open water at "
        "dawn, seen from behind, sitting low at the stern with one hand resting "
        "on the tiller. Directly above her and filling the upper half of the "
        "frame is her own single tall pale sail, close to the camera, its boom "
        "just above her head and its mast rising from the boat she is sitting "
        "in. The sail is softly filled by a light breeze. There is no other "
        "boat anywhere in the frame. Long dark wavy hair lifting slightly in "
        "the wind, a fine gold headpiece with small hanging coins, a dark cloak "
        "around her shoulders. The water is glassy, with long slow ripples spreading out "
        "behind the boat. Warm amber and rose along the horizon, deep violet "
        "above, thin mist on the far water. Faint concentric rings of light "
        "spread outward from the hull. The camera holds still while the boat "
        "glides slowly away. Dreamlike illustration, flowing ink and "
        "watercolour, soft luminous glow, painterly. No text, no letters, no "
        "logos."
    )},
    # Het lastigste van de drie, om twee redenen. Haar handen komen in beeld en
    # die zijn waar een beeldmodel het vaakst de mist in gaat - vandaar `hands
    # relaxed and low` in de opdracht en `distorted hands` in BASIS. En het
    # lichtspoor waar het katje naar slaat heet met opzet geen lint of draad:
    # dat is precies de val uit de eerste ronde, waar "one long line" een kabel
    # werd. Hier is het een krul van licht en verder niets.
    "katje": {"negatief": BASIS + (
        # `artist signature` en de rest staan erbij omdat de eerste poging een
        # gekrabbeld kunstenaarsmerkje rechtsonder opleverde - terwijl
        # `watermark, signature` al in BASIS stonden. Eén woord is bij dit soort
        # artefacten blijkbaar niet genoeg; het moet benoemd worden zoals het
        # eruitziet.
        ", front view, facing camera, second animal, dog, kitten face close-up, "
        "distorted paws, extra legs, toy mouse, leash, collar with tag, clutter, "
        "modern furniture, television, artist signature, initials, handwriting, "
        "corner mark, autograph, stamp, border, frame"
    ), "prompt": (
        "A woman sitting on the floor of a warm dim room at dawn, seen from "
        "directly behind, playing with a small kitten in front of her. Long dark "
        "wavy hair down her back, a fine gold headpiece with small hanging "
        "coins, a dark cloak pooled around her on the floor. Her hands rest low "
        "and relaxed. The kitten reaches up and bats at a slow curl of soft "
        "light drifting just above the floorboards. A low window beyond them "
        "lets in pale dawn light. Deep violet shadows, warm amber glow near the "
        "floor. Faint concentric rings of light hang in the air around the two "
        "of them. The camera holds still; only the kitten and the curl of light "
        "move. Dreamlike illustration, flowing ink and watercolour, soft "
        "luminous glow, painterly. No text, no letters, no logos."
    )},
    # Drie erbij op 17 september: dieren en gezelligheid. Ruuds vraag, en het is
    # dezelfde redenering als bij de gidsscènes - wat Vera dóet beweegt, en dus
    # beweegt het beeld.
    #
    # **De glazen zijn bijzaak en geen onderwerp, en dat is opzet.** TikTok
    # beperkt het promoten van alcohol en kan zulke posts achter een
    # leeftijdsgrens zetten. Een glas op tafel tussen de kaarsen valt daar niet
    # onder; een shot dat over drinken gaat wel. Bovendien verkoopt dit product
    # geen avond maar een ochtend - gezelligheid mag, dronkenschap niet.
    "hondjes": {"negatief": BASIS + (
        ", front view, facing camera, distorted paws, extra legs, merged "
        "animals, aggressive dogs, bared teeth, leash, collar with tag, "
        "modern clothing, park bench, buildings"
    ), "prompt": (
        "A woman sitting on the grass in an open meadow at morning, seen from "
        "directly behind, playing with two small puppies that tumble and roll "
        "around her and climb into her lap. Long dark wavy hair down her back, "
        "a fine gold headpiece with small hanging coins, a dark cloak spread on "
        "the grass around her. The puppies move constantly. Tall grass sways in "
        "the breeze, seed heads drift through the low sun. Warm amber light, "
        "deep violet shadows in the treeline behind. Faint concentric rings of "
        "light spread outward across the grass. The camera holds still. "
        "Dreamlike illustration, flowing ink and watercolour, soft luminous "
        "glow, painterly. No text, no letters, no logos."
    )},
    "vogels": {"negatief": BASIS + (
        ", front view, facing camera, birds of prey, crows attacking, dead "
        "birds, cage, distorted wings, flock covering her face"
    ), "prompt": (
        "A woman standing in a wide field at dawn, seen from directly behind, "
        "one arm held out level while small pale birds land on her arm and "
        "shoulder and lift off again, one after another, circling around her. "
        "Long dark wavy hair lifting in the wind, a fine gold headpiece with "
        "small hanging coins, a dark cloak moving in loose soft folds. The "
        "birds are in constant motion. Warm amber and rose along the horizon, "
        "deep violet above, thin mist over the grass. Faint concentric rings of "
        "light spread outward from where she stands. The camera holds still. "
        "Dreamlike illustration, flowing ink and watercolour, soft luminous "
        "glow, painterly. No text, no letters, no logos."
    )},
    "tafel": {"negatief": BASIS + (
        # Iedereen van achteren of in silhouet: dezelfde regel als voor Vera
        # zelf, en hier ook omdat verzonnen gezichten aan een tafel er snel
        # griezelig uitzien.
        ", front view, facing camera, visible faces, portraits, bottles in "
        "the foreground, drinking from a glass, toasting, crowd, modern "
        "clothing, brand labels, neon, restaurant interior"
    ), "prompt": (
        "A long wooden table outdoors under a tree at dusk, seen from behind "
        "one end. A woman sits at the near end with her back to the camera - "
        "long dark wavy hair down her back, a fine gold headpiece with small "
        "hanging coins, a dark cloak over the chair. Four or five other people "
        "sit further along the table, all seen from behind or in silhouette "
        "against the light, leaning towards each other and gesturing as they "
        "talk. Lanterns and candles line the table among plates and a few "
        "glasses. The candle flames flicker constantly, the lanterns sway in "
        "the breeze, leaves move overhead and warm light shifts across the "
        "table. Warm amber light, deep violet dusk beyond. Faint concentric "
        "rings of light in the air. The camera holds still. Dreamlike "
        "illustration, flowing ink and watercolour, soft luminous glow, "
        "painterly. No text, no letters, no logos."
    )},
}


def start(prompt, negatief):
    antwoord = kling._call("POST", "/v1/videos/text2video", {
        "model_name": MODEL,
        "prompt": prompt,
        "negative_prompt": negatief,
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
            print("\n  %s\n    %s" % (n, SHOTS[n]["prompt"][:160]))
        print("\nNiets gedaan. Geef --ja mee om ze te maken.")
        return 0

    gelukt = 0
    for i, naam in enumerate(te_doen, 1):
        print("[%d/%d] %s" % (i, len(te_doen), naam), flush=True)
        try:
            taak = start(SHOTS[naam]["prompt"], SHOTS[naam]["negatief"])
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
