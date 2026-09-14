"""Eén beeld per onderwerp van Vera's Dream Guide.

Het veld `"image"` staat al in elke JSON en wordt overal gebruikt zodra het
gevuld is: als kaartbeeld op het overzicht, als hero boven het artikel, en als
`og:image` bij een gedeelde link. Alleen was het nog nergens gevuld.

    python build/gids_beelden.py --check      # wat zou er gemaakt worden
    python build/gids_beelden.py --ja         # maken en de JSON bijwerken
    python build/gids_beelden.py --ja snakes water

Vier eenheden per beeld bij Kling, dus negen onderwerpen is 36 van de ruim 600
die er nog staan. Dat tegoed verloopt 18 september 2026 en rolt niet door, dus
dit is er een goede besteding van.

Drie dingen die hier bewust in zitten.

**Dezelfde stijl als de panelen.** `kling.STYLE` en `kling.NEGATIVE` komen uit
`kling.py` en worden hier niet overgeschreven. Wie op een gidspagina landt en
daarna de app opent, hoort dezelfde hand te zien - dat is het hele argument
waarom de panelen bij Kling blijven en niet bij een goedkoper model.

**Geen mensen met een gezicht.** Deze beelden staan op een openbare pagina en
worden als voorvertoning meegestuurd bij elke gedeelde link. Een herkenbaar
gezicht bij "dromen over je ex" of "dromen over een baby" suggereert een
persoon, en dat is precies wat een droom niet is. Dus: silhouetten, van
veraf, afgewend, of helemaal geen figuur.

**Niet letterlijk, en niet eng.** Het onderwerp is de aanleiding, niet de
opdracht. Bij tanden geen mond en geen bloed, bij spinnen geen close-up van een
spin: iemand die 's ochtends zoekt op "dromen over spinnen" is er meestal van
geschrokken, en dan is een grote harige spin op het scherm geen hulp. Het beeld
mag de sfeer van de droom hebben zonder de schrik.
"""

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

WORTEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORTEL))
load_dotenv(WORTEL / ".env")

import kling  # noqa: E402  - moet ná load_dotenv

ONDERWERPEN = WORTEL / "knowledge" / "droomgids"
DOEL = WORTEL / "static" / "gids"
WEBPAD = "/gids/{}.jpg"

# 16:9 - dat past op de kaart (die snijdt naar 16:10), boven het artikel (die
# snijdt naar max 22rem hoog) en op een gedeelde link (1200 x 630 is 1,90:1).
VERHOUDING = "16:9"

# De staande set, alleen voor de Reels.
#
# De gidspagina's hebben 16:9 nodig: dat is de vorm van een kaart, van de hero
# boven een artikel en van een og:image. Instagram is 9:16, en een liggend beeld
# daarin tonen kan maar op twee manieren - in een kader met randen eromheen, of
# inzoomen en driekwart van de compositie weggooien. Een eigen staande set lost
# dat op zonder een van beide.
#
# Ze gaan naar `data/` en niet naar `static/`: ze worden nergens geserveerd,
# alleen door build/reels.py gelezen. In `static/` zouden ze bij elke deploy
# meegaan zonder dat iemand ze opvraagt.
DOEL_STAAND = WORTEL / "data" / "gids-staand"
VERHOUDING_STAAND = "9:16"

PROMPTS = {
    # Tien onderwerpen erbij op 14 september, tweede ronde. Dezelfde drie regels:
    # geen gezichten, niet letterlijk, niet eng.
    "train":
        "an empty railway platform at dusk, the rails curving away into mist, "
        "a single lamp lit further down, the departure board too far to read, "
        "no people, wide and quiet",
    "hair":
        "a long dark ribbon of hair lifted on the wind against a pale morning "
        "sky, drifting free of anything, seen from a distance, no face and no "
        "head, weightless",
    "stairs":
        "a wide stone staircase curving upward into soft light, worn in the "
        "middle by use, the top out of sight, warm light from above and cool "
        "shadow below, no people",
    "forest":
        "tall trees in early morning mist, shafts of low sun between the "
        "trunks, a faint path that disappears after a few steps, seen from "
        "standing height, no figures",
    "exam":
        "a single empty desk in a large hall, a blank sheet of paper and one "
        "pencil on it, high windows with grey light, rows of other desks "
        "receding into soft focus, no people",
    "wolf":
        "a single wolf standing at the edge of a moonlit clearing, seen from a "
        "distance in profile, breath visible in cold air, dark trees behind, "
        "watchful and still rather than threatening",
    "bridge":
        "a long stone bridge over still water at first light, mist below it so "
        "the far end is not visible, seen from the near bank, no people, calm "
        "and wide",
    "phone":
        "an old telephone receiver lying off the hook on a dark table, the cord "
        "curling away into shadow, a small warm light from one side, no hands "
        "and no faces, quiet",
    "storm":
        "a great dark cloud front moving in over an open landscape, still "
        "sunlit in the foreground, one distant flash inside the cloud, seen "
        "from far away, no people and no buildings",
    "door":
        "a single old door standing ajar in a bare wall, warm light spilling "
        "through the gap onto a dark floor, nothing visible beyond it, seen "
        "straight on, no people",
    # Zes onderwerpen erbij op 14 september. Dezelfde drie regels als de rest:
    # geen gezichten, niet letterlijk, en niet eng. Bij de mensen-onderwerpen
    # (father) is het beeld de plek die hij net verliet, zoals bij mother.
    "father":
        "an empty workshop at first light, a jacket over the back of a chair, "
        "a pair of worn tools laid down on the bench, a window with the morning "
        "behind it, no people and no faces, warm and quiet",
    "money":
        "a scattering of old coins on a dark table, one catching a single warm "
        "light from above, the rest in shadow, seen from close but not "
        "touching, no hands and no faces, still and unhurried",
    # Bloed: geen wond, geen lichaam, niets medisch. Een druppel in water is
    # het beeld dat mensen zelf beschrijven en het schrikt niemand af.
    "blood":
        "a single dark red drop dispersing slowly in clear water, unfurling "
        "into soft ribbons, lit from one side, seen close up against a deep "
        "blue ground, no body, no wound, no hands, quiet and weightless",
    # Verdrinken: van onder naar het licht toe, niet iemand die kopje-onder
    # gaat. Het beeld moet over water gaan en niet over paniek.
    "drowning":
        "the surface of water seen from below, pale light breaking through it "
        "in wide slow shafts, bubbles rising toward it, deep blue-green fading "
        "to dark underneath, no figure and no face, calm and vast",
    "wedding":
        "two rings resting side by side on pale linen, a scatter of dried "
        "petals around them, low warm light from one side, an empty hall "
        "softly out of focus behind, no people and no faces",
    "mirror":
        "an old standing mirror in an empty room at dusk, its surface holding "
        "only light and the outline of a window, nothing else reflected, dust "
        "drifting in the air, no figure and no face",
    "snakes":
        "a single serpent of light coiling through tall dark grass at night, "
        "its scales catching a low green glow, seen from a distance, calm and "
        "watchful rather than threatening, deep indigo sky above",
    "teeth-falling-out":
        "small white pearls falling slowly through dark water, drifting apart "
        "as they sink, a pale glow from above, no faces and no mouth, quiet and "
        "weightless",
    "ex":
        "two empty chairs facing each other in an empty room at dusk, one still "
        "warm with light, the other in shadow, a doorway standing open behind "
        "them, no people",
    "being-chased":
        "a lone silhouette running through a corridor of tall trees, seen from "
        "far behind, warm light ahead and long blue shadows stretching after, "
        "nothing visible pursuing",
    "falling":
        "a small figure seen from very far above, falling through soft layered "
        "clouds lit from below by golden light, arms open, more like floating "
        "than dropping",
    "water":
        "a still dark lake at first light, one figure standing at the very edge "
        "seen from behind and far away, the surface holding the whole sky, "
        "faint ripples spreading outward",
    "spiders":
        "an enormous web strung between bare branches at dawn, every thread "
        "beaded with dew and catching the light, seen from a distance, "
        "geometric and delicate, no spider",
    "dogs":
        "a dog waiting at the end of a long moonlit path, seen from far off, "
        "its outline warm against cool blue night, the path curving away behind "
        "the viewer",
    "baby":
        "a small bundle of soft light held in cupped hands, seen from above, "
        "surrounded by deep warm dark, no faces, tender and quiet",
    # Het enige onderwerp dat over een persoon gaat terwijl er geen gezicht mag
    # staan. Dat valt hier samen: in het artikel is de onbekende de bode - de
    # figuur die van buiten komt en iets brengt in plaats van iets weghaalt - en
    # een gestalte in een lichte deuropening is per constructie gezichtsloos.
    # De open hand is dat "brengen", het ochtendlicht houdt het van een
    # indringer af.
    "stranger":
        "a still silhouette standing in an open doorway, seen from inside a "
        "dim room, warm morning light behind them so no face is visible, one "
        "hand slightly open as if offering something, welcoming rather than "
        "unsettling, long soft light falling across the floor",

    # -- de tweede ronde ---------------------------------------------------- #
    "cat":
        "a cat sitting on a windowsill at night, seen from behind, looking out "
        "at a dark garden, one ear turned back toward the room, calm and "
        "unhurried, cool moonlight and a warm lamp behind it",
    "house":
        "a quiet house at dusk seen from the garden, one upstairs window lit "
        "warm gold and the rest dark, a door standing slightly open, nobody "
        "visible, soft mist along the ground",
    "flying":
        "a small figure far above a sleeping landscape at dawn, arms out, seen "
        "from behind and very small against the sky, layered clouds catching "
        "first light, weightless rather than falling",
    "cant-move":
        "a dim bedroom at the blue hour, an empty bed with the covers thrown "
        "back, long still shadows across the floor, the door ajar, nothing "
        "moving, no figure",
    "school":
        "a long empty school corridor in afternoon light, lockers on one side, "
        "an open classroom door at the far end with light spilling out, dust in "
        "the air, nobody there",
    "being-late":
        "an empty station platform at dusk, the last carriage of a train "
        "already far down the track, a large clock with no hands, one suitcase "
        "standing alone, nobody on the platform",
    "being-naked":
        "a single empty chair in the middle of a large bright hall, a coat "
        "fallen on the floor beside it, rows of empty seats facing it, warm "
        "light from high windows, nobody present",
    "getting-lost":
        "a maze of narrow streets seen from above at night, warm windows here "
        "and there, one tiny figure at a crossing far below, the streets folding "
        "into each other, no landmark",
    "car":
        "an empty road at night seen through a windscreen from inside a car, "
        "headlights on wet asphalt, the steering wheel in soft focus in the "
        "foreground, nobody in the seat, quiet rather than tense",
    "fire":
        "a single fire burning in an open landscape at night, seen from a "
        "distance, sparks rising into a deep sky, the ground around it warm "
        "gold and the horizon calm, nothing damaged",
    "mother":
        "a kitchen at early morning, one chair pulled out, a cup still warm on "
        "the table, low golden light through a window, a coat over the chair "
        "back, nobody in the room",
    "horse":
        "a horse standing alone in an open field at first light, seen from a "
        "distance in profile, mist to the knees, wide pale sky, no rider and no "
        "fence in sight",
    "birds":
        "a flock of birds turning together against a wide dawn sky, seen from "
        "below, their shapes catching the light, one bird lower and apart from "
        "the rest, calm and open",
    "pregnancy":
        "a seed of soft light held inside a curved shell of dark water, seen "
        "close, faint concentric rings spreading outward from it, warm glow "
        "against deep blue, abstract and tender, no figure",
    # De drie gevoelige. Hier geldt de regel uit het artikel ook voor het beeld:
    # niets grafisch, niets dat schrikt, en niets dat een uitspraak doet. Wie om
    # zeven uur 's ochtends zoekt op "dromen dat ik doodga" is bang, en dan is
    # het beeld het eerste wat hem geruststelt of niet.
    "dying":
        "a doorway of soft light standing open in a dark field at night, warm "
        "and quiet, a path leading toward it through long grass, stars above, "
        "peaceful and entirely gentle, no figure",
    "deceased-person":
        "a single lit candle on a windowsill at night, its reflection doubled "
        "in the dark glass, a wide calm sky beyond, warm and still, nothing "
        "sombre, no figure",
    "cheating":
        "two cups on a table at dusk, one still steaming and one cold and "
        "pushed aside, a chair turned slightly away, soft blue evening light, "
        "quiet rather than dramatic, nobody present",
}


def onderwerpen(alleen=None):
    for pad in sorted(ONDERWERPEN.glob("*.json")):
        d = json.loads(pad.read_text(encoding="utf-8"))
        slug = d.get("slug") or pad.stem
        if alleen and slug not in alleen:
            continue
        yield pad, d, slug


def volle_prompt(slug):
    kern = PROMPTS.get(slug)
    if not kern:
        return None
    return "{}. {}".format(kern, kling.STYLE)


# Kling levert PNG van rond de 1,7 MB. Negen daarvan op het overzicht is 15 MB
# aan beeld op een pagina die iemand vanaf zijn telefoon opent, en dat is precies
# de reden dat de voorbeeldclips in de app pas bij een klik laden. Dus: JPEG,
# 1200 breed. Dat is ook de maat die Facebook, WhatsApp en LinkedIn van een
# og:image verwachten, en breder heeft geen enkele plek in deze site nodig - de
# kaart is hoogstens 24rem en de hero hoogstens 22rem hoog.
BREEDTE = 1200
KWALITEIT = 82


def verklein(bron, slug, map_=None, breedte=None):
    """Van wat Kling stuurt naar een JPEG die op een telefoon te laden is."""
    from PIL import Image
    map_ = map_ or DOEL
    breedte = breedte or BREEDTE
    with Image.open(bron) as im:
        im = im.convert("RGB")
        if im.width > breedte:
            hoogte = round(im.height * breedte / im.width)
            im = im.resize((breedte, hoogte), Image.LANCZOS)
        doel = map_ / (slug + ".jpg")
        im.save(doel, "JPEG", quality=KWALITEIT, optimize=True, progressive=True)
    if bron != doel:
        bron.unlink()
    return doel


def maak(slug, staand=False):
    """Eén beeld. Geeft het webpad terug, of gooit.

    Staand gaat naar data/gids-staand/ en wordt 1080 breed gehouden: dat is de
    breedte van een Reel, dus verkleinen tot 1200 zou hem eerst groter en dan
    weer kleiner maken.
    """
    map_ = DOEL_STAAND if staand else DOEL
    map_.mkdir(parents=True, exist_ok=True)
    taak = kling.submit(volle_prompt(slug),
                        aspect_ratio=VERHOUDING_STAAND if staand else VERHOUDING)
    for _ in range(kling.POLL_MAX):
        url = kling.result(taak)
        if url:
            rauw = kling.download(url, map_ / (slug + "-rauw"))
            naam = verklein(rauw, slug, map_, 1080 if staand else None).name
            return str(map_ / naam) if staand else "/gids/" + naam
        time.sleep(kling.POLL_EVERY)
    raise kling.KlingError("Kling was na {} seconden nog niet klaar.".format(
        kling.POLL_MAX * kling.POLL_EVERY))


def main(argv):
    doen = "--ja" in argv
    # De staande set voor de Reels. Die schrijft niet in de JSON: het veld
    # `image` is het webpad voor de gidspagina en dat blijft 16:9.
    staand = "--staand" in argv
    alleen = {a for a in argv[1:] if not a.startswith("-")} or None

    if not kling.enabled():
        print("Geen Kling-sleutel. Zet KLING_API_KEY in .env.")
        return 1

    rijen = list(onderwerpen(alleen))
    zonder = [s for _, d, s in rijen if not volle_prompt(s)]
    if zonder:
        print("Geen prompt voor: {}. Zet er een in PROMPTS.".format(", ".join(zonder)))
        return 1

    # Klaar is: het veld staat er **en** het bestand bestaat.
    #
    # Eerst keek dit alleen naar het veld, en dat gaat mis zodra je een nieuw
    # onderwerp schrijft met `"image": "/gids/<slug>.jpg"` er alvast in - het
    # script meldt dan "heeft al een beeld" terwijl de gidspagina een kapot
    # plaatje toont. Precies dat gebeurde met de zes onderwerpen van
    # 14 september.
    def af(d):
        # Staand kijkt alleen naar het bestand: er is geen veld in de JSON dat
        # ernaar wijst, en dat hoort ook niet - de gidspagina gebruikt 16:9.
        if staand:
            return (DOEL_STAAND / ((d.get("slug") or "") + ".jpg")).exists()
        naam = (d.get("image") or "").strip()
        # Het veld is een webpad ("/gids/x.jpg"); op schijf staat dat
        # onder static/.
        return bool(naam) and (WORTEL / "static" / naam.lstrip("/")).exists()

    te_doen = [(p, d, s) for p, d, s in rijen if not af(d)]
    klaar = [s for _, d, s in rijen if af(d)]
    if klaar:
        print("Heeft al een beeld: {}".format(", ".join(klaar)))
    if not te_doen:
        print("Niets te doen.")
        return 0

    print("{} beelden, {} eenheden bij Kling ({} per stuk).".format(
        len(te_doen), len(te_doen) * 4, 4))
    if not doen:
        print("\nDit zou er gemaakt worden. Draai met --ja om het echt te doen.\n")
        for _, _, slug in te_doen:
            print("  {}\n    {}\n".format(slug, volle_prompt(slug)[:150]))
        return 0

    mislukt = []
    for pad, d, slug in te_doen:
        print("  {:<20} ".format(slug), end="", flush=True)
        try:
            web = maak(slug, staand)
        except Exception as e:                      # noqa: BLE001 - alles melden
            print("MISLUKT: {}".format(e))
            mislukt.append(slug)
            continue
        if staand:
            # Niets in de JSON: die wijst naar het liggende beeld voor de
            # gidspagina, en dat moet zo blijven.
            grootte = Path(web).stat().st_size
        else:
            d["image"] = web
            pad.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
            grootte = (WORTEL / "static" / web.lstrip("/")).stat().st_size
        print("{}  {} kB".format(Path(web).name, round(grootte / 1024)))

    if mislukt:
        print("\nNiet gelukt: {}. Draai nog eens; wat er al staat wordt "
              "overgeslagen.".format(", ".join(mislukt)))
        return 1
    print("\nKlaar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
