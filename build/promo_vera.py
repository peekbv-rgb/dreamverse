"""De promo met Vera: tien seconden, twee beelden, één zin die doorloopt.

    python build/promo_vera.py --ja            # Engels
    python build/promo_vera.py --taal nl --ja  # Nederlands

De beelden komen uit `build/vera_vliegt.py` (text2video bij Kling, 9:16, geen
watermerk). Twee shots die bij elkaar passen omdat ze hetzelfde licht en
dezelfde wolkenzee delen:

    rand.mp4        ze loopt naar de rand, boven de wolken
    overkomen.mp4   ze zweeft

Dat is een verhaal in twee beelden, en het was niet het plan. `rand.mp4` was een
mislukte poging om vliegen te maken - ze liep. Het beeld was op zichzelf goed en
paste toevallig beter bij het geslaagde shot dan het oorspronkelijke idee.

**De zin loopt door over de knip.** Beeld één stelt vast, beeld twee antwoordt:

    Every night you go somewhere.
    Dreamverse remembers where.

Dat tweede woord is de hele belofte van het product. Het staat er niet omdat het
mooi klinkt: het is de reden dat Ruud dit bouwde - bij droom tien was droom drie
allang vergeten.

Drie dingen die hier bewust zo zijn, alle drie geleerd bij de gidsreels:

- **Contour om de letters, geen waas over het beeld.** Een verloop dat de tekst
  overal leesbaar maakt dooft ook de lucht, en die lucht is het enige wat hier
  verkoopt.
- **Alles tussen 285 en 1500.** Instagram legt bij een Reel zijn eigen bediening
  over de onderste 420 pixels.
- **Het merk komt pas in de laatste tellen.** Wie het meteen ziet weet dat het
  reclame is voordat het beeld iets heeft kunnen doen.
"""

import argparse
import importlib.util
import sys
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORTEL))

_spec = importlib.util.spec_from_file_location("reels", WORTEL / "build" / "reels.py")
reels = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reels)

import imageio                                                   # noqa: E402
import numpy as np                                               # noqa: E402
from PIL import Image, ImageDraw                                 # noqa: E402

BREEDTE, HOOGTE = reels.BREEDTE, reels.HOOGTE
FPS = reels.FPS
VEILIG_BOVEN, VEILIG_ONDER = reels.VEILIG_BOVEN, reels.VEILIG_ONDER
KANTLIJN = reels.KANTLIJN
VOID, INK, SITE = reels.VOID, reels.INK, reels.SITE

BRON = WORTEL / "data" / "2-bron" / "vera-shots"
DOEL = WORTEL / "data" / "1-posten" / "promo"

SECONDEN_PER_BEELD = 5

# Drie beelden, en het derde is het slotbeeld.
#
# Eerst waren het er twee en lagen het merk en de knop over het zweefshot heen.
# Dat werkte, maar het beeld en de boodschap vochten om dezelfde ruimte. Met een
# eigen slotbeeld krijgt elk van de drie één taak: vaststellen, antwoorden,
# wijzen. En de boog toont de reis in plaats van de reiziger - dat idee komt uit
# een montage die Ruud zelf in CapCut maakte.
#
# `None` als regel betekent: geen zin, alleen merk en knop.
TELLEN = [
    ("rand.mp4", {
        "en": "Every night you go somewhere.",
        "nl": "Elke nacht ga je ergens heen.",
    }),
    ("overkomen.mp4", {
        "en": "Dreamverse remembers where.",
        "nl": "Dreamverse onthoudt waar.",
    }),
    ("boog.mp4", {"en": None, "nl": None}),
]

KNOP = {"en": "Start free", "nl": "Gratis beginnen"}


def vullend(beeld):
    verhouding = BREEDTE / HOOGTE
    if beeld.width / beeld.height > verhouding:
        h = beeld.height
        b = round(h * verhouding)
    else:
        b = beeld.width
        h = round(b / verhouding)
    x = (beeld.width - b) // 2
    y = (beeld.height - h) // 2
    return beeld.crop((x, y, x + b, y + h)).resize((BREEDTE, HOOGTE),
                                                   Image.LANCZOS)


def overlaag(regel, knop=None, merk=False):
    laag = Image.new("RGBA", (BREEDTE, HOOGTE), (0, 0, 0, 0))

    kap = Image.new("RGBA", (BREEDTE, HOOGTE), VOID + (255,))
    kap.putalpha(reels.verloop(340, 900, 170, 0))
    laag = Image.alpha_composite(laag, kap)

    if knop or merk:
        voet = Image.new("RGBA", (BREEDTE, HOOGTE), VOID + (255,))
        voet.putalpha(reels.verloop(1040, 1340, 0, 180))
        laag = Image.alpha_composite(laag, voet)

    tekenen = ImageDraw.Draw(laag)
    ruimte = BREEDTE - 2 * KANTLIJN

    if regel:
        for punten in (80, 72, 64, 58):
            kop = reels.letter(("georgiai.ttf", "Georgia Italic.ttf",
                                "DejaVuSerif-Italic.ttf"), punten)
            regels = reels.omslaan(tekenen, regel, kop, ruimte)
            if len(regels) <= 2:
                break
        hoog = round(punten * 1.2)
        y = VEILIG_BOVEN + 70
        for r in regels:
            tekenen.text((BREEDTE / 2, y), r, font=kop, fill=INK, anchor="ma",
                         stroke_width=3, stroke_fill=VOID)
            y += hoog

    if knop:
        body = reels.letter(("segoeuisb.ttf", "segoeuib.ttf",
                             "DejaVuSans-Bold.ttf"), 42)
        breed = tekenen.textlength(knop, font=body)
        x0 = BREEDTE / 2 - breed / 2 - 46
        x1 = BREEDTE / 2 + breed / 2 + 46
        yk = VEILIG_ONDER - 250
        tekenen.rounded_rectangle([x0, yk, x1, yk + 92], radius=46,
                                  fill=(122, 92, 214, 238))
        tekenen.text((BREEDTE / 2, yk + 46), knop, font=body, fill=INK,
                     anchor="mm")

    if merk:
        klein = reels.letter(("segoeuisb.ttf", "segoeuib.ttf",
                              "DejaVuSans-Bold.ttf"), 34)
        reels.gespreid(tekenen, "VERA DREAMVERSE", klein, BREEDTE / 2,
                       VEILIG_ONDER - 112, (204, 194, 232), contour=2)
        adres = reels.letter(("segoeui.ttf", "DejaVuSans.ttf"), 32)
        tekenen.text((BREEDTE / 2, VEILIG_ONDER - 52), SITE, font=adres,
                     fill=(188, 178, 214), anchor="ma",
                     stroke_width=2, stroke_fill=VOID)
    return laag


def beeldjes_van(pad, aantal):
    lezer = imageio.get_reader(str(pad))
    try:
        ruw = [Image.fromarray(b).convert("RGB") for b in lezer]
    finally:
        lezer.close()
    if not ruw:
        raise SystemExit("{} bevat geen beeldjes.".format(pad.name))
    # Heen en terug als de clip te kort is: liever een omgekeerde beweging dan
    # een sprong terug naar het begin. Dezelfde keuze als bij de gidsreels.
    # Via reels.uitgerekt(): vertragen in plaats van terugspelen. Zie de
    # correctie van 18 september - Vera die naar een rand loopt en dan weer
    # achteruit is het eerste wat een kijker ziet.
    return reels.uitgerekt(ruw, aantal)


def maak(taal):
    DOEL.mkdir(parents=True, exist_ok=True)
    doel = DOEL / ("vera-promo-" + taal + ".mp4")
    per_beeld = FPS * SECONDEN_PER_BEELD

    schrijver = imageio.get_writer(
        str(doel), fps=FPS, codec="libx264", macro_block_size=8,
        ffmpeg_params=["-crf", "21", "-profile:v", "high",
                       "-movflags", "+faststart"])
    try:
        for i, (clip, regels) in enumerate(TELLEN):
            regel = regels[taal]
            laatste = i == len(TELLEN) - 1
            # Het slotbeeld heeft geen zin en draagt alleen merk en knop; de
            # twee ervoor dragen alleen de zin. Zo vecht niets om dezelfde
            # ruimte, en staat het merk pas in beeld als het beeld zijn werk
            # gedaan heeft.
            kaal = overlaag(regel, KNOP[taal] if laatste else None, laatste)
            beeldjes = beeldjes_van(BRON / clip, per_beeld)
            for n, beeld in enumerate(beeldjes):
                laag = kaal
                doek = vullend(beeld).convert("RGBA")
                schrijver.append_data(
                    np.asarray(Image.alpha_composite(doek, laag).convert("RGB")))
    finally:
        schrijver.close()
    return doel


MUZIEK = WORTEL / "data" / "muziek"

# `rustig` en niet `midden`, en dat is redactie.
#
# De gidsreels stellen een vraag over iemands nacht; die mogen onrustig zijn.
# Deze doet een belofte over onthouden, boven een wolkenzee bij zonsopgang, en
# dan is een beat eronder een ander soort merk dan je wilt zijn. Bij twijfel
# niet de beat - dezelfde regel als bij de verdeling in build/reels.py, en daar
# staat hij er ook met reden: een te kalme track valt niemand op, het
# omgekeerde wel.
STANDAARD_NUMMER = "mixkit-peace-487.mp3"


# De caption. De eerste regel is wat er staat vóór "meer" - daar wordt besloten
# of iemand doorleest, dus dat is de regel uit de video zelf.
#
# Elf hashtags, en dat is een bewuste bovengrens: Instagram staat er dertig toe
# maar een muur leest als spam. Dezelfde afweging als bij de gidsreels, waar er
# acht staan. Hier mogen het er iets meer zijn omdat dit de vastgepinde post is
# en de enige die het hele product beschrijft - die hoeft niet één onderwerp te
# raken maar een publiek.
#
# `#lucidwdreaming` staat er bewust **niet** tussen, hoe groot hij ook is: dat
# is het publiek dat zijn dromen wil sturen, en dit product doet het
# tegenovergestelde - het onthoudt wat er vanzelf gebeurde. Verkeerd publiek
# aantrekken is duurder dan een kleiner bereik, want Instagram leert ervan wie
# je volgende post te zien krijgt.
CAPTION = {
    "en": """Every night you go somewhere. Dreamverse remembers where.

Tell your dream in the morning and get it back as five panels, a reading and a
look ahead — psychological, symbolic or spiritual, whichever way you want to
look at it.

And every dream you tell counts in the next one. Recurring places, people and
animals slowly become one world, and after a while you can see what runs through
all of them. That is the part you cannot do alone: by dream ten, dream three is
long forgotten.

Free to start. Three dreams a month, no card needed. Link in bio.

#dreams #dreammeaning #dreaminterpretation #dreamjournal #dreamanalysis
#dreamsymbols #dreamdiary #subconscious #whatdoesmydreammean #nightmares
#veradreamverse""",
    "nl": """Elke nacht ga je ergens heen. Dreamverse onthoudt waar.

Vertel 's ochtends je droom en krijg hem terug als vijf panelen, met een duiding
en een vooruitblik — psychologisch, symbolisch of spiritueel, hoe je er ook naar
wilt kijken.

En elke droom die je vertelt telt mee in de volgende. Terugkerende plaatsen,
personen en dieren worden langzaam één wereld, en na een tijdje zie je wat er
door al je nachten heen loopt. Dat is het deel dat je alleen niet kunt: bij
droom tien is droom drie allang vergeten.

Gratis om te beginnen. Drie dromen per maand, geen betaalgegevens. Link in bio.

#dromen #droombetekenis #droomuitleg #droomdagboek #droomduiding #droomsymbolen
#watbetekentmijndroom #onderbewuste #nachtmerrie #slapen #veradreamverse""",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--taal", default="en", choices=("en", "nl"))
    ap.add_argument("--ja", action="store_true", help="echt maken")
    ap.add_argument("--nummer", default=STANDAARD_NUMMER,
                    help="een ander nummer uit data/muziek/")
    ap.add_argument("--stil", action="store_true", help="zonder geluid")
    args = ap.parse_args()

    ontbreekt = [c for c, _ in TELLEN if not (BRON / c).exists()]
    if ontbreekt:
        print("Deze clips staan niet in data/vera-vliegt/: %s"
              % ", ".join(ontbreekt))
        print("Draai eerst: python build/vera_vliegt.py --ja")
        return 1

    print("Promo van %d seconden, %d beelden, taal %s."
          % (SECONDEN_PER_BEELD * len(TELLEN), len(TELLEN), args.taal))
    for clip, regels in TELLEN:
        print("  %-16s %s" % (clip, regels[args.taal] or "(slotbeeld: merk en knop)"))
    if not args.ja:
        print("\nNiets gedaan. Geef --ja mee om hem te maken.")
        return 0

    doel = maak(args.taal)
    if not args.stil:
        nummer = MUZIEK / args.nummer
        if not nummer.exists():
            print("Dat nummer staat niet in data/muziek/: %s" % args.nummer)
            return 1
        print("  muziek: %s" % nummer.name)
        reels.geluid_eronder(doel, nummer,
                             SECONDEN_PER_BEELD * len(TELLEN),
                             luider=-4.0)
    tekst = DOEL / ("vera-promo-" + args.taal + ".txt")
    tekst.write_text(CAPTION[args.taal], encoding="utf-8")
    print("\n  %s  %.1f MB" % (doel.name, doel.stat().st_size / 1e6))
    print("  %s" % tekst.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
