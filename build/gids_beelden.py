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

PROMPTS = {
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


def verklein(bron, slug):
    """Van wat Kling stuurt naar een JPEG die op een telefoon te laden is."""
    from PIL import Image
    with Image.open(bron) as im:
        im = im.convert("RGB")
        if im.width > BREEDTE:
            hoogte = round(im.height * BREEDTE / im.width)
            im = im.resize((BREEDTE, hoogte), Image.LANCZOS)
        doel = DOEL / (slug + ".jpg")
        im.save(doel, "JPEG", quality=KWALITEIT, optimize=True, progressive=True)
    if bron != doel:
        bron.unlink()
    return doel


def maak(slug):
    """Eén beeld. Geeft het webpad terug, of gooit."""
    taak = kling.submit(volle_prompt(slug), aspect_ratio=VERHOUDING)
    for _ in range(kling.POLL_MAX):
        url = kling.result(taak)
        if url:
            rauw = kling.download(url, DOEL / (slug + "-rauw"))
            return "/gids/" + verklein(rauw, slug).name
        time.sleep(kling.POLL_EVERY)
    raise kling.KlingError("Kling was na {} seconden nog niet klaar.".format(
        kling.POLL_MAX * kling.POLL_EVERY))


def main(argv):
    doen = "--ja" in argv
    alleen = {a for a in argv[1:] if not a.startswith("-")} or None

    if not kling.enabled():
        print("Geen Kling-sleutel. Zet KLING_API_KEY in .env.")
        return 1

    rijen = list(onderwerpen(alleen))
    zonder = [s for _, d, s in rijen if not volle_prompt(s)]
    if zonder:
        print("Geen prompt voor: {}. Zet er een in PROMPTS.".format(", ".join(zonder)))
        return 1

    te_doen = [(p, d, s) for p, d, s in rijen if not d.get("image")]
    klaar = [s for _, d, s in rijen if d.get("image")]
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
            web = maak(slug)
        except Exception as e:                      # noqa: BLE001 - alles melden
            print("MISLUKT: {}".format(e))
            mislukt.append(slug)
            continue
        d["image"] = web
        pad.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        grootte = (WORTEL / "static" / web.lstrip("/")).stat().st_size
        print("{}  {} kB".format(web, round(grootte / 1024)))

    if mislukt:
        print("\nNiet gelukt: {}. Draai nog eens; wat er al staat wordt "
              "overgeslagen.".format(", ".join(mislukt)))
        return 1
    print("\nKlaar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
