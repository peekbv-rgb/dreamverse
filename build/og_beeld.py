"""Het plaatje dat bij de link hoort.

Zet iemand vera-dreamverse.com in zijn Instagram-bio, stuurt hij het adres in
een DM, of plakt hij het in WhatsApp of Slack, dan haalt die app `og:image` op
en zet daar een kaartje van. Staat er geen, dan is de link een grijze regel
tekst - en dan concurreert het mooiste stuk van dit product (het beeld) niet
mee op de plek waar mensen besluiten of ze klikken.

Eén vast beeld, geen beeld per droom: de landingspagina is voor iedereen
dezelfde en een droompaneel van gebruiker 1 hoort niet in andermans
voorvertoning. De vuurvogel is hetzelfde beeld dat op de landingspagina vooropstaat.

1200 bij 630 is de maat die Facebook, Instagram, WhatsApp, LinkedIn en Slack
allemaal aanhouden (1,91:1). Kleiner dan 600 breed laat Facebook het kaartje
klein en vierkant tonen, dus dit is de ondergrens niet maar de bovenkant van
wat nog overal past.

De tekst staat op een **eigen donkere grond**, niet als waas over het beeld:
dezelfde regel als in de app, want een voorvertoning wordt ook als duimnagel
van 200 pixels getoond en dan moet die regel het nog houden.

    python build/og_beeld.py [pad-naar-beeld]

Maakt static/og-beeld.jpg. Zonder argument wordt het volledige paneel uit
data/panels gebruikt als dat er ligt, en anders de poster uit
static/voorbeelden - die staat wél in git, dus dit is overal opnieuw te maken.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WORTEL = Path(__file__).resolve().parent.parent
DOEL = WORTEL / "static" / "og-beeld.jpg"

# Het volledige paneel is 1360 breed en dus scherper dan de poster van 720; die
# poster is de terugval, want data/ is git-ignored en verdwijnt bij een deploy.
SCHERP = WORTEL / "data" / "panels" / "1_6-1.png"
POSTER = WORTEL / "static" / "voorbeelden" / "vuurvogel.jpg"

BREEDTE, HOOGTE = 1200, 630
BAND = 210          # de donkere strook onderaan waar de tekst op staat
VOID = (8, 6, 15)   # --void uit style.css
INK = (242, 238, 251)
MUTED = (176, 164, 208)

# Er staat geen letternaam in de app; hier wel, want PIL kan niet terugvallen op
# een reeks zoals de browser dat doet. Dit zijn dezelfde twee letters die de
# DreamCard krijgt als Cormorant en Karla niet binnen zijn: een schreefletter
# voor wat je leest, een schreefloze voor het merk.
DISPLAY = ("georgiai.ttf", "Georgia Italic.ttf", "DejaVuSerif-Italic.ttf")
BODY = ("segoeuisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf")
FONTMAPPEN = (Path("C:/Windows/Fonts"), Path("/usr/share/fonts"),
              Path("/Library/Fonts"), Path.home() / "Library" / "Fonts")

TITEL = "Your dream, imagined"
REGEL = "VERA DREAMVERSE"
ADRES = "vera-dreamverse.com"


def letter(namen, punten):
    """De eerste letter die op deze machine te vinden is."""
    for map_ in FONTMAPPEN:
        if not map_.exists():
            continue
        for naam in namen:
            for pad in [map_ / naam] + list(map_.rglob(naam)):
                if pad.exists():
                    return ImageFont.truetype(str(pad), punten)
    raise SystemExit(
        "Geen letter gevonden ({}). Zet er een neer of pas FONTMAPPEN aan."
        .format(", ".join(namen)))


def vullend(im, breedte, hoogte):
    """Vullend uitsnijden, met het midden van het beeld als middelpunt."""
    schaal = max(breedte / im.width, hoogte / im.height)
    groot = im.resize((round(im.width * schaal), round(im.height * schaal)),
                      Image.LANCZOS)
    x = (groot.width - breedte) // 2
    y = (groot.height - hoogte) // 2
    return groot.crop((x, y, x + breedte, y + hoogte))


def maak(bron):
    kaart = Image.new("RGB", (BREEDTE, HOOGTE), VOID)

    # Het beeld vult de hele kaart; de band eronder ligt eroverheen. Zo blijft er
    # beeld achter de tekst zichtbaar in de overgang en plakt de strook niet als
    # een balk op de foto.
    kaart.paste(vullend(Image.open(bron).convert("RGB"), BREEDTE, HOOGTE))

    # De band: dekkend genoeg om de tekst te dragen (dezelfde .92 als in de app)
    # en met een verloop erboven zodat het beeld erin wegzakt.
    laag = Image.new("RGBA", (BREEDTE, HOOGTE), (0, 0, 0, 0))
    tekenen = ImageDraw.Draw(laag)
    boven = HOOGTE - BAND
    for i in range(90):
        deel = i / 89
        tekenen.rectangle([0, boven - 90 + i, BREEDTE, boven - 90 + i + 1],
                          fill=VOID + (round(235 * deel),))
    tekenen.rectangle([0, boven, BREEDTE, HOOGTE], fill=VOID + (235,))
    kaart = Image.alpha_composite(kaart.convert("RGBA"), laag).convert("RGB")

    tekenen = ImageDraw.Draw(kaart)
    tekenen.text((72, boven + 42), TITEL, font=letter(DISPLAY, 62), fill=INK)
    klein = letter(BODY, 24)
    tekenen.text((74, boven + 132), REGEL, font=klein, fill=MUTED)
    x = 74 + tekenen.textlength(REGEL, font=klein)
    tekenen.text((x + 18, boven + 132), "\u00b7  " + ADRES, font=klein,
                 fill=(140, 128, 170))

    # Kwaliteit 88: een voorvertoning wordt zelden groter dan 600 pixels getoond,
    # en elke honderd kB kost tijd bij de eerste keer dat een app hem ophaalt.
    kaart.save(DOEL, "JPEG", quality=88, optimize=True)
    return DOEL


def main():
    if len(sys.argv) > 1:
        bron = Path(sys.argv[1])
    else:
        bron = SCHERP if SCHERP.exists() else POSTER
    if not bron.exists():
        raise SystemExit("Bron niet gevonden: {}".format(bron))
    pad = maak(bron)
    print("%s  %d x %d  %.0f kB  (uit %s)" % (
        pad.relative_to(WORTEL), BREEDTE, HOOGTE,
        pad.stat().st_size / 1000, bron.name))
    print("Vergeet de tags niet: og:image staat in welkom.html en index.html.")


if __name__ == "__main__":
    main()
