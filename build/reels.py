"""Van een gidsonderwerp een Reel maken: staand, met tekst, met beweging.

Er liggen zevenentwintig onderwerpen met elk een beeld en een uitgeschreven
tekst. Dat is bijna vier weken dagelijks posten zonder dat er nog iets bedacht
hoeft te worden - en het is de enige inhoud die dit account heeft en niemand
anders.

    python build/reels.py --ja                    # de video's, nog zonder geluid
    python build/reels.py --verdeel --ja          # de muziek eronder
    python build/reels.py --ja snakes falling     # een paar
    python build/reels.py --ja --taal nl          # Nederlandse tekst
    python build/reels.py --check                 # wat er gemaakt zou worden

In `data/reels/` staat wat je post: `<slug>.mp4` (1080 x 1920, 8 seconden, mét
muziek) en `<slug>.txt` met de caption ernaast. In `data/reels/stil/` staat
hetzelfde beeld zonder geluid; dat is de werkmap waar de muziekstap uit leest.

Vier dingen die hier bewust zo zijn.

**Staand, en niet het liggende gidsbeeld opgerekt.** Alles wat de app maakt is
16:9 en Instagram is 9:16. Een liggend beeld dat je vult door in te zoomen
verliest driekwart van zijn compositie, dus gaat het beeld in een kader midden
op een donkere grond - dezelfde vorm als de DreamCard, en om dezelfde reden.

**De onderste 420 pixels blijven leeg.** Bij een Reel legt Instagram daar de
caption, de audioregel en de knoppen over je beeld; aan de rechterkant staan de
knoppen voor liken en delen. Daarom staat alles tussen 285 en 1500, en niets
tegen de rechterrand. Dat is strenger dan de 285/1635 van de DreamCard, want een
verhaal en een Reel bedekken niet hetzelfde.

**Beweging zonder een beeldmodel.** Een langzame zoom over een stilstaand beeld
is genoeg om het levend te laten lijken, en kost niets. Een echte animatie bij
Runway is € 0,55 tot € 1,47 per stuk - dat is € 15 tot € 40 voor deze set, en
voor een beeld dat acht seconden in beeld staat koopt die zoom hetzelfde effect.

**Geen geluid.** Muziek uit de bibliotheek van Instagram mag je alleen in
Instagram zelf toevoegen; dat is precies waar die licentie voor geldt. Dus komt
de video er stil uit en kies je het muziekje bij het plaatsen. Een eigen
muziekbestand eronder plakken kan technisch wel, maar dan draait je Reel niet
mee in de zoekresultaten op dat nummer - en dat is juist waar het bereik zit.
"""

import argparse
import json
import sys
import textwrap
from pathlib import Path

import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WORTEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from og_beeld import letter  # noqa: E402  - dezelfde letterzoeker als het og-beeld

ONDERWERPEN = WORTEL / "knowledge" / "droomgids"
BEELDEN = WORTEL / "static" / "gids"
DOEL = WORTEL / "data" / "reels"

# De stille versies staan een niveau dieper, en dat is met opzet omgedraaid.
#
# Eerst stond de bron in `data/reels/` en kwam het resultaat met muziek in
# `data/reels/muziek/`. Logisch vanuit het script, maar verkeerd vanuit de map:
# wie de bovenste map opende pakte de versie die hij níet wil hebben, en de
# goede zat een niveau dieper. Nu staat in `data/reels/` wat je post - video mét
# muziek, plus de caption ernaast - en is `stil/` de werkmap.
STIL = DOEL / "stil"
# De animaties uit build/gids_animaties.py. Is er geen bestand voor een
# onderwerp, dan valt maak() terug op de zoom over het stilstaande beeld.
ANIMATIES = DOEL.parent / "gids-animatie"

BREEDTE, HOOGTE = 1080, 1920
FPS, SECONDEN = 30, 8

# De strook waar Instagram zijn eigen bediening over je beeld legt.
VEILIG_BOVEN, VEILIG_ONDER = 285, 1500
KANTLIJN = 96                      # tekst nooit tegen de rand, ook niet rechts

# Waar het gidsbeeld staat: 960 x 600.
#
# Die verhouding is een afweging. Het gidsbeeld is 16:9, want zo is het
# gecomponeerd en zo staat het op de gidspagina. Een kader van 960 x 680 snijdt
# er 29% van de zijkanten af - bij `spiders` valt dan de helft van het web weg.
# Op 960 x 600 is dat nog 10%, en het staat rechtop genoeg om geen filmbalk te
# lijken.
VAK = (60, 570, BREEDTE - 60, 1170)
ZOOM = 1.12                            # van 1,00 naar 1,12 over acht seconden

VOID = (8, 6, 15)
INK = (242, 238, 251)
ZACHT = (206, 196, 228)
MERK = (167, 154, 203)

SITE = "vera-dreamverse.com"
BASIS = "/dream-meaning/"

MUZIEKMAP = WORTEL / "data" / "muziek"

# Welk nummer onder welk onderwerp, en dat is een redactionele keuze en geen
# techniek.
#
# Eén nummer onder alle zevenentwintig klinkt als één account, maar dan staat er
# ook een beat van 130 onder "dromen over iemand die overleden is" - en dat leest
# als ongevoelig. Dus vier stemmingen, met het rustige stuk onder alles wat over
# verlies, lichaam of verraad gaat.
#
# `rustig` is met opzet ruim genomen: bij twijfel het rustige nummer. Een te
# kalme track onder een lichte droom valt niemand op; het omgekeerde wel.
MUZIEK = {
    "rustig": "mixkit-peace-487.mp3",
    "midden": "mixkit-hazy-after-hours-132.mp3",
    "licht": "mixkit-house-vibes-129.mp3",
    "puls": "mixkit-deep-techno-ambience-134.mp3",
}

STEMMING = {
    # Verlies, lichaam, verraad, en het tedere.
    "rustig": ("dying", "deceased-person", "pregnancy", "mother", "ex",
               "cheating", "baby"),
    # Onrustig of raadselachtig: het beeld doet het werk, de muziek draagt.
    "midden": ("being-chased", "cant-move", "being-naked", "teeth-falling-out",
               "snakes", "spiders", "stranger", "getting-lost", "water",
               "house"),
    # Beweging en dieren: hier mag energie bij.
    "licht": ("flying", "birds", "falling", "horse", "dogs", "cat"),
    # Alledaags en stedelijk.
    "puls": ("fire", "car", "school", "being-late"),
}


def stemming_van(slug):
    for naam, slugs in STEMMING.items():
        if slug in slugs:
            return naam
    # Onbekend onderwerp: het rustige nummer. Bij twijfel niet de beat.
    return "rustig"


def veld(d, sleutel, taal):
    """Het veld in de gevraagde taal, met het Engels als terugval."""
    if taal != "en":
        blok = d.get(taal) or {}
        if blok.get(sleutel):
            return blok[sleutel]
    return d.get(sleutel, "")


def omslaan(tekenen, tekst, font, breedte):
    """Regels die binnen `breedte` passen."""
    woorden = tekst.split()
    regels, regel = [], ""
    for w in woorden:
        proef = (regel + " " + w).strip()
        if tekenen.textlength(proef, font=font) <= breedte or not regel:
            regel = proef
        else:
            regels.append(regel)
            regel = w
    if regel:
        regels.append(regel)
    return regels


def gespreid(tekenen, tekst, font, midden, y, kleur, spatie=6, contour=0):
    """Tekst met ruimte tussen de letters. PIL kent geen letter-spacing, en het
    merk hoort er net zo uit te zien als op de DreamCard.

    `contour` zet er een donkere rand omheen, voor de schermvullende Reel waar
    deze regel op het beeld ligt in plaats van op een donkere grond."""
    breedtes = [tekenen.textlength(c, font=font) for c in tekst]
    totaal = sum(breedtes) + spatie * (len(tekst) - 1)
    x = midden - totaal / 2
    for c, b in zip(tekst, breedtes):
        if contour:
            tekenen.text((x, y), c, font=font, fill=kleur,
                         stroke_width=contour, stroke_fill=VOID)
        else:
            tekenen.text((x, y), c, font=font, fill=kleur)
        x += b + spatie


def achtergrond(titel, vraag, link):
    """De vaste laag: grond, gloed, en alle tekst. Het beeld komt er per frame in."""
    kaart = Image.new("RGB", (BREEDTE, HOOGTE), VOID)

    # Een violette gloed achter het kader, zodat het beeld niet als een
    # postzegel op zwart ligt.
    gloed = Image.new("RGB", (BREEDTE, HOOGTE), VOID)
    tek = ImageDraw.Draw(gloed)
    midden_y = (VAK[1] + VAK[3]) // 2
    for i in range(120, 0, -1):
        deel = i / 120
        straal = int(BREEDTE * 0.95 * deel)
        kleur = (int(8 + 46 * (1 - deel)), int(6 + 38 * (1 - deel)),
                 int(15 + 92 * (1 - deel)))
        tek.ellipse([BREEDTE // 2 - straal, midden_y - straal,
                     BREEDTE // 2 + straal, midden_y + straal], fill=kleur)
    kaart = Image.blend(kaart, gloed, 0.85)

    tekenen = ImageDraw.Draw(kaart)
    ruimte = BREEDTE - 2 * KANTLIJN

    # De titel boven het beeld, in maximaal twee regels: bij drie schuift hij de
    # veilige strook in.
    #
    # Past hij niet, dan wordt de letter kleiner en niet de tekst korter. Er
    # stond eerst `[:2]`, en dan verliest "Dreaming about being naked in public"
    # zijn laatste woorden zonder dat iets het meldt - precies het soort fout
    # waar je pas achter komt als het al op Instagram staat.
    for punten in (84, 76, 68, 60, 54):
        kop = letter(("georgiai.ttf", "Georgia Italic.ttf",
                      "DejaVuSerif-Italic.ttf"), punten)
        regels = omslaan(tekenen, titel, kop, ruimte)
        if len(regels) <= 2:
            break
    hoog = round(punten * 1.14)
    y = VAK[1] - 60 - len(regels) * hoog
    for r in regels:
        tekenen.text((BREEDTE / 2, y), r, font=kop, fill=INK, anchor="ma")
        y += hoog

    # De vraag onder het beeld: dit is wat iemand aan het denken zet, en het is
    # dezelfde regel die op de kaart in de gids staat.
    # Ook hier kleiner in plaats van korter, met drie regels als bovengrens.
    for punten in (44, 40, 36, 32):
        body = letter(("segoeui.ttf", "DejaVuSans.ttf"), punten)
        regels = omslaan(tekenen, vraag, body, ruimte)
        if len(regels) <= 3:
            break
    y = VAK[3] + 70
    for r in regels:
        tekenen.text((BREEDTE / 2, y), r, font=body, fill=ZACHT, anchor="ma")
        y += round(punten * 1.32)

    # Onderaan de weg naar de gids, en niet het merk.
    #
    # Op de DreamCard staat VERA DREAMVERSE met het domein eronder, want die
    # kaart is de advertentie. Hier is het beeld de advertentie en is de vraag
    # net gesteld; wat er dan hoort te staan is waar het antwoord ligt. De naam
    # zit er trouwens nog in - het heet Vera's Dream Guide.
    #
    # Het overzichtsadres en niet de diepe link naar dit onderwerp: dat laatste
    # is drieënveertig tekens die niemand overtypt, en op het overzicht staat
    # het onderwerp één tik verderop. De diepe link staat wél in de caption.
    # Aanklikbaar is geen van beide - dat kan bij Instagram alleen vanuit je bio
    # of met een sticker in een verhaal.
    klein = letter(("segoeuisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"), 32)
    gespreid(tekenen, "VERA'S DREAM GUIDE", klein, BREEDTE / 2,
             VEILIG_ONDER - 96, MERK)
    adres = letter(("segoeui.ttf", "DejaVuSans.ttf"), 30)
    tekenen.text((BREEDTE / 2, VEILIG_ONDER - 44), SITE + link, font=adres,
                 fill=(150, 138, 182), anchor="ma")
    return kaart


# De staande animaties uit `build/gids_animaties.py --staand`.
ANIMATIES_STAAND = DOEL.parent / "gids-animatie-staand"

# Gezet door main(); maak() leest hem.
STAAND = False


def verloop(van_y, tot_y, van_alfa, tot_alfa):
    """Een verticaal verloop als alfamasker, van boven naar beneden."""
    m = Image.new("L", (BREEDTE, HOOGTE), 0)
    tek = ImageDraw.Draw(m)
    hoogte = max(tot_y - van_y, 1)
    for y in range(van_y, tot_y):
        deel = (y - van_y) / hoogte
        tek.line([(0, y), (BREEDTE, y)],
                 fill=int(van_alfa + (tot_alfa - van_alfa) * deel))
    # Alles buiten het verloop houdt de eindwaarde vast, anders komt er een
    # harde rand waar het masker ophoudt.
    if van_y > 0 and van_alfa:
        tek.rectangle([0, 0, BREEDTE, van_y], fill=van_alfa)
    if tot_y < HOOGTE and tot_alfa:
        tek.rectangle([0, tot_y, BREEDTE, HOOGTE], fill=tot_alfa)
    return m


def overlaag_staand(titel, vraag, link):
    """De tekstlaag voor een schermvullende Reel, met doorzichtige achtergrond.

    Bij de gekaderde versie staat alle tekst op een donkere grond en is
    leesbaarheid gratis. Hier ligt ze op het beeld, en dan is ze soms leesbaar
    en soms niet - en "soms" bestaat hier niet als eis, net als in de app. Dus
    twee verlopen: een donkere kap bovenaan achter de titel en een donkere voet
    onderaan achter de vraag en het merk. Het beeld blijft in het midden
    onaangeroerd, en dat is precies het stuk waar de beweging zit.

    Geen egale waas over het hele beeld: dat dooft de kleuren die de hele reden
    zijn om schermvullend te gaan.
    """
    laag = Image.new("RGBA", (BREEDTE, HOOGTE), (0, 0, 0, 0))

    # Leesbaarheid komt van de contour om de letters, niet van het verloop.
    #
    # Dat is in twee stappen geleerd. De eerste versie had zachte verlopen en
    # las prima op het slangenbeeld - en dat was precies het probleem: waar de
    # vraag begint (rond y=1234) zat het verloop op alfa 77, dertig procent
    # dekking. Bij een donker beeld valt dat niet op; bij `fire`, `flying` of
    # een lichte ochtendlucht staat er witte tekst op wit. "Leesbaar bij dit
    # beeld" is niet hetzelfde als leesbaar bij alle drieënveertig.
    #
    # De tweede versie maakte de verlopen vol en dekkend tot voorbij de tekst.
    # Toen was de tekst overal leesbaar en was het beeld gedoofd - en die
    # kleuren zijn de hele reden om schermvullend te gaan. Twee keer de
    # verkeerde knop.
    #
    # De goede knop is de tekst zelf: een donkere contour van drie pixels om
    # witte letters is leesbaar op vrijwel alles, en raakt het beeld nergens
    # anders aan. Zo doen ondertitels het ook. De verlopen blijven, maar nu
    # alleen om boven- en onderkant van het midden te scheiden - niet om het
    # werk te doen.
    kap = Image.new("RGBA", (BREEDTE, HOOGTE), VOID + (255,))
    kap.putalpha(verloop(340, 900, 186, 0))
    laag = Image.alpha_composite(laag, kap)

    # Onder: begint op 820 en is vol op 1240, ruim voordat de vraag begint.
    # Daaronder blijft hij vol - dat kost niets, want alles beneden 1500 ligt
    # toch onder de bediening van Instagram.
    voet = Image.new("RGBA", (BREEDTE, HOOGTE), VOID + (255,))
    voet.putalpha(verloop(980, 1300, 0, 196))
    laag = Image.alpha_composite(laag, voet)

    tekenen = ImageDraw.Draw(laag)
    ruimte = BREEDTE - 2 * KANTLIJN

    # De titel binnen de veilige strook. Kleiner in plaats van korter, net als
    # in de gekaderde versie: een afgekapte titel merk je pas op Instagram.
    for punten in (84, 76, 68, 60, 54):
        kop = letter(("georgiai.ttf", "Georgia Italic.ttf",
                      "DejaVuSerif-Italic.ttf"), punten)
        regels = omslaan(tekenen, titel, kop, ruimte)
        if len(regels) <= 3:
            break
    hoog = round(punten * 1.14)
    y = VEILIG_BOVEN + 40
    for r in regels:
        tekenen.text((BREEDTE / 2, y), r, font=kop, fill=INK, anchor="ma",
                     stroke_width=3, stroke_fill=VOID)
        y += hoog

    # De vraag onderaan, boven het merk. Van onderen naar boven opgebouwd,
    # zodat een vraag van drie regels het merk niet wegduwt.
    for punten in (44, 40, 36, 32):
        body = letter(("segoeui.ttf", "DejaVuSans.ttf"), punten)
        regels = omslaan(tekenen, vraag, body, ruimte)
        if len(regels) <= 3:
            break
    regelhoog = round(punten * 1.32)
    y = VEILIG_ONDER - 150 - len(regels) * regelhoog
    for r in regels:
        tekenen.text((BREEDTE / 2, y), r, font=body, fill=ZACHT, anchor="ma",
                     stroke_width=3, stroke_fill=VOID)
        y += regelhoog

    klein = letter(("segoeuisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"), 32)
    gespreid(tekenen, "VERA'S DREAM GUIDE", klein, BREEDTE / 2,
             VEILIG_ONDER - 96, (196, 186, 224), contour=2)
    adres = letter(("segoeui.ttf", "DejaVuSans.ttf"), 30)
    tekenen.text((BREEDTE / 2, VEILIG_ONDER - 44), SITE + link, font=adres,
                 fill=(178, 168, 204), anchor="ma",
                 stroke_width=2, stroke_fill=VOID)
    return laag


def _vullend(beeld):
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


def frames_staand(pad, titel, vraag, link):
    """Elk beeldje van de staande animatie, schermvullend, met de tekst erover.

    Heen en terug, om dezelfde reden als bij de gekaderde versie: de animatie is
    vijf seconden en de Reel acht, en herhalen geeft een sprong op het naadje.
    """
    laag = overlaag_staand(titel, vraag, link)

    lezer = imageio.get_reader(str(pad))
    try:
        ruw = [Image.fromarray(b).convert("RGB") for b in lezer]
    finally:
        lezer.close()
    if not ruw:
        raise SystemExit("De animatie {} bevat geen beeldjes.".format(pad.name))

    reeks = ruw + ruw[-2:0:-1]
    totaal = FPS * SECONDEN
    for i in range(totaal):
        doek = _vullend(reeks[i % len(reeks)]).convert("RGBA")
        yield np.asarray(Image.alpha_composite(doek, laag).convert("RGB"))


def masker(breedte, hoogte, hoek=36):
    m = Image.new("L", (breedte, hoogte), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, breedte - 1, hoogte - 1],
                                        radius=hoek, fill=255)
    return m


def _binnen_kader(beeld, vak_b, vak_h, schaal=1.0):
    """Het grootste stuk uit het midden, in de verhouding van het kader."""
    verhouding = vak_b / vak_h
    if beeld.width / beeld.height > verhouding:
        h = beeld.height
        b = round(h * verhouding)
    else:
        b = beeld.width
        h = round(b / verhouding)
    snee_b, snee_h = round(b / schaal), round(h / schaal)
    x = (beeld.width - snee_b) // 2
    y = (beeld.height - snee_h) // 2
    return beeld.crop((x, y, x + snee_b, y + snee_h)).resize(
        (vak_b, vak_h), Image.LANCZOS)


def frames(bron, titel, vraag, link):
    """Elk beeldje: de vaste laag met het ingezoomde beeld erin.

    Dit is de terugval. Zie `frames_uit_animatie` voor wat er gebeurt als het
    onderwerp een echte animatie heeft.
    """
    grond = achtergrond(titel, vraag, link)
    vak_b, vak_h = VAK[2] - VAK[0], VAK[3] - VAK[1]
    vorm = masker(vak_b, vak_h)
    beeld = Image.open(bron).convert("RGB")

    totaal = FPS * SECONDEN
    for i in range(totaal):
        deel = i / max(totaal - 1, 1)
        stuk = _binnen_kader(beeld, vak_b, vak_h, 1 + (ZOOM - 1) * deel)
        doek = grond.copy()
        doek.paste(stuk, (VAK[0], VAK[1]), vorm)
        yield np.asarray(doek)


def frames_uit_animatie(pad, titel, vraag, link):
    """Elk beeldje uit de Kling-animatie, in hetzelfde kader.

    De animatie is vijf seconden en de Reel acht. Dat gat vullen kan op drie
    manieren, en twee daarvan zijn zichtbaar: herhalen geeft een sprong op het
    naadje, en het laatste beeldje vasthouden geeft drie seconden stilstand
    precies wanneer de kijker nog kijkt.

    Dus **heen en terug**. Een clip die vooruit loopt en daarna achteruit is aan
    het keerpunt naadloos - de beweging is traag en omkeerbaar (mist die drijft,
    water dat rimpelt, licht dat verschuift), dus achteruit ziet er niet
    achteruit uit. Vijf seconden heen en terug is tien, en daar knippen we er
    acht uit; het keerpunt valt dan op vijf seconden en niemand ziet het.
    """
    grond = achtergrond(titel, vraag, link)
    vak_b, vak_h = VAK[2] - VAK[0], VAK[3] - VAK[1]
    vorm = masker(vak_b, vak_h)

    lezer = imageio.get_reader(str(pad))
    try:
        ruw = [Image.fromarray(b).convert("RGB") for b in lezer]
    finally:
        lezer.close()
    if not ruw:
        raise SystemExit("De animatie {} bevat geen beeldjes.".format(pad.name))

    # Heen en terug, zonder het eerste en laatste beeldje te verdubbelen.
    reeks = ruw + ruw[-2:0:-1]
    totaal = FPS * SECONDEN
    for i in range(totaal):
        # Modulo, zodat een kortere animatie dan verwacht nooit een IndexError
        # geeft maar gewoon nog een keer heen en terug gaat.
        beeld = reeks[i % len(reeks)]
        doek = grond.copy()
        doek.paste(_binnen_kader(beeld, vak_b, vak_h), (VAK[0], VAK[1]), vorm)
        yield np.asarray(doek)


# Instagram kapt een caption af op 2200 tekens. Daar zitten we ruim onder, maar
# `main()` waarschuwt als een onderwerp erboven komt - afgekapt betekent hier dat
# de link en de hashtags wegvallen, en dat zijn precies de twee dingen die werk
# moeten doen.
CAPTION_MAX = 2200

LENS_KOP = {
    "en": (("psychological", "Psychologically"), ("symbolic", "Symbolically"),
           ("spiritual", "Spiritually")),
    "nl": (("psychological", "Psychologisch"), ("symbolic", "Symbolisch"),
           ("spiritual", "Spiritueel")),
}

# Vaste tags naast de tags van het onderwerp zelf. Tien à twaalf is genoeg;
# Instagram staat er dertig toe maar een muur van tags leest als spam.
TAGS_VAST = {
    "en": ("dreams", "dreammeaning", "dreaminterpretation", "dreamsymbols",
           "dreamjournal", "veradreamverse"),
    "nl": ("dromen", "droombetekenis", "droomuitleg", "droomsymbolen",
           "droomdagboek", "veradreamverse"),
}


def eerste_zinnen(tekst, minimaal=2, tekens=300):
    """De opening van een stuk: hele zinnen, tot ongeveer `tekens`.

    Minimaal twee, en dat is geen smaak. Bij *dying* staat de ontkenning in de
    **tweede** zin - "a dream about dying carries no information about anybody's
    health, safety or lifespan" - en een caption over dromen over doodgaan die
    daar niet mee opent, hoort niet op Instagram. Bij *pregnancy* staat hij in de
    eerste. Eén zin pakken zou dus per onderwerp verschillen, en juist bij deze
    twee mag dat niet.
    """
    stukken = [z.strip() for z in tekst.replace("? ", "?|").replace(". ", ".|")
               .split("|") if z.strip()]
    uit = []
    for z in stukken:
        uit.append(z)
        if len(uit) >= minimaal and len(" ".join(uit)) >= tekens:
            break
    return " ".join(uit)


def hashtags(d, taal):
    """Tags van het onderwerp, dan de vaste.

    De eerste komen uit `slug` en uit `also` - dat veld bestaat al voor de
    zoekwoorden van de gids, en dat zijn precies de woorden waarop iemand op
    Instagram ook zoekt.
    """
    # De slug plus hoogstens twee uit `also`, en dat is met opzet weinig.
    #
    # `also` staat er voor de zoekwoorden van de gids, en die zijn voor Google
    # geschreven. Als zoekvraag is "someone I love dying" volkomen normaal; als
    # hashtag onder een post is het iets anders, en Instagram beperkt de
    # zichtbaarheid van een deel van dat soort tags - dan verdwijnt je hele post
    # in stilte. Welke tags dat zijn kan ik hier niet nakijken, dus houden we het
    # klein en doen de vaste tags het werk. **Kijk bij `dying` en
    # `deceased-person` altijd zelf naar de tags voordat je plaatst.**
    ruw = [d["slug"]] + list(d.get("also") or [])[:2]
    tags, gezien = [], set()
    for woord in ruw:
        t = "".join(c for c in woord.lower() if c.isalnum())
        if t and t not in gezien:
            gezien.add(t)
            tags.append(t)
    for t in TAGS_VAST.get(taal, TAGS_VAST["en"]):
        if t not in gezien:
            gezien.add(t)
            tags.append(t)
    return " ".join("#" + t for t in tags[:12])


def caption(d, taal):
    """De tekst die eronder komt.

    Een link in een caption is bij Instagram niet aanklikbaar - alleen de link in
    je bio en een sticker in een verhaal zijn dat. Dus staat het adres er wel,
    maar met "link in bio" erbij, want dat is de weg die werkt.
    """
    titel = veld(d, "title", taal)
    vera = veld(d, "vera", taal)
    vragen = (veld(d, "details", taal) or [])[:3]
    pad = ("" if taal == "en" else "/nl") + BASIS + d["slug"]

    if taal == "nl":
        woorden = ["Wat de tradities en de psychologie erover zeggen:",
                   "En dan kantelen de details alles:",
                   "De hele duiding staat op {}{} — link in bio.".format(SITE, pad),
                   "Vertel je eigen droom aan Vera en je krijgt hem terug als "
                   "vijf panelen, met een duiding."]
    else:
        woorden = ["What tradition and psychology make of it:",
                   "And then the details change everything:",
                   "Full reading on {}{} — link in bio.".format(SITE, pad),
                   "Tell Vera your own dream and get it back as five panels, "
                   "with a reading."]

    # Vera's regel is de haak, dan de opening van het artikel, dan de drie
    # brillen in één regel elk. Niet het hele artikel: dat staat op de pagina en
    # daar willen we mensen juist naartoe hebben.
    stukken = [titel, "", vera, "", eerste_zinnen(veld(d, "intro", taal)), "",
               woorden[0]]
    brillen = d.get("perspectives") or {}
    nl_brillen = (d.get(taal) or {}).get("perspectives") or {}
    for sleutel, kop in LENS_KOP.get(taal, LENS_KOP["en"]):
        tekst = nl_brillen.get(sleutel) or brillen.get(sleutel) or ""
        if tekst:
            stukken.append("{}: {}".format(kop, eerste_zinnen(tekst, 1, 0)))
    stukken += ["", woorden[1]]
    stukken += ["• " + v for v in vragen]
    stukken += ["", woorden[2], "", woorden[3], "", hashtags(d, taal)]
    return "\n".join(stukken).strip() + "\n"


def beste_start(muziek, stappen=(0, 8, 16, 24, 32, 40, 48)):
    """Waar in het nummer het stuk van acht seconden begonnen moet worden.

    Bijna elk nummer begint met een kale opbouw en gaat pas na een halve minuut
    open. `mixkit-peace` staat de eerste dertig seconden op -21 dB en daarna op
    -9 - dat is geen nuance maar een ander nummer. Bij acht seconden video wil je
    het stuk waar de arrangement al staat, anders lijkt het alsof er geen muziek
    onder zit.

    Dus meten in plaats van gokken: het eerste venster dat binnen anderhalve
    decibel van het luidste zit. Het eerste en niet het luidste, want verderop in
    een nummer zit vaak een climax die onder een rustig beeld te veel is.
    """
    import re
    import subprocess
    import imageio_ffmpeg

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    gemeten = []
    for start in stappen:
        r = subprocess.run(
            [ff, "-hide_banner", "-ss", str(start), "-t", str(SECONDEN),
             "-i", str(muziek), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, errors="replace")
        m = re.search(r"mean_volume: (-?[\d.]+)", r.stderr)
        if m:
            gemeten.append((start, float(m.group(1))))
    if not gemeten:
        return 20.0
    luidst = max(v for _, v in gemeten)
    for start, v in gemeten:
        if v >= luidst - 1.5:
            return float(start)
    return float(gemeten[0][0])


def muziek_eronder(slug, muziek, vanaf=20.0, luider=-3.0):
    """Een muziekstuk onder een al gemaakte Reel.

    Dit is een aparte stap en geen onderdeel van het renderen, om twee redenen.
    De stille versie blijft de bron - een ander nummer proberen kost dan geen
    nieuwe render maar een paar seconden. En het beeld wordt hier niet opnieuw
    gecodeerd (`-c:v copy`), dus er gaat geen kwaliteit verloren en het is klaar
    voor je het gezien hebt.

    `vanaf` pakt het stuk niet bij nul: de eerste seconden van een nummer zijn
    meestal een kale opbouw, en bij acht seconden wil je de groove die er al
    staat. Er komt een fade in en een langere fade uit, want een track die
    midden in een maat afkapt klinkt als een fout.

    Instagram normaliseert het volume alsnog, maar iets zachter dan het origineel
    houdt de tekst leesbaar in plaats van dat het beeld tegen de muziek vecht.
    """
    import subprocess
    import imageio_ffmpeg

    bron = STIL / (slug + ".mp4")
    if not bron.exists():
        # Overslaan en doorgaan, niet stoppen.
        #
        # Dit was een SystemExit, en dan valt de hele reeks stil op het eerste
        # onderwerp dat nog geen stille versie heeft - terwijl de zesentwintig
        # erachter gewoon klaar stonden. Dat gebeurde toen er zes onderwerpen
        # bij kwamen waarvan de animatie nog liep: --verdeel stopte bij `blood`
        # en de rest kreeg geen muziek. Wat ontbreekt hoort gemeld te worden,
        # niet de rest tegen te houden.
        print("  %-20s overgeslagen: nog geen stille versie" % slug)
        return None
    DOEL.mkdir(parents=True, exist_ok=True)
    doel = DOEL / (slug + ".mp4")

    fade_uit = max(SECONDEN - 1.2, 0.1)
    filter_ = ("afade=t=in:st=0:d=0.6,"
               "afade=t=out:st={:.2f}:d=1.2,volume={:.1f}dB".format(fade_uit, luider))
    opdracht = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(bron),
        "-ss", "{:.2f}".format(vanaf), "-t", "{:.2f}".format(SECONDEN), "-i", str(muziek),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        "-af", filter_, "-shortest", "-movflags", "+faststart", str(doel),
    ]
    subprocess.run(opdracht, check=True, capture_output=True)
    return doel


def onderwerpen(alleen=None):
    for pad in sorted(ONDERWERPEN.glob("*.json")):
        d = json.loads(pad.read_text(encoding="utf-8"))
        slug = d.get("slug") or pad.stem
        if alleen and slug not in alleen:
            continue
        yield d, slug


def maak(d, slug, taal):
    bron = BEELDEN / (slug + ".jpg")
    if not bron.exists():
        raise SystemExit("Geen beeld voor {}. Draai eerst build/gids_beelden.py."
                         .format(slug))
    DOEL.mkdir(parents=True, exist_ok=True)
    STIL.mkdir(parents=True, exist_ok=True)
    # De video komt stil in de werkmap; de caption hoort bij wat je post en
    # staat dus wel in de bovenste map.
    doel = STIL / (slug + ".mp4")
    titel = veld(d, "title", taal)
    vraag = veld(d, "card", taal)
    link = ("" if taal == "en" else "/nl") + BASIS.rstrip("/")

    # macro_block_size=8: 1080 en 1920 zijn beide door 8 deelbaar, dus ffmpeg
    # hoeft niets te herschalen. Op de standaard 16 zou hij het formaat
    # stilletjes aanpassen, en dan klopt de veilige strook niet meer.
    # faststart zet de index vooraan, zodat een speler niet eerst het hele
    # bestand hoeft te laden.
    schrijver = imageio.get_writer(
        str(doel), fps=FPS, codec="libx264", macro_block_size=8,
        # Geen -pix_fmt hier: imageio zet die zelf al op yuv420p, en twee keer
        # dezelfde optie levert een waarschuwing van ffmpeg op.
        ffmpeg_params=["-crf", "21", "-profile:v", "high",
                       "-movflags", "+faststart"])
    # Een echte animatie als die er is, anders de zoom. Het Kling-videotegoed
    # verliep 18 september 2026, dus de zevenentwintig die er nu liggen zijn er
    # en er komen er voorlopig geen bij: een nieuw onderwerp krijgt de zoom tot
    # er tegoed is om het te animeren.
    staande = ANIMATIES_STAAND / (slug + ".mp4")
    animatie = ANIMATIES / (slug + ".mp4")
    if STAAND and staande.exists():
        beeldjes = frames_staand(staande, titel, vraag, link)
    elif STAAND:
        raise SystemExit(
            "Geen staande animatie voor {}. Draai eerst:\n"
            "  python build/gids_beelden.py --staand --ja\n"
            "  python build/gids_animaties.py --staand --ja".format(slug))
    elif animatie.exists():
        beeldjes = frames_uit_animatie(animatie, titel, vraag, link)
    else:
        beeldjes = frames(bron, titel, vraag, link)
    try:
        for beeldje in beeldjes:
            schrijver.append_data(beeldje)
    finally:
        schrijver.close()

    tekst = DOEL / (slug + ".txt")
    tekst.write_text(caption(d, taal), encoding="utf-8")
    return doel, tekst


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reels uit de Dream Guide.")
    ap.add_argument("slugs", nargs="*", help="alleen deze onderwerpen")
    ap.add_argument("--ja", action="store_true", help="echt maken")
    ap.add_argument("--check", action="store_true", help="alleen laten zien")
    ap.add_argument("--taal", default="en", choices=("en", "nl"))
    # Schermvullend in plaats van een liggend beeld in een kader. Vraagt een
    # eigen staande set; zie build/gids_beelden.py --staand.
    ap.add_argument("--staand", action="store_true",
                    help="het beeld schermvullend, met de tekst erover")
    ap.add_argument("--tekst", action="store_true",
                    help="alleen de captions opnieuw schrijven, geen video")
    ap.add_argument("--muziek", metavar="MP3",
                    help="één nummer onder alle video's zetten; het resultaat "
                         "komt in data/reels/")
    ap.add_argument("--verdeel", action="store_true",
                    help="per onderwerp het nummer dat bij de stemming hoort, "
                         "uit data/muziek/")
    ap.add_argument("--vanaf", type=float, default=None,
                    help="op welke seconde van het nummer het stuk begint; "
                         "zonder dit wordt het gemeten")
    args = ap.parse_args(argv)

    # De Nederlandse Reels gaan naar een eigen map.
    #
    # Zonder dit schrijven beide talen naar `data/reels/<slug>.mp4` én naar
    # dezelfde caption, en overschrijft de tweede run stilletjes de eerste. Dat
    # merk je pas als er al iets geplaatst is. Eén keer omzetten bij de start is
    # genoeg; de rest van het script kent alleen DOEL en STIL.
    global DOEL, STIL, STAAND
    STAAND = args.staand
    if STAAND:
        # Een eigen map, want dit is een andere opmaak van hetzelfde onderwerp.
        # In dezelfde map zou de tweede run de eerste overschrijven, net als bij
        # de talen.
        DOEL = DOEL.parent / (DOEL.name + "-staand")
        STIL = DOEL / "stil"
    if args.taal == "nl":
        DOEL = DOEL.parent / (DOEL.name + "-nl")
        STIL = DOEL / "stil"

    rijen = list(onderwerpen(set(args.slugs) or None))
    if not rijen:
        raise SystemExit("Geen onderwerpen gevonden.")

    if not args.ja:
        print("{} Reels, {} x {}, {} seconden, zonder geluid.".format(
            len(rijen), BREEDTE, HOOGTE, SECONDEN))
        print("Draai met --ja om ze te maken.\n")
        for d, slug in rijen:
            print("  {:<20} {}".format(slug, veld(d, "title", args.taal)))
        return 0

    if args.verdeel:
        # Het startpunt wordt per nummer één keer gemeten en niet per video:
        # zeven metingen maal zevenentwintig is zonde van de tijd, en het
        # antwoord is voor elk onderwerp hetzelfde.
        starts, ontbreekt = {}, []
        for naam, bestand in MUZIEK.items():
            pad = MUZIEKMAP / bestand
            if not pad.exists():
                ontbreekt.append(str(pad.relative_to(WORTEL)))
                continue
            starts[naam] = (pad, beste_start(pad))
        if ontbreekt:
            raise SystemExit("Ontbrekende nummers:\n  " + "\n  ".join(ontbreekt))
        for naam, (pad, vanaf) in starts.items():
            print("  {:<8} {:<38} vanaf {:.0f}s".format(naam, pad.name, vanaf))
        print("")
        for d, slug in rijen:
            naam = stemming_van(slug)
            pad, vanaf = starts[naam]
            uit = muziek_eronder(slug, pad, vanaf)
            if uit is None:
                continue
            print("  {:<20} {:<8} {:>6.1f} MB".format(
                slug, naam, uit.stat().st_size / 1e6))
        print("")
        print("Klaar: {}".format(DOEL.relative_to(WORTEL)))
        return 0

    if args.muziek:
        muziek = Path(args.muziek)
        if not muziek.exists():
            raise SystemExit("Muziekbestand niet gevonden: {}".format(muziek))
        vanaf = args.vanaf if args.vanaf is not None else beste_start(muziek)
        print("{} onder {} video's, vanaf seconde {:.0f}{}.".format(
            muziek.name, len(rijen), vanaf,
            "" if args.vanaf is not None else " (gemeten)"))
        print("")
        for d, slug in rijen:
            uit = muziek_eronder(slug, muziek, vanaf)
            if uit is None:
                continue
            print("  {:<20} {:>6.1f} MB".format(slug, uit.stat().st_size / 1e6))
        print("")
        print("Klaar: {}".format(DOEL.relative_to(WORTEL)))
        return 0

    if args.tekst:
        DOEL.mkdir(parents=True, exist_ok=True)
        for d, slug in rijen:
            tekst = DOEL / (slug + ".txt")
            inhoud = caption(d, args.taal)
            tekst.write_text(inhoud, encoding="utf-8")
            merk = "  LET OP: boven de 2200" if len(inhoud) > CAPTION_MAX else ""
            print("  {:<20} {:>5} tekens{}".format(slug, len(inhoud), merk))
        return 0

    for d, slug in rijen:
        print("  {:<20} ".format(slug), end="", flush=True)
        video, tekst = maak(d, slug, args.taal)
        print("{:>6.1f} MB   caption {} regels".format(
            video.stat().st_size / 1e6,
            len(tekst.read_text(encoding="utf-8").splitlines())))
    print("")
    print("Klaar: {} (stil) en de captions in {}".format(
        STIL.relative_to(WORTEL), DOEL.relative_to(WORTEL)))
    print("Nog geen geluid. Draai nu: python build/reels.py --verdeel --ja")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
