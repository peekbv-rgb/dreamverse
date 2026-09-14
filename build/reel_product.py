"""De Reel die zegt wat Dreamverse is.

Er zijn drieënveertig Reels over droomonderwerpen, en die brengen mensen naar
het profiel. Daar staat vervolgens **geen enkele post die uitlegt wat je
verkoopt**: de bio-link is de enige aanwijzing. Dat is een gat in de trechter
precies op de plek waar iemand al belangstelling toont.

Deze maakt er één, in drie tellen van bijna drie seconden:

    1. Wat droomde je vannacht?
    2. Vijf panelen, een duiding en een vooruitblik.
    3. Elke droom die je vertelt telt mee in de volgende.

    python build/reel_product.py --ja            # Engels
    python build/reel_product.py --taal nl --ja  # Nederlands

**Kost geen Kling-eenheid.** De beelden zijn de animaties die al in
`static/voorbeelden/` staan - echte kernmomenten uit het archief, dezelfde die
op de landingspagina staan. Wat dit toevoegt is de volgorde en de tekst.

Drie dingen die hier bewust zo zijn:

- **Dezelfde maten als de gewone Reels.** 1080 x 1920, alles tussen 285 en
  1500, want Instagram legt bij een Reel zijn eigen bediening over de onderste
  420 pixels. Die grenzen staan in build/reels.py en worden hier overgenomen.
- **Contour om de letters en geen waas over het beeld.** Zelfde les als bij de
  schermvullende Reels: een verloop dat de tekst overal leesbaar maakt dooft
  ook het beeld, en die kleuren zijn het enige wat verkoopt.
- **Drie clips en niet één.** Een enkel beeld acht seconden lang is een poster;
  drie stukken maken er een belofte van die ergens heen gaat. De vuurvogel komt
  als laatste, want die is het sterkst.
"""

import argparse
import sys
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORTEL))
sys.path.insert(0, str(WORTEL / "build"))

import importlib.util                                            # noqa: E402

_spec = importlib.util.spec_from_file_location("reels", WORTEL / "build" / "reels.py")
reels = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reels)

import imageio                                                   # noqa: E402
import numpy as np                                               # noqa: E402
from PIL import Image, ImageDraw                                 # noqa: E402

BREEDTE, HOOGTE = reels.BREEDTE, reels.HOOGTE
FPS, SECONDEN = reels.FPS, 9
VEILIG_BOVEN, VEILIG_ONDER = reels.VEILIG_BOVEN, reels.VEILIG_ONDER
KANTLIJN = reels.KANTLIJN
VOID, INK, ZACHT, MERK = reels.VOID, reels.INK, reels.ZACHT, reels.MERK
SITE = reels.SITE

CLIPS = WORTEL / "static" / "voorbeelden"
DOEL = WORTEL / "data" / "reels-product"

# Drie tellen, elk met een clip en een regel. De vuurvogel staat achteraan:
# dat is het sterkste beeld en het laatste wat iemand ziet voordat hij besluit
# of hij op je bio drukt.
TELLEN = [
    ("zee.mp4", {
        "en": ("What did you dream last night?", ""),
        "nl": ("Wat droomde je vannacht?", ""),
    }),
    ("raceauto.mp4", {
        "en": ("Five panels, a reading\nand a look ahead.", ""),
        "nl": ("Vijf panelen, een duiding\nen een vooruitblik.", ""),
    }),
    ("vuurvogel.mp4", {
        "en": ("Every dream you tell\ncounts in the next.", "Start free"),
        "nl": ("Elke droom die je vertelt\ntelt mee in de volgende.", "Gratis beginnen"),
    }),
]


def vullend(beeld):
    """Het beeld schermvullend, midden uitgesneden."""
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


def overlaag(regel, knop, laatste):
    """De tekstlaag voor één tel, met doorzichtige achtergrond."""
    laag = Image.new("RGBA", (BREEDTE, HOOGTE), (0, 0, 0, 0))

    kap = Image.new("RGBA", (BREEDTE, HOOGTE), VOID + (255,))
    kap.putalpha(reels.verloop(340, 900, 186, 0))
    laag = Image.alpha_composite(laag, kap)

    voet = Image.new("RGBA", (BREEDTE, HOOGTE), VOID + (255,))
    voet.putalpha(reels.verloop(980, 1300, 0, 196))
    laag = Image.alpha_composite(laag, voet)

    tekenen = ImageDraw.Draw(laag)
    ruimte = BREEDTE - 2 * KANTLIJN

    # De regel bovenaan. Handmatige regelovergangen worden gerespecteerd, want
    # bij drie regels tekst bepaalt de afbreking het ritme - die laat je niet
    # aan een algoritme over.
    for punten in (78, 70, 62, 56):
        kop = reels.letter(("georgiai.ttf", "Georgia Italic.ttf",
                            "DejaVuSerif-Italic.ttf"), punten)
        regels = []
        for stuk in regel.split("\n"):
            regels.extend(reels.omslaan(tekenen, stuk, kop, ruimte))
        if len(regels) <= 3:
            break
    hoog = round(punten * 1.2)
    y = VEILIG_BOVEN + 60
    for r in regels:
        tekenen.text((BREEDTE / 2, y), r, font=kop, fill=INK, anchor="ma",
                     stroke_width=3, stroke_fill=VOID)
        y += hoog

    if knop:
        # Geen echte knop: in een Reel is niets aanklikbaar. Wel de vorm ervan,
        # zodat het oog weet waar het heen moet - en dat is de bio.
        body = reels.letter(("segoeuisb.ttf", "segoeuib.ttf",
                             "DejaVuSans-Bold.ttf"), 42)
        breed = tekenen.textlength(knop, font=body)
        x0 = BREEDTE / 2 - breed / 2 - 46
        x1 = BREEDTE / 2 + breed / 2 + 46
        yk = VEILIG_ONDER - 260
        tekenen.rounded_rectangle([x0, yk, x1, yk + 92], radius=46,
                                  fill=(122, 92, 214, 235))
        tekenen.text((BREEDTE / 2, yk + 46), knop, font=body, fill=INK,
                     anchor="mm")

    if laatste:
        klein = reels.letter(("segoeuisb.ttf", "segoeuib.ttf",
                              "DejaVuSans-Bold.ttf"), 34)
        reels.gespreid(tekenen, "VERA DREAMVERSE", klein, BREEDTE / 2,
                       VEILIG_ONDER - 118, (200, 190, 228), contour=2)
        adres = reels.letter(("segoeui.ttf", "DejaVuSans.ttf"), 32)
        tekenen.text((BREEDTE / 2, VEILIG_ONDER - 58), SITE, font=adres,
                     fill=(184, 174, 210), anchor="ma",
                     stroke_width=2, stroke_fill=VOID)
    return laag


def beeldjes_van(pad, aantal):
    """`aantal` beeldjes uit deze clip, heen en terug als hij te kort is."""
    lezer = imageio.get_reader(str(pad))
    try:
        ruw = [Image.fromarray(b).convert("RGB") for b in lezer]
    finally:
        lezer.close()
    if not ruw:
        raise SystemExit("{} bevat geen beeldjes.".format(pad.name))
    reeks = ruw + ruw[-2:0:-1] if len(ruw) > 1 else ruw
    return [reeks[i % len(reeks)] for i in range(aantal)]


def maak(taal):
    DOEL.mkdir(parents=True, exist_ok=True)
    doel = DOEL / ("dreamverse-" + taal + ".mp4")
    per_tel = FPS * SECONDEN // len(TELLEN)

    schrijver = imageio.get_writer(
        str(doel), fps=FPS, codec="libx264", macro_block_size=8,
        ffmpeg_params=["-crf", "21", "-profile:v", "high",
                       "-movflags", "+faststart"])
    try:
        for i, (clip, teksten) in enumerate(TELLEN):
            regel, knop = teksten[taal]
            laatste = i == len(TELLEN) - 1
            laag = overlaag(regel, knop, laatste)
            for beeld in beeldjes_van(CLIPS / clip, per_tel):
                doek = vullend(beeld).convert("RGBA")
                schrijver.append_data(
                    np.asarray(Image.alpha_composite(doek, laag).convert("RGB")))
    finally:
        schrijver.close()
    return doel


CAPTION = {
    "en": """What Dreamverse does, in nine seconds.

Tell your dream in the morning and get it back as five panels, a reading and a
look ahead. Every dream you tell counts in the next one — recurring places,
people and animals slowly become one world.

Free to start. Link in bio.

#dreams #dreammeaning #dreaminterpretation #dreamjournal #veradreamverse""",
    "nl": """Wat Dreamverse doet, in negen seconden.

Vertel 's ochtends je droom en krijg hem terug als vijf panelen, met een duiding
en een vooruitblik. Elke droom die je vertelt telt mee in de volgende —
terugkerende plaatsen, personen en dieren worden zo langzaam één wereld.

Gratis om te beginnen. Link in bio.

#dromen #droombetekenis #droomuitleg #droomdagboek #veradreamverse""",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--taal", default="en", choices=("en", "nl"))
    ap.add_argument("--ja", action="store_true", help="echt maken")
    args = ap.parse_args()

    ontbreekt = [c for c, _ in TELLEN if not (CLIPS / c).exists()]
    if ontbreekt:
        print("Deze clips staan niet in static/voorbeelden/: %s"
              % ", ".join(ontbreekt))
        return 1

    print("Eén Reel van %d seconden, %d tellen, taal %s."
          % (SECONDEN, len(TELLEN), args.taal))
    for clip, teksten in TELLEN:
        print("  %-16s %s" % (clip, teksten[args.taal][0].replace("\n", " ")))
    if not args.ja:
        print("\nNiets gedaan. Geef --ja mee om hem te maken.")
        return 0

    doel = maak(args.taal)
    tekst = DOEL / ("dreamverse-" + args.taal + ".txt")
    tekst.write_text(CAPTION[args.taal], encoding="utf-8")
    print("\n  %s  %.1f MB" % (doel.name, doel.stat().st_size / 1e6))
    print("  %s" % tekst.name)
    print("\nZet hem vast bovenaan je profiel: dit is de enige post die zegt")
    print("wat je verkoopt, en alle andere brengen mensen ernaartoe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
