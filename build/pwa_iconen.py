"""De iconen voor het beginscherm maken.

Zet iemand Dreamverse op zijn telefoon, dan is dit het enige wat hij van de app
ziet als hij hem niet open heeft. De chakrapilaar is daarvoor het juiste beeld:
zeven lotussen in een lichtbundel is op 48 pixels nog herkenbaar, en het is het
deel van de app waar mensen voor terugkomen. Vera's portret wordt op dat formaat
een vlek.

De bron is staand (576 x 1008) en een icoon is vierkant. We schalen op hoogte en
snijden de zijkanten weg, zodat de pilaar in het midden blijft staan.

    python build/pwa_iconen.py

Maakt static/icoon-192.png, static/icoon-512.png, static/icoon-maskable.png en
static/apple-touch-icon.png. Draai dit opnieuw als de plaat verandert.
"""

from pathlib import Path

from PIL import Image

WORTEL = Path(__file__).resolve().parent.parent
BRON = WORTEL / "static" / "chakra-pilaar.jpg"
VOID = (10, 7, 20)  # --void uit style.css, zodat het icoon bij de app past


def vierkant(bron, zijde, marge=0.0):
    """Een vierkant icoon van de staande plaat.

    `marge` is de fractie van het icoon die rondom leeg blijft. Android snijdt
    bij een maskable icoon tot 20% weg aan elke kant; met marge blijft de pilaar
    dan heel.
    """
    doek = Image.new("RGB", (zijde, zijde), VOID)
    binnen = int(zijde * (1 - 2 * marge))

    # Op hoogte schalen en de zijkanten wegsnijden: de pilaar staat midden.
    schaal = binnen / bron.height
    nieuw = bron.resize((max(1, round(bron.width * schaal)), binnen), Image.LANCZOS)
    links = max(0, (nieuw.width - binnen) // 2)
    uitsnede = nieuw.crop((links, 0, links + binnen, binnen))

    doek.paste(uitsnede, (int(zijde * marge), int(zijde * marge)))
    return doek


def main():
    if not BRON.exists():
        print("De bronplaat ontbreekt: %s" % BRON)
        return 1
    bron = Image.open(BRON).convert("RGB")

    werk = [
        ("icoon-192.png", 192, 0.0),
        ("icoon-512.png", 512, 0.0),
        # Maskable: Android knipt er een vorm uit, dus ruimte rondom laten.
        ("icoon-maskable.png", 512, 0.14),
        # iOS zet er zelf de ronde hoeken op en wil geen transparantie.
        ("apple-touch-icon.png", 180, 0.0),
    ]
    for naam, zijde, marge in werk:
        doel = WORTEL / "static" / naam
        vierkant(bron, zijde, marge).save(doel, "PNG", optimize=True)
        print("%-24s %4d x %-4d  %5.0f kB" % (naam, zijde, zijde,
                                              doel.stat().st_size / 1000))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
