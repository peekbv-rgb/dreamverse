"""Van een gidsonderwerp een Reel maken: staand, met tekst, met beweging.

Er liggen zevenentwintig onderwerpen met elk een beeld en een uitgeschreven
tekst. Dat is bijna vier weken dagelijks posten zonder dat er nog iets bedacht
hoeft te worden - en het is de enige inhoud die dit account heeft en niemand
anders.

    python build/reels.py --check                 # wat er gemaakt zou worden
    python build/reels.py --ja                    # alles
    python build/reels.py --ja snakes falling     # een paar
    python build/reels.py --ja --taal nl          # Nederlandse tekst

Levert per onderwerp `data/reels/<slug>.mp4` (1080 x 1920, 8 seconden) en
`data/reels/<slug>.txt` met de caption om erbij te zetten.

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


def gespreid(tekenen, tekst, font, midden, y, kleur, spatie=6):
    """Tekst met ruimte tussen de letters. PIL kent geen letter-spacing, en het
    merk hoort er net zo uit te zien als op de DreamCard."""
    breedtes = [tekenen.textlength(c, font=font) for c in tekst]
    totaal = sum(breedtes) + spatie * (len(tekst) - 1)
    x = midden - totaal / 2
    for c, b in zip(tekst, breedtes):
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


def masker(breedte, hoogte, hoek=36):
    m = Image.new("L", (breedte, hoogte), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, breedte - 1, hoogte - 1],
                                        radius=hoek, fill=255)
    return m


def frames(bron, titel, vraag, link):
    """Elk beeldje: de vaste laag met het ingezoomde beeld erin."""
    grond = achtergrond(titel, vraag, link)
    vak_b, vak_h = VAK[2] - VAK[0], VAK[3] - VAK[1]
    vorm = masker(vak_b, vak_h)

    beeld = Image.open(bron).convert("RGB")
    # Het grootste stuk van de bron met de verhouding van het kader.
    verhouding = vak_b / vak_h
    if beeld.width / beeld.height > verhouding:
        h = beeld.height
        b = round(h * verhouding)
    else:
        b = beeld.width
        h = round(b / verhouding)

    totaal = FPS * SECONDEN
    for i in range(totaal):
        deel = i / max(totaal - 1, 1)
        schaal = 1 + (ZOOM - 1) * deel
        snee_b, snee_h = round(b / schaal), round(h / schaal)
        x = (beeld.width - snee_b) // 2
        y = (beeld.height - snee_h) // 2
        stuk = beeld.crop((x, y, x + snee_b, y + snee_h)).resize(
            (vak_b, vak_h), Image.LANCZOS)
        doek = grond.copy()
        doek.paste(stuk, (VAK[0], VAK[1]), vorm)
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
    doel = DOEL / (slug + ".mp4")
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
    try:
        for beeldje in frames(bron, titel, vraag, link):
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
    ap.add_argument("--tekst", action="store_true",
                    help="alleen de captions opnieuw schrijven, geen video")
    args = ap.parse_args(argv)

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
    print("\nKlaar: {}".format(DOEL.relative_to(WORTEL)))
    print("De muziek kies je in Instagram; deze bestanden zijn stil.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
