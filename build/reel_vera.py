"""Een Reel uit losse Vera-shots, met één zin die over de knip doorloopt.

`promo_vera.py` doet dit voor één vaste reeks van drie vliegshots. Dit doet het
voor elke combinatie die er in `data/vera-vliegt/` ligt, en dat zijn er
inmiddels eenentwintig - van het strand tot een casinotafel.

    python build/reel_vera.py --ja reis            # strand + motor
    python build/reel_vera.py --ja --taal nl reis
    python build/reel_vera.py                      # welke reeksen er zijn

**Waarom een eigen script en niet nog een variant in `promo_vera.py`.** Die
maakt één ding en zegt één ding; hier is de reeks het onderwerp. Een nieuwe
combinatie is een regel in `REEKSEN` en verder niets.

Drie dingen die hetzelfde blijven als overal:

- **Alle tekst bovenin**, met een contour om de letters en geen waas over het
  beeld. Zie *Bij de schermvullende Reel staat alle tekst bovenin* in CLAUDE.md:
  het onderwerp van deze shots staat in het onderste deel van het beeld.
- **Het merk pas in de laatste tel.** Wie het meteen ziet weet dat het reclame
  is voordat het beeld iets heeft kunnen doen.
- **Niets loopt achteruit.** De beeldjes komen door `reels.uitgerekt()`, dus een
  clip die te kort is wordt vertraagd en niet teruggespeeld. Dat is de correctie
  van 18 september; een paard dat achteruit loopt is het eerste wat je ziet.
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

import subprocess                                                # noqa: E402
import imageio                                                   # noqa: E402
import imageio_ffmpeg                                            # noqa: E402
import numpy as np                                               # noqa: E402
from PIL import Image, ImageDraw                                 # noqa: E402

BREEDTE, HOOGTE = reels.BREEDTE, reels.HOOGTE
FPS = reels.FPS
VEILIG_BOVEN, VEILIG_ONDER = reels.VEILIG_BOVEN, reels.VEILIG_ONDER
KANTLIJN = reels.KANTLIJN
VOID, INK = reels.VOID, reels.INK
SITE = reels.SITE

SHOTS = WORTEL / "data" / "vera-vliegt"
DOEL = WORTEL / "data" / "reels-vera"
MUZIEK = WORTEL / "data" / "muziek"

def tellen_van(reeks, taal):
    """De tellen van een reeks, met de lengtes van deze taal erin.

    **Een gesproken shot is in twee talen niet even lang.** Vera doet er in het
    Nederlands 5,7 seconden over waar het Engels op 4,8 zit, en met een vaste
    tel valt haar laatste zin er gewoon af - zonder dat iets het meldt, want
    het beeld loopt netjes door. `sec_per_taal` in de reeks zegt per shot welke
    lengte bij welke taal hoort; wat er niet in staat blijft zoals het staat.
    """
    per = REEKSEN[reeks].get("sec_per_taal", {})
    return [(slug, per.get(slug, {}).get(taal, sec), regels)
            for slug, sec, regels in REEKSEN[reeks]["tellen"]]


# De lengte komt uit de reeks zelf; niet elke Reel is even lang.
def duur_van(reeks, taal):
    return sum(sec for _, sec, _ in tellen_van(reeks, taal))

KOP = ("georgiai.ttf", "Georgia Italic.ttf", "DejaVuSerif-Italic.ttf")
BODY = ("segoeui.ttf", "DejaVuSans.ttf")
VET = ("segoeuisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf")

# Een reeks is: welke shots, hoe lang elk, en wat erbij staat.
#
# De zin loopt door over de knip - beeld één stelt vast, beeld twee antwoordt.
# Dat is dezelfde vorm als de promo, en het werkt omdat de kijker de tweede
# helft al wil hebben voordat hij er is.
# Clips die niet in data/vera-vliegt/ staan.
#
# **Een waarde mag een woordenboek per taal zijn.** Bij `vera-intro` moet dat:
# die clip is Vera die praat, en in de Nederlandse Reel stond haar Engelse
# opname onder Nederlandse tekst in beeld. Dat is precies het soort fout dat
# niets meldt - het beeld klopt, de tekst klopt, alleen wat je hoort niet.
ELDERS = {
    "vera-intro": {
        "en": WORTEL / "data" / "vera-frames" / "origineel-en.mp4",
        "nl": WORTEL / "data" / "vera-frames" / "origineel-nl.mp4",
    },
}


def elders(slug, taal):
    p = ELDERS.get(slug)
    return p.get(taal) if isinstance(p, dict) else p

REEKSEN = {
    # De kennismaking, om vast te pinnen. Vier tellen en twaalf seconden.
    #
    # **Het beeld gaat in een kader en wordt niet bijgesneden.** De clip is
    # 1088 x 704 en liggend; naar 9:16 snijden laat een strook van 396 pixels
    # breed over, die dan bijna drie keer opgeblazen moet worden. Op een donkere
    # grond in een kader blijft hij scherp - dezelfde afweging als bij de
    # gekaderde gidsreels.
    #
    # Daarna het strandshot, en dat is geen willekeurige keuze: beide beelden
    # spelen op een strand bij laag licht, dus de knip valt niet op.
    "kennismaking": {
        "tellen": [
            ("vera-intro", 4.8, {
                "en": "Hi, I am Vera.",
                "nl": "Hoi, ik ben Vera.",
            }),
            ("strand", 4.2, {
                "en": "Tell me your dream in the morning.",
                "nl": "Vertel me 's ochtends je droom.",
            }),
            ("strand", 3.0, {"en": None, "nl": None}),
        ],
        "knop": {"en": "Start free", "nl": "Gratis beginnen"},
        # Hetzelfde nummer als de gidsreels in de stemming `licht` - dat is
        # de Reel waarvan Ruud zei dat de muziek beter stond dan de trap.
        "nummer": "mixkit-house-vibes-129.mp3",
        # Het geluid van de clip zelf blijft staan: zij praat erin.
        "behoud": True,
        "stem": "vera-intro",
        # Haar opname staat rond -22 dB; zonder optillen valt ze weg
        # zodra de muziek hoorbaar wordt gezet.
        "stem_luider": 7.0,
        # Gemeten: origineel-en.mp4 duurt 4,80 s, origineel-nl.mp4 5,67 s.
        "sec_per_taal": {"vera-intro": {"nl": 5.7}},
        "kader": ("vera-intro",),
    },

    # Eén shot, drie tellen: haak, belofte, merk. Twaalf seconden - binnen de
    # twaalf tot achttien die op TikTok blijven hangen, en precies wat één shot
    # van tien seconden kan dragen zonder te rekken.
    "strand": {
        "tellen": [
            ("strand", 5.0, {
                "en": "Every night you go somewhere.",
                "nl": "Elke nacht ga je ergens heen.",
            }),
            ("strand", 4.0, {
                "en": "Dreamverse remembers where.",
                "nl": "Dreamverse onthoudt waar.",
            }),
            ("strand", 3.0, {"en": None, "nl": None}),
        ],
        "knop": {"en": "Start free", "nl": "Gratis beginnen"},
        "nummer": "mixkit-peace-487.mp3",
    },
    # Een andere zin dan bij `strand`, met opzet: twee Reels met dezelfde regel
    # naast elkaar op een profiel lezen als één post die dubbel geplaatst is.
    # Dezelfde belofte, andere woorden.
    "motor": {
        "tellen": [
            ("motor", 5.0, {
                "en": "No two nights take the same road.",
                "nl": "Geen twee nachten nemen dezelfde weg.",
            }),
            ("motor", 4.0, {
                "en": "Dreamverse keeps the map.",
                "nl": "Dreamverse houdt de kaart bij.",
            }),
            ("motor", 3.0, {"en": None, "nl": None}),
        ],
        "knop": {"en": "Start free", "nl": "Gratis beginnen"},
        # `licht` in plaats van `rustig`: dit beeld heeft vaart, en de verdeling
        # in reels.py zegt dat beweging energie mag hebben.
        "nummer": "mixkit-house-vibes-129.mp3",
    },
}


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


def gekaderd(beeld):
    """Het beeld op ware grootte midden op een donkere grond.

    Voor een liggende clip die te smal is om schermvullend te maken zonder hem
    op te blazen. Dezelfde vorm als de gekaderde gidsreels: het beeld blijft
    heel, de grond doet de rest.
    """
    doek = Image.new("RGB", (BREEDTE, HOOGTE), VOID)
    breed = BREEDTE - 2 * 40
    hoog = round(beeld.height * breed / beeld.width)
    doek.paste(beeld.resize((breed, hoog), Image.LANCZOS),
               (40, (HOOGTE - hoog) // 2))
    return doek


def overlaag(regel, knop=None, merk=False):
    laag = Image.new("RGBA", (BREEDTE, HOOGTE), (0, 0, 0, 0))
    kap = Image.new("RGBA", (BREEDTE, HOOGTE), VOID + (255,))
    kap.putalpha(reels.verloop(300, 1020 if merk else 900, 205, 0))
    laag = Image.alpha_composite(laag, kap)

    tekenen = ImageDraw.Draw(laag)
    ruimte = BREEDTE - 2 * KANTLIJN

    if regel:
        for punten in (84, 76, 68, 60):
            kop = reels.letter(KOP, punten)
            regels = reels.omslaan(tekenen, regel, kop, ruimte)
            if len(regels) <= 2:
                break
        y = VEILIG_BOVEN + 60
        for r in regels:
            tekenen.text((BREEDTE / 2, y), r, font=kop, fill=INK, anchor="ma",
                         stroke_width=3, stroke_fill=VOID)
            y += round(punten * 1.2)

    if merk:
        klein = reels.letter(VET, 34)
        reels.gespreid(tekenen, "VERA DREAMVERSE", klein, BREEDTE / 2,
                       VEILIG_BOVEN + 120, (224, 216, 244), contour=3)
        adres = reels.letter(BODY, 32)
        tekenen.text((BREEDTE / 2, VEILIG_BOVEN + 176), SITE, font=adres,
                     fill=(212, 204, 234), anchor="ma",
                     stroke_width=3, stroke_fill=VOID)

    if knop:
        # Geen echte knop: in een Reel is niets aanklikbaar. Wel de vorm ervan,
        # zodat het oog weet waar het heen moet - en dat is de bio.
        body = reels.letter(VET, 42)
        breed = tekenen.textlength(knop, font=body)
        x0 = BREEDTE / 2 - breed / 2 - 46
        x1 = BREEDTE / 2 + breed / 2 + 46
        yk = VEILIG_BOVEN + 240
        tekenen.rounded_rectangle([x0, yk, x1, yk + 92], radius=46,
                                  fill=(122, 92, 214, 238))
        tekenen.text((BREEDTE / 2, yk + 46), knop, font=body, fill=INK,
                     anchor="mm")
    return laag


def lees(pad):
    lezer = imageio.get_reader(str(pad))
    try:
        return [Image.fromarray(b).convert("RGB") for b in lezer]
    finally:
        lezer.close()


def maak(naam, taal):
    reeks = REEKSEN[naam]
    DOEL.mkdir(parents=True, exist_ok=True)
    doel = DOEL / ("%s-%s.mp4" % (naam, taal))

    # Per shot één keer inlezen, ook als hij twee tellen bedient.
    ruw = {}
    for slug, _, _ in tellen_van(naam, taal):
        if slug not in ruw:
            # Een tel mag ook naar een bestand elders wijzen - de
            # kennismakingsclip staat in data/vera-frames/ en niet bij de
            # text2video-shots. `ELDERS` is de uitzonderingenlijst; alles wat
            # er niet in staat is gewoon een shot.
            p = elders(slug, taal) or (SHOTS / (slug + ".mp4"))
            if not p.exists():
                raise SystemExit("Geen shot %s gevonden (%s)." % (slug, p))
            ruw[slug] = lees(p)

    # Een shot dat twee tellen achter elkaar bedient moet doorlopen en niet
    # opnieuw beginnen: `motor` draagt hier de tekst én het slot. Daarom wordt
    # per shot één keer uitgerekt over de volle tijd die hij in beeld is, en
    # daarna in stukken geknipt.
    duur = {}
    for slug, sec, _ in tellen_van(naam, taal):
        duur[slug] = duur.get(slug, 0.0) + sec
    stroom = {s: reels.uitgerekt(ruw[s], int(FPS * duur[s])) for s in ruw}
    op = {s: 0 for s in ruw}

    schrijver = imageio.get_writer(
        str(doel), fps=FPS, codec="libx264", macro_block_size=8,
        ffmpeg_params=["-crf", "21", "-profile:v", "high",
                       "-movflags", "+faststart"])
    try:
        tellen = tellen_van(naam, taal)
        for i, (slug, sec, regels) in enumerate(tellen):
            laatste = i == len(tellen) - 1
            laag = overlaag(regels[taal],
                            reeks["knop"][taal] if laatste else None, laatste)
            for _ in range(int(FPS * sec)):
                beeld = stroom[slug][min(op[slug], len(stroom[slug]) - 1)]
                op[slug] += 1
                if slug in reeks.get("kader", ()):
                    doek = gekaderd(beeld).convert("RGBA")
                else:
                    doek = vullend(beeld).convert("RGBA")
                schrijver.append_data(
                    np.asarray(Image.alpha_composite(doek, laag).convert("RGB")))
    finally:
        schrijver.close()

    # **De stem van de bronclip terugzetten.** De Reel wordt beeldje voor
    # beeldje opgebouwd, en daarbij gaat het audiospoor van de bron verloren -
    # ook als die bron iemand is die praat. Bij de kennismaking is dat precies
    # het geluid dat er moet zijn, dus hij wordt er na het renderen weer onder
    # gelegd, op de plek waar die tel begint.
    if reeks.get("stem"):
        stem_slug = reeks["stem"]
        begin = 0.0
        for slug, sec, _ in tellen_van(naam, taal):
            if slug == stem_slug:
                break
            begin += sec
        duur = duur_van(naam, taal)
        bron = elders(stem_slug, taal) or (SHOTS / (stem_slug + ".mp4"))
        tijdelijk = doel.with_name(doel.stem + "-stem.mp4")
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([
            ff, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(doel), "-i", str(bron),
            "-filter_complex",
            "[1:a]volume={1:.1f}dB,adelay={0}|{0},apad[s]".format(
                int(begin * 1000), reeks.get("stem_luider", 0.0)),
            # `-t` en niet `-shortest`: `apad` vult het spoor eindeloos aan,
            # en die combinatie blijft hangen in plaats van af te kappen. De
            # lengte staat toch vast, dus zeg hem gewoon.
            "-map", "0:v", "-map", "[s]", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "160k", "-ac", "2", "-t", "%.2f" % duur,
            "-movflags", "+faststart", str(tijdelijk),
        ], check=True)
        doel.unlink()
        tijdelijk.rename(doel)
    return doel


CAPTION = {
    "kennismaking": {
        "en": """Hi, I am Vera. Tell me your dream in the morning.

You get it back as five panels, a reading and a look ahead - and every dream you
tell counts in the next one. After a few months the places, people and animals
that keep coming back become one world of their own.

Free to start. Link in bio.

#dreams #dreammeaning #dreaminterpretation #dreamjournal #luciddreaming #veradreamverse""",
        "nl": """Hoi, ik ben Vera. Vertel me 's ochtends je droom.

Je krijgt hem terug als vijf panelen, met een duiding en een vooruitblik - en
elke droom die je vertelt telt mee in de volgende. Na een paar maanden worden de
plekken, personen en dieren die blijven terugkomen een eigen wereld.

Gratis om te beginnen. Link in bio.

#dromen #droombetekenis #droomuitleg #droomdagboek #veradreamverse""",
    },
    "strand": {
        "en": """Every night you go somewhere. Dreamverse remembers where.

Tell your dream in the morning and get it back as five panels, a reading and a
look ahead. Every dream you tell counts in the next one - recurring places,
people and animals slowly become one world.

Free to start. Link in bio.

#dreams #dreammeaning #dreaminterpretation #dreamjournal #veradreamverse""",
        "nl": """Elke nacht ga je ergens heen. Dreamverse onthoudt waar.

Vertel 's ochtends je droom en krijg hem terug als vijf panelen, met een duiding
en een vooruitblik. Elke droom die je vertelt telt mee in de volgende.

Gratis om te beginnen. Link in bio.

#dromen #droombetekenis #droomuitleg #droomdagboek #veradreamverse""",
    },
    "motor": {
        "en": """No two nights take the same road. Dreamverse keeps the map.

Tell your dream in the morning and get it back as five panels, a reading and a
look ahead. After a few months the recurring places and people become one world.

Free to start. Link in bio.

#dreams #dreammeaning #dreaminterpretation #dreamjournal #veradreamverse""",
        "nl": """Geen twee nachten nemen dezelfde weg. Dreamverse houdt de kaart bij.

Vertel 's ochtends je droom en krijg hem terug als vijf panelen, met een duiding
en een vooruitblik. Na een paar maanden worden de terugkerende plekken en
personen een wereld.

Gratis om te beginnen. Link in bio.

#dromen #droombetekenis #droomuitleg #droomdagboek #veradreamverse""",
    },
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("reeks", nargs="?", help="welke reeks uit REEKSEN")
    ap.add_argument("--taal", default="en", choices=("en", "nl"))
    ap.add_argument("--ja", action="store_true", help="echt maken")
    ap.add_argument("--nummer", help="een ander nummer uit data/muziek/")
    ap.add_argument("--stil", action="store_true")
    args = ap.parse_args()

    if not args.reeks:
        print("Reeksen:")
        for naam, r in REEKSEN.items():
            print("  %-10s %s" % (naam, " + ".join(s for s, _, _ in r["tellen"])))
        return 0
    if args.reeks not in REEKSEN:
        print("Geen reeks %s." % args.reeks)
        return 1

    print("%s, %.0f seconden, taal %s."
          % (args.reeks, duur_van(args.reeks, args.taal), args.taal))
    for slug, sec, regels in tellen_van(args.reeks, args.taal):
        print("  %-9s %4.1f s  %s" % (slug, sec, regels[args.taal] or "(merk en knop)"))
    if not args.ja:
        print("\nNiets gedaan. Geef --ja mee.")
        return 0

    doel = maak(args.reeks, args.taal)
    if not args.stil:
        nummer = MUZIEK / (args.nummer or REEKSEN[args.reeks]["nummer"])
        if not nummer.exists():
            print("Dat nummer staat niet in data/muziek/: %s" % nummer.name)
            return 1
        reels.geluid_eronder(
            doel, nummer, duur_van(args.reeks, args.taal),
            # -3 dB en niet -6: onder een gemengd spoor zakt muziek
            # verder weg dan wanneer ze het hele spoor is.
            luider=REEKSEN[args.reeks].get("luider", -3.0),
            behoud=REEKSEN[args.reeks].get("behoud", False))
    tekst = DOEL / ("%s-%s.txt" % (args.reeks, args.taal))
    tekst.write_text(CAPTION[args.reeks][args.taal], encoding="utf-8")
    print("\n  %s  %.1f MB" % (doel.name, doel.stat().st_size / 1e6))
    print("  %s" % tekst.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
