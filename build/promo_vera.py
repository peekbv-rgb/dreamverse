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

BRON = WORTEL / "data" / "vera-vliegt"
DOEL = WORTEL / "data" / "promo-vera"

SECONDEN_PER_BEELD = 5

TELLEN = [
    ("rand.mp4", {
        "en": "Every night you go somewhere.",
        "nl": "Elke nacht ga je ergens heen.",
    }),
    ("overkomen.mp4", {
        "en": "Dreamverse remembers where.",
        "nl": "Dreamverse onthoudt waar.",
    }),
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
    reeks = ruw + ruw[-2:0:-1] if len(ruw) > 1 else ruw
    return [reeks[i % len(reeks)] for i in range(aantal)]


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
            kaal = overlaag(regel)
            # In het laatste beeld komen knop en merk er halverwege bij. Wie ze
            # meteen ziet, weet dat het reclame is voordat het beeld iets heeft
            # kunnen doen.
            met_merk = overlaag(regel, KNOP[taal], True) if laatste else None
            beeldjes = beeldjes_van(BRON / clip, per_beeld)
            for n, beeld in enumerate(beeldjes):
                laag = met_merk if (laatste and n >= per_beeld // 2) else kaal
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


def muziek_eronder(video, nummer, luider=-4.0):
    """Het geluid eronder zetten zonder het beeld opnieuw te coderen.

    `-c:v copy`, dus een ander nummer proberen kost seconden in plaats van een
    halve minuut. De stille versie blijft de bron.
    """
    import subprocess
    import imageio_ffmpeg

    duur = SECONDEN_PER_BEELD * len(TELLEN)
    vanaf = reels.beste_start(nummer)
    fade_uit = max(duur - 1.4, 0.1)
    filter_ = ("afade=t=in:st=0:d=0.8,"
               "afade=t=out:st={:.2f}:d=1.4,volume={:.1f}dB".format(
                   fade_uit, luider))
    doel = video.with_name(video.stem + "-muziek.mp4")
    opdracht = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
        "-y", "-i", str(video), "-ss", str(vanaf), "-i", str(nummer),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        "-af", filter_, "-shortest", "-movflags", "+faststart", str(doel),
    ]
    subprocess.run(opdracht, check=True)
    video.unlink()
    doel.rename(video)
    return video


CAPTION = {
    "en": """Every night you go somewhere. Dreamverse remembers where.

Tell your dream in the morning and get it back as five panels, a reading and a
look ahead. Every dream you tell counts in the next one — recurring places,
people and animals slowly become one world.

Free to start. Link in bio.

#dreams #dreammeaning #dreaminterpretation #dreamjournal #veradreamverse""",
    "nl": """Elke nacht ga je ergens heen. Dreamverse onthoudt waar.

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
        print("  %-16s %s" % (clip, regels[args.taal]))
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
        muziek_eronder(doel, nummer)
    tekst = DOEL / ("vera-promo-" + args.taal + ".txt")
    tekst.write_text(CAPTION[args.taal], encoding="utf-8")
    print("\n  %s  %.1f MB" % (doel.name, doel.stat().st_size / 1e6))
    print("  %s" % tekst.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
