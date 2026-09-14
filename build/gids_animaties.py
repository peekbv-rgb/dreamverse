"""Van elk gidsbeeld een korte animatie maken, voor de Reels.

De Reels laten een stilstaand beeld langzaam inzoomen. Dat is een goede
oplossing zolang bewegen geld kost - een animatie bij Runway is € 0,55 tot
€ 1,47 per stuk, en dat is voor een Instagram-post niet te verantwoorden.

Maar het Kling-videotegoed verloopt **18 september 2026** en rolt niet door.
Wat er op 14 september nog stond: 904 van de 1000 eenheden. Een animatie van
vijf seconden op `kling-v2-1` in `pro` kost er 3,5, dus zevenentwintig
onderwerpen is 94,5 eenheden - ruim een tiende van wat er anders ongebruikt
verdampt. Het argument tegen bewegen was de prijs, en die is er deze week niet.

    python build/gids_animaties.py --een snakes --ja    # eerst een, om te kijken
    python build/gids_animaties.py --ja                 # de rest erachteraan

Het script is **hervatbaar**: een onderwerp dat al een bestand in
`data/gids-animatie/` heeft wordt overgeslagen. Zo kost een afgebroken run niets
extra, en dat telt hier dubbel - elke mislukte poging is tegoed dat weg is.

Drie regels in de bewegingsopdracht, en ze komen uit dezelfde hoek als `STYLE`
en `NEGATIVE` in `kling.py`:

- **Alleen de wereld beweegt, niet de camera.** Een zwenk of een zoom maakt er
  een filmpje van; wat we willen is een beeld dat ademt. Water dat rimpelt, stof
  dat beweegt, licht dat verschuift.
- **Er komt niets bij.** Geen figuren die in beeld lopen, geen gezichten die
  verschijnen, geen tekst. Een beeldmodel dat vijf seconden mag invullen
  verzint anders een mens in een deuropening waar een lege deuropening stond -
  en juist bij deze onderwerpen is dat precies wat er niet mag gebeuren.
- **Traag.** Deze beelden staan onder een vraag over iemands droom; een snelle
  beweging leest als een reclame.
"""

import argparse
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORTEL))

from dotenv import load_dotenv                                  # noqa: E402
load_dotenv(WORTEL / ".env")

import kling                                                     # noqa: E402

ONDERWERPEN = WORTEL / "knowledge" / "droomgids"
BEELDEN = WORTEL / "static" / "gids"
UIT = WORTEL / "data" / "gids-animatie"
# De staande set, voor de schermvullende Reels. Zie gids_beelden.py --staand.
BEELDEN_STAAND = WORTEL / "data" / "gids-staand"
UIT_STAAND = WORTEL / "data" / "gids-animatie-staand"

MODEL = "kling-v2-1"
MODUS = "pro"
SECONDEN = 5
KOSTEN = 3.5          # eenheden per animatie, gemeten op droom 12

# Wat er in elk beeld beweegt. Zonder deze regel krijgt het model alleen de
# algemene opdracht en kiest het zelf - en dan gaat er bij "spiders" een spin
# lopen waar een leeg web hoorde te hangen.
BEWEGING = {
    # baby: twee handen om een lichtje heen.
    "baby": "the small light cupped in the hands pulses very slowly, warmer then cooler",
    # being-chased: een pad met mist.
    "being-chased": "mist drifts slowly across the path, the grass bends in a light wind",
    # being-late: een klok en stoflicht.
    "being-late": "dust motes drift through the light, the shadows creep almost imperceptibly",
    # being-naked: een lege zaal met een stoel.
    "being-naked": "dust motes drift through the empty hall, the light shifts slowly across the floor",
    # birds: vogels tegen de lucht.
    "birds": "the birds glide slowly on held wings, the clouds drift behind them",
    # cant-move: een lege slaapkamer op het blauwe uur, deur op een kier.
    "cant-move": "the light in the room shifts almost imperceptibly toward dawn, "
                 "the shadows lengthen, the door stays exactly where it is",
    # car: een lege weg door een voorruit, koplampen op nat asfalt.
    "car": "the wet asphalt glistens as the light moves over it, fine rain drifts "
           "through the headlight beams, the road stays still",
    # cat: een kat op een vensterbank, van achteren.
    "cat": "the cat's fur stirs faintly, its ear turns a little, moonlight shifts "
           "in the dark garden beyond the glass",
    # cheating: een leeg vertrek met een gordijn.
    "cheating": "the curtain stirs faintly, the light moves across the empty room",
    # deceased-person: kaarslicht.
    "deceased-person": "the candle flame sways gently, the shadows breathe on the wall",
    # dogs: een hond ver weg op een maanverlicht pad.
    "dogs": "mist drifts low across the moonlit path, the grass moves in a faint "
            "breeze, the dog stays exactly where it stands",
    # dying: mist die oplicht.
    "dying": "the mist drifts slowly upward and the light behind it brightens",
    # ex: een foto in schuin licht.
    "ex": "dust drifts through the slanted light, one edge of the photograph lifts faintly",
    # falling: wolken van bovenaf.
    "falling": "the clouds move slowly past, the air below shimmers",
    # fire: vuur.
    "fire": "the flames move slowly, embers rise and fade into the dark",
    # flying: wolken onder je.
    "flying": "the clouds drift below, the light along the horizon shifts",
    # getting-lost: een doolhof van straatjes van bovenaf, met warme ramen.
    "getting-lost": "the warm windows flicker faintly one by one, thin mist drifts "
                    "between the rooftops, the streets stay still",
    # horse: een paard in een veld bij eerste licht, mist tot de knieen.
    "horse": "the mist drifts slowly across the field, the horse's mane and tail "
             "move in a light wind, the sky slowly brightens",
    # house: kamers met licht.
    "house": "the light moves slowly across the rooms, a curtain stirs",
    # mother: een stoel, een warme kop, een jas.
    "mother": "steam rises slowly from the cup, the sleeve of the coat stirs faintly",
    # pregnancy: licht in het midden, water.
    "pregnancy": "the light at the centre pulses slowly, the water ripples outward",
    # school: raamlicht en stof.
    "school": "dust drifts through the window light, a page lifts slightly and settles",
    # snakes: een lichtslang door donker gras.
    "snakes": "the light along the serpent's scales travels slowly from head to tail, "
              "the tall grass sways in a faint breeze",
    # spiders: een web vol dauw, geen spin.
    "spiders": "the dew drops tremble on the web, the strands move in a faint breeze, "
               "no spider appears",
    # stranger: een gestalte in een lichte deuropening.
    "stranger": "the light in the doorway brightens very slowly, dust drifts through it, "
                "the figure does not move or step forward",
    # teeth-falling-out: parels die door donker water zakken.
    "teeth-falling-out": "the pearls sink slowly through the dark water, drifting apart, "
                         "small bubbles trailing upward",
    # water: een wateroppervlak.
    "water": "the surface ripples outward in slow rings, the reflections shift",
    # --- de zes van 14 september ------------------------------------------ #
    # father: een lege werkplaats bij eerste licht, jas over de stoel.
    "father": "the morning light through the window slowly brightens, dust "
              "drifts across the bench, the sleeve of the jacket stirs faintly",
    # money: oude munten op een donkere tafel, een vangt het licht.
    "money": "the light shifts slowly across the coins so the glints travel "
             "from one to the next, the shadows lengthen a little",
    # blood: een druppel die oplost in helder water.
    "blood": "the red drop keeps unfurling very slowly into soft ribbons, "
             "drifting outward and thinning, nothing else moves",
    # drowning: het oppervlak van onderaf, licht dat erdoorheen breekt.
    "drowning": "the shafts of light sway gently as the surface above moves, "
                "bubbles rise slowly toward it",
    # wedding: twee ringen op linnen, droge blaadjes eromheen.
    "wedding": "the warm light moves slowly across the rings so they catch it "
               "in turn, one dried petal shifts a little",
    # mirror: een staande spiegel in een lege kamer, alleen licht erin.
    "mirror": "the light held in the mirror slowly brightens and dims again, "
              "dust drifts through the room, nothing appears in the glass",
    # --- de tien van de tweede ronde ---------------------------------- #
    # train: een leeg perron in de schemering, rails die de mist in lopen.
    "train": "mist drifts slowly across the rails, the single lamp flickers "
             "faintly, no train arrives and nobody appears",
    # hair: een lint haar op de wind tegen een bleke ochtendlucht.
    "hair": "the strands of hair ripple and drift on the wind, turning slowly, "
            "the sky behind them brightens a little",
    # stairs: een brede stenen trap die omhoog krult het licht in.
    "stairs": "the light from above slowly brightens and moves down the steps, "
              "dust drifts in the shaft of light, nothing climbs them",
    # forest: hoge bomen in ochtendmist met zonneschachten.
    "forest": "the mist drifts slowly between the trunks, the shafts of sun "
              "shift and sharpen, leaves move in a faint breeze",
    # exam: een lege tafel in een grote zaal, een blad en een potlood.
    "exam": "the grey light from the high windows shifts slowly across the "
            "desk, one corner of the paper lifts and settles, nobody enters",
    # wolf: een wolf aan de rand van een maanverlichte open plek.
    "wolf": "the wolf's breath drifts visibly in the cold air and its fur "
            "stirs, the grass moves, it stays exactly where it stands",
    # bridge: een stenen brug over stil water bij eerste licht.
    "bridge": "the mist beneath the bridge drifts and thins slowly, the water "
              "ripples faintly, the far end stays out of sight",
    # phone: een hoorn naast de haak op een donkere tafel.
    "phone": "the warm light shifts slowly across the receiver and the curling "
             "cord, dust drifts, nothing is picked up",
    # storm: een wolkenfront boven een open landschap.
    "storm": "the cloud front rolls slowly forward, one distant flash pulses "
             "inside it, the sunlit grass in front bends in the rising wind",
    # door: een oude deur op een kier met warm licht erdoorheen.
    "door": "the warm light through the gap slowly brightens and steadies, "
            "dust drifts in it, the door neither opens nor closes",
}

# "no new people ... enter the frame" en niet "no people": bij cat, dogs, horse,
# birds en snakes staat het dier er juist al, en dat moet blijven bewegen. Met de
# kortere formulering leest het model het als "geen dieren" en houdt het het beest
# stil of laat het uit beeld lopen.
ALGEMEEN = ("very slow, gentle, ambient motion. the camera does not move, "
            "no pan, no zoom, no dolly. keep the composition exactly as it is. "
            "no new people, faces, animals or objects enter the frame, "
            "and no text or letters appear. painterly, dreamlike, calm.")


def onderwerpen():
    return sorted(p.stem for p in ONDERWERPEN.glob("*.json"))


def beeld_van(slug, staand=False):
    """Het bestand achter het veld `image` van dit onderwerp.

    Staand staat niet in de JSON: dat veld is het webpad voor de gidspagina en
    blijft 16:9. De staande set ligt onder zijn eigen naam in data/.
    """
    if staand:
        return BEELDEN_STAAND / (slug + ".jpg")
    data = json.loads((ONDERWERPEN / (slug + ".json")).read_text(encoding="utf-8"))
    naam = (data.get("image") or "").strip()
    if not naam:
        return None
    return WORTEL / "static" / naam.lstrip("/")


def opdracht(slug):
    eigen = BEWEGING.get(slug)
    if not eigen:
        return None
    return eigen + ". " + ALGEMEEN


def start(bestand, prompt):
    rauw = base64.b64encode(bestand.read_bytes()).decode()
    antwoord = kling._call("POST", "/v1/videos/image2video", {
        "model_name": MODEL,
        "mode": MODUS,
        "duration": str(SECONDEN),
        "image": rauw,
        "prompt": prompt,
        # Laag: het beeld moet herkenbaar blijven. Hoog laat het model zijn
        # eigen interpretatie erdoorheen duwen en dan verandert de compositie.
        "cfg_scale": 0.5,
    })
    return (antwoord.get("data") or {}).get("task_id")


def wacht(task_id, minuten=10):
    grens = time.time() + minuten * 60
    vorige = None
    while time.time() < grens:
        r = kling._call("GET", "/v1/videos/image2video/" + task_id)
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
    print("      nog niet klaar na %d minuten; task_id %s" % (minuten, task_id))
    return None


def haal(url, doel):
    with urllib.request.urlopen(url, timeout=180) as r:
        doel.write_bytes(r.read())
    return doel.stat().st_size


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--een", help="alleen dit onderwerp")
    ap.add_argument("--ja", action="store_true", help="echt versturen")
    ap.add_argument("--opnieuw", action="store_true",
                    help="ook onderwerpen die al een animatie hebben")
    ap.add_argument("--staand", action="store_true",
                    help="de staande (9:16) set animeren")
    args = ap.parse_args()

    if not kling.enabled():
        print("Geen Kling-sleutel. Zet KLING_API_KEY in .env.")
        return 1

    lijst = [args.een] if args.een else onderwerpen()

    # Weigeren te draaien als er een bewegingsopdracht ontbreekt, in plaats van
    # het onderwerp stil over te slaan. Zelfde regel als in gids_beelden.py:
    # stil overslaan levert een reeks op waar er een tussenuit is en niemand
    # ziet welke.
    zonder = [s for s in lijst if not opdracht(s)]
    if zonder:
        print("Geen bewegingsopdracht in BEWEGING voor: %s" % ", ".join(zonder))
        print("Vul die eerst aan; zonder opdracht verzint het model zelf iets.")
        return 1

    uit = UIT_STAAND if args.staand else UIT
    uit.mkdir(parents=True, exist_ok=True)
    te_doen = []
    for slug in lijst:
        doel = uit / (slug + ".mp4")
        if doel.exists() and not args.opnieuw:
            continue
        beeld = beeld_van(slug, args.staand)
        if not beeld or not beeld.exists():
            print("%-18s geen beeld op schijf, overgeslagen" % slug)
            continue
        te_doen.append((slug, beeld, doel))

    print("%d onderwerpen te doen, %.1f eenheden (%d al klaar)"
          % (len(te_doen), len(te_doen) * KOSTEN, len(lijst) - len(te_doen)))
    if not args.ja:
        for slug, beeld, _ in te_doen:
            print("  %-18s %s" % (slug, beeld.name))
        print("\nNiets gedaan. Geef --ja mee om het echt te doen.")
        return 0

    gelukt = 0
    for i, (slug, beeld, doel) in enumerate(te_doen, 1):
        print("[%d/%d] %s" % (i, len(te_doen), slug), flush=True)
        try:
            taak = start(beeld, opdracht(slug))
            if not taak:
                print("      geen task_id terug")
                continue
            url = wacht(taak)
            if not url:
                continue
            groot = haal(url, doel)
            print("      %s (%.1f MB)" % (doel.name, groot / 1e6))
            gelukt += 1
        except kling.KlingError as e:
            # Doorgaan met de rest: een onderwerp dat faalt mag de reeks niet
            # stoppen, want elke minuut die we niet draaien is tegoed dat
            # woensdag verdampt.
            print("      %s" % e)

    print("\n%d van de %d gelukt, ongeveer %.1f eenheden gebruikt."
          % (gelukt, len(te_doen), gelukt * KOSTEN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
