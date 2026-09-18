"""De Reel die iets wéggeeft in plaats van iets te vragen.

De drieënveertig gidsreels doen allemaal hetzelfde: een titel, een vraag, en de
belofte dat het antwoord op de site staat. Dat is een advertentie. Dit formaat
geeft het inzicht zelf, en vraagt pas daarna iets - de opzet komt van Ruud, op
17 september:

    0 - 2 s   Dreaming about your ex?
    2 - 9 s   het inzicht, uit het artikel zelf
    9 - 12 s  It may be about who you were back then.
    12 - 15 s Tell Vera what happened - link in bio.

    python build/reel_inzicht.py --ja ex
    python build/reel_inzicht.py --ja --taal nl ex

**Vijftien seconden, en dat is een keuze voor TikTok.** De gidsreels zijn acht
seconden; daar past een vraag in en verder niets. Twaalf tot achttien is waar
TikTok een kijker echt laat blijven, en dat is precies genoeg voor een inzicht
met een wending erachter. Eén shot bij Kling gaat tot tien seconden, dus die
lengte komt hier uit de montage en niet uit het beeld - net als bij
`promo_vera.py`.

**Het inzicht wordt niet geschreven maar overgenomen.** Beat twee komt
letterlijk uit `intro` van het gidsartikel, de eerste twee zinnen. Dat is
dezelfde regel als bij de captions in `reels.py`, en om dezelfde reden: bij
`dying` en `pregnancy` staat de ontkenning in de tweede zin, en een Reel die
alleen de eerste pakt zegt dan iets wat de pagina juist ontkent. Verzin hier dus
nooit een inzicht - als het niet in het artikel staat, hoort het niet in de
Reel.

**De wending staat wél per onderwerp in dit bestand**, in `HERKADER`. Dat is de
enige zin die niet uit de gids komt: hij draait de betekenis van *hen* naar
*jou*, en dat is redactiewerk. Zonder zo'n zin weigert dit script het onderwerp
- dezelfde regel als `PROMPTS` in `gids_beelden.py` en `BEWEGING` in
`gids_animaties.py`. Stil overslaan levert een Reel op met een gat op de plek
waar de wending hoort.

**Alle tekst staat bovenin**, om precies dezelfde reden als bij de
schermvullende gidsreels: het onderwerp van elk gidsbeeld staat op een grondlijn
in het onderste derde deel, en tekst daar botst met het beeld. Zie die sectie in
CLAUDE.md.
"""

import argparse
import importlib.util
import json
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
VOID, INK, ZACHT = reels.VOID, reels.INK, reels.ZACHT
SITE = reels.SITE

ONDERWERPEN = WORTEL / "knowledge" / "droomgids"
ANIMATIES = WORTEL / "data" / "gids-animatie-staand"
BEELDEN = WORTEL / "static" / "gids"
DOEL = WORTEL / "data" / "reels-inzicht"
MUZIEK = WORTEL / "data" / "muziek"

SECONDEN = 15
# De vier tellen, in seconden. Beat twee is met opzet de langste: daar staat de
# meeste tekst en die moet gelezen kunnen worden, niet gescand.
TELLEN = (2.0, 7.0, 3.0, 3.0)

# De wending per onderwerp - de enige zin die niet uit het artikel komt.
#
# Wat hij moet doen: de droom weghalen bij de ander en teruggeven aan de dromer.
# Niet "dit betekent X", want dat is de claim die dit product nooit maakt, maar
# "het gaat misschien niet over wie je denkt".
HERKADER = {
    "ex": {
        "en": "It may be about who you were back then.",
        "nl": "Misschien gaat het over wie jij toen was.",
    },
    "being-chased": {
        "en": "It may be less about what was behind you than what you keep ahead of.",
        "nl": "Misschien gaat het minder om wat achter je zat dan om wat je voorblijft.",
    },
    "baby": {
        "en": "It may be less about a child than about what depends on you.",
        "nl": "Misschien gaat het minder om een kind dan om wat van jou afhangt.",
    },
    "teeth-falling-out": {
        "en": "It may be less about your teeth than about what you were about to say.",
        "nl": "Misschien gaat het minder om je tanden dan om wat je wilde zeggen.",
    },
    "being-late": {
        "en": "It may be less about being late than about what kept getting in the way.",
        "nl": "Misschien gaat het minder om te laat zijn dan om wat er steeds tussen kwam.",
    },
    "snakes": {
        "en": "It may be less about the snake than about how calm you were.",
        "nl": "Misschien gaat het minder om de slang dan om hoe rustig jij was.",
    },
    "being-naked": {
        "en": "It may be less about being seen than about who actually noticed.",
        "nl": "Misschien gaat het minder om gezien worden dan om wie het opviel.",
    },
    "falling": {
        "en": "It may be less about falling than about whether you let go.",
        "nl": "Misschien gaat het minder om vallen dan om of je losliet.",
    },
    "water": {
        "en": "It may be less about the water than about where you were standing.",
        "nl": "Misschien gaat het minder om het water dan om waar jij stond.",
    },
    # Deze wending staat letterlijk in het artikel: "the position matters so
    # much - on its back, holding the reins, or standing in a field watching".
    "horse": {
        "en": "It may be less about the horse than about whether you were on it.",
        "nl": "Misschien gaat het minder om het paard dan om of jij erop zat.",
    },
}

# Een ander beeld dan de gidsanimatie, per onderwerp.
#
# Normaal is het beeld de animatie van dat gidsonderwerp - dan herkent iemand
# die doorklikt hetzelfde artikel. Bij `horse` staat er iets beters klaar: het
# shot uit `vera_vliegt.py` waarin Vera over het strand rijdt. Dat is tien
# seconden in plaats van vijf, het is het beeld met de meeste diepte van alles
# wat er ligt, en Vera zit er zelf op - wat precies is waar het artikel over
# gaat: zat je erop, of keek je ernaar.
#
# **Alleen doen als het echt beter is.** Elk onderwerp dat hier in komt te staan
# breekt de band tussen de Reel en de pagina een stukje verder, en dat was op
# 17 september een bewuste prijs en geen gewoonte.
EIGEN_BEELD = {
    "horse": WORTEL / "data" / "vera-vliegt" / "strand.mp4",
}

AFSLUITER = {
    "en": "Tell Vera what happened — link in bio.",
    "nl": "Vertel Vera wat er gebeurde — link in bio.",
}


def zinnen(tekst, hoeveel=2):
    """De eerste `hoeveel` zinnen, zonder ze af te kappen.

    Minstens twee, en dat is geen smaak: bij `dying` staat de ontkenning in de
    tweede zin. Zie de caption-regel in reels.py.
    """
    uit, rest = [], (tekst or "").strip()
    while rest and len(uit) < hoeveel:
        punt = rest.find(". ")
        if punt < 0:
            uit.append(rest.strip())
            break
        uit.append(rest[:punt + 1].strip())
        rest = rest[punt + 2:]
    return " ".join(uit)


def tekstlaag(regels_per_maat, punten_reeks, y_start, kleur, kap_tot):
    """Eén tekstblok bovenin, op een donkere kap die naar doorzichtig dooft."""
    laag = Image.new("RGBA", (BREEDTE, HOOGTE), (0, 0, 0, 0))
    kap = Image.new("RGBA", (BREEDTE, HOOGTE), VOID + (255,))
    kap.putalpha(reels.verloop(300, kap_tot, 205, 0))
    laag = Image.alpha_composite(laag, kap)

    tekenen = ImageDraw.Draw(laag)
    ruimte = BREEDTE - 2 * KANTLIJN
    for punten in punten_reeks:
        letter = reels.letter(regels_per_maat["letters"], punten)
        regels = []
        for stuk in regels_per_maat["tekst"].split("\n"):
            regels.extend(reels.omslaan(tekenen, stuk, letter, ruimte))
        if len(regels) <= regels_per_maat["max"]:
            break
    y = y_start
    for r in regels:
        tekenen.text((BREEDTE / 2, y), r, font=letter, fill=kleur, anchor="ma",
                     stroke_width=3, stroke_fill=VOID)
        y += round(punten * 1.24)
    return laag


KOP = ("georgiai.ttf", "Georgia Italic.ttf", "DejaVuSerif-Italic.ttf")
BODY = ("segoeui.ttf", "DejaVuSans.ttf")
VET = ("segoeuisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf")


def lagen(d, slug, taal):
    """De vier tekstlagen, in volgorde."""
    titel = reels.veld(d, "title", taal)
    # "Dreaming about an ex" -> "Dreaming about an ex?" ; de titel is al de haak.
    haak = titel.rstrip(".") + "?"
    inzicht = zinnen(reels.veld(d, "intro", taal), 2)
    wending = HERKADER[slug][taal]

    return [
        tekstlaag({"tekst": haak, "letters": KOP, "max": 3},
                  (92, 84, 74, 64), VEILIG_BOVEN + 60, INK, 940),
        # **`INK` en niet `ZACHT`, en de kap dieper.** Dit is de langste tekst
        # van de vier en dus de kwetsbaarste: bij `horse` (een strand bij
        # zonsopgang) viel de onderste regel over de lichte horizon en was hij
        # nauwelijks te lezen, terwijl hij bij `ex` (een donkere kamer) prima
        # stond. Een blok dat bij het ene beeld werkt en bij het andere niet is
        # hier geen blok dat werkt - zie *Leesbaar boven een bewegende
        # achtergrond* in CLAUDE.md.
        #
        # De kleur doet het werk en niet een waas over het beeld: fellere letters
        # met dezelfde contour, en de kap loopt dieper door omdat deze tekst
        # verder naar beneden komt dan de andere drie.
        tekstlaag({"tekst": inzicht, "letters": BODY, "max": 7},
                  (46, 42, 38, 34), VEILIG_BOVEN + 50, INK, 1260),
        tekstlaag({"tekst": wending, "letters": KOP, "max": 3},
                  (74, 66, 58, 52), VEILIG_BOVEN + 80, INK, 940),
        slot(taal),
    ]


def slot(taal):
    """De afsluiter, met het merk eronder.

    Het merk stond eerst op `VEILIG_BOVEN + 300` met een kap tot 1000, en dat
    was net te laag: daar is de kap al bijna doorzichtig, en bij een licht
    gidsbeeld - `ex` is een lichte kamer - staat lichtgrijze tekst dan op wit.
    Dezelfde fout als in *Leesbaar boven een bewegende achtergrond*, maar dan in
    een video.

    Twee dingen aangepast, en geen van beide is een waas over het beeld: de kap
    loopt dieper door (1240) en het blok schuift omhoog naar +230. De kleuren
    zijn ook een stap feller, want dit is de enige regel in de hele Reel die
    iemand moet kunnen overtypen.
    """
    laag = tekstlaag({"tekst": AFSLUITER[taal], "letters": BODY, "max": 3},
                     (52, 46, 42, 38), VEILIG_BOVEN + 80, INK, 1240)
    tekenen = ImageDraw.Draw(laag)
    klein = reels.letter(VET, 34)
    reels.gespreid(tekenen, "VERA DREAMVERSE", klein, BREEDTE / 2,
                   VEILIG_BOVEN + 230, (224, 216, 244), contour=3)
    adres = reels.letter(BODY, 32)
    tekenen.text((BREEDTE / 2, VEILIG_BOVEN + 286), SITE, font=adres,
                 fill=(212, 204, 234), anchor="ma",
                 stroke_width=3, stroke_fill=VOID)
    return laag


def beeldjes(pad, aantal):
    """Heen en terug, zodat vijf seconden animatie vijftien seconden vult."""
    lezer = imageio.get_reader(str(pad))
    try:
        ruw = [Image.fromarray(b).convert("RGB") for b in lezer]
    finally:
        lezer.close()
    if not ruw:
        raise SystemExit("{} bevat geen beeldjes.".format(pad.name))
    reeks = ruw + ruw[-2:0:-1] if len(ruw) > 1 else ruw
    return [reeks[i % len(reeks)] for i in range(aantal)]


def maak(d, slug, taal):
    DOEL.mkdir(parents=True, exist_ok=True)
    doel = DOEL / (slug + "-" + taal + ".mp4")
    bron = EIGEN_BEELD.get(slug) or (ANIMATIES / (slug + ".mp4"))
    if not bron.exists():
        raise SystemExit("Geen staande animatie voor {}.".format(slug))

    vier = lagen(d, slug, taal)
    totaal = int(FPS * SECONDEN)
    grenzen, op = [], 0.0
    for t in TELLEN:
        op += t
        grenzen.append(int(FPS * op))

    schrijver = imageio.get_writer(
        str(doel), fps=FPS, codec="libx264", macro_block_size=8,
        ffmpeg_params=["-crf", "21", "-profile:v", "high",
                       "-movflags", "+faststart"])
    try:
        for i, beeld in enumerate(beeldjes(bron, totaal)):
            welke = 0
            for n, g in enumerate(grenzen):
                if i < g:
                    welke = n
                    break
            else:
                welke = len(vier) - 1
            doek = reels._vullend(beeld).convert("RGBA")
            schrijver.append_data(
                np.asarray(Image.alpha_composite(doek, vier[welke]).convert("RGB")))
    finally:
        schrijver.close()
    return doel


def caption(d, slug, taal):
    titel = reels.veld(d, "title", taal)
    inzicht = zinnen(reels.veld(d, "intro", taal), 3)
    pad = ("" if taal == "en" else "/nl") + reels.BASIS.rstrip("/") + "/" + slug
    if taal == "nl":
        staart = ("De hele duiding staat op {}{} — link in bio.\n\n"
                  "#dromen #droombetekenis #droomuitleg #veradreamverse"
                  .format(SITE, pad))
    else:
        staart = ("Full reading on {}{} — link in bio.\n\n"
                  "#dreams #dreammeaning #dreaminterpretation #veradreamverse"
                  .format(SITE, pad))
    return "%s\n\n%s\n\n%s\n\n%s" % (titel, inzicht, HERKADER[slug][taal], staart)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slugs", nargs="*", help="welke onderwerpen")
    ap.add_argument("--taal", default="en", choices=("en", "nl"))
    ap.add_argument("--ja", action="store_true", help="echt maken")
    ap.add_argument("--nummer", default="mixkit-peace-487.mp3",
                    help="een ander nummer uit data/muziek/")
    ap.add_argument("--stil", action="store_true", help="zonder geluid")
    args = ap.parse_args()

    namen = args.slugs or sorted(HERKADER)
    zonder = [s for s in namen if s not in HERKADER]
    if zonder:
        print("Geen wending in HERKADER voor: %s" % ", ".join(zonder))
        print("Schrijf die eerst - dit script slaat een onderwerp niet stil over.")
        return 1

    print("%d Reel(s) van %d seconden, taal %s." % (len(namen), SECONDEN, args.taal))
    for slug in namen:
        d = json.loads((ONDERWERPEN / (slug + ".json")).read_text(encoding="utf-8"))
        print("\n  %s" % slug)
        for n, regel in enumerate(
                (reels.veld(d, "title", args.taal).rstrip(".") + "?",
                 zinnen(reels.veld(d, "intro", args.taal), 2),
                 HERKADER[slug][args.taal], AFSLUITER[args.taal]), 1):
            print("   %d. %s" % (n, regel[:96]))
    if not args.ja:
        print("\nNiets gedaan. Geef --ja mee.")
        return 0

    for slug in namen:
        d = json.loads((ONDERWERPEN / (slug + ".json")).read_text(encoding="utf-8"))
        doel = maak(d, slug, args.taal)
        if not args.stil:
            nummer = MUZIEK / args.nummer
            if not nummer.exists():
                print("Dat nummer staat niet in data/muziek/: %s" % args.nummer)
                return 1
            reels.geluid_eronder(doel, nummer, SECONDEN)
        tekst = DOEL / (slug + "-" + args.taal + ".txt")
        tekst.write_text(caption(d, slug, args.taal), encoding="utf-8")
        print("\n  %s  %.1f MB" % (doel.name, doel.stat().st_size / 1e6))
        print("  %s" % tekst.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
