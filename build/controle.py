"""Stuurtekens in de broncode opsporen.

Dit bestaat om één reden. In `static/app.js` stond maandenlang een letterlijk
backspace-teken (0x08) middenin een reguliere expressie:

    if (/[?&]beheer<BS>/.test(location.search))

Bedoeld was een woordgrens, maar het teken zelf is weggeschreven in plaats van
de twee tekens die het beschrijven. Gevolg: `?beheer` matchte nooit, het
beheerpaneel ging nooit open, en er was géén spoor - geen fout in de console,
geen melding, niets. In een editor is het onzichtbaar; in de browser lijkt het
alsof een knop niet werkt.

Zoiets komt binnen als een script broncode wegschrijft en een reeks als \\b of
\\f onderweg als escape wordt uitgelegd. Dat is hier drie keer gebeurd, en de
kosten zitten niet in de reparatie maar in het zoeken.

    python build/controle.py

Geeft 1 terug als er iets gevonden is, zodat het in een hook of CI kan.
Tab (9), regeleinde (10) en carriage return (13) horen er gewoon; de rest niet.
"""

import sys
from pathlib import Path

WORTEL = Path(__file__).resolve().parent.parent
SUFFIXEN = (".py", ".js", ".html", ".css", ".json", ".txt", ".md", ".yaml", ".yml")
OVERSLAAN = {".git", "data", "node_modules", "__pycache__", "bronnen"}

GOED = {9, 10, 13}
NAMEN = {0: "NUL", 7: "bell", 8: "backspace", 11: "vertical tab", 12: "formfeed",
         26: "substitute", 27: "escape"}


def bestanden():
    for pad in sorted(WORTEL.rglob("*")):
        if not pad.is_file() or pad.suffix.lower() not in SUFFIXEN:
            continue
        if any(deel in OVERSLAAN for deel in pad.relative_to(WORTEL).parts):
            continue
        yield pad


def css_variabelen():
    """CSS-variabelen die gebruikt worden maar nergens gezet zijn.

    Dezelfde soort fout als een stuurteken: hij meldt zich niet. `var(--foo)`
    met een tikfout maakt de hele regel ongeldig, de browser slaat hem stil over
    en je ziet alleen dat er iets niet kleurt. Zo stond `--third_eye` met een
    lage streep op twee plekken, en werd `--water` nergens gezet - dus Vera's
    portret lichtte nooit op als ze luisterde.
    """
    import re
    pad = WORTEL / "static" / "style.css"
    if not pad.exists():
        return []
    tekst = pad.read_text(encoding="utf-8")
    gezet = set(re.findall(r"(--[\w-]+)\s*:", tekst))
    gebruikt = set(re.findall(r"var\(\s*(--[\w-]+)", tekst))
    return sorted(gebruikt - gezet)


def vertalingen():
    """`t("...")` in app.js zonder regel in taal.js.

    Zo'n zin valt terug op het Nederlands en blijft staan als de bezoeker op
    English drukt. Dat meldt zich nergens: er is geen fout, de app werkt, er
    staat alleen ineens een Nederlandse zin tussen de Engelse.

    Dit vangt alleen wat JavaScript maakt. Wat in index.html staat is hiermee
    niet te controleren - daar bepalen CSS-selectors welke elementen meedoen, en
    dat vraagt een echte browser. Die kant meet je door in de app op English te
    drukken en te kijken welke elementen hun `data-nl` houden.
    """
    import re
    app = WORTEL / "static" / "app.js"
    taal = WORTEL / "static" / "taal.js"
    if not app.exists() or not taal.exists():
        return []
    plat = lambda s: re.sub(r"\s+", " ", s).strip()

    sleutels = set()
    for m in re.finditer(r"\[\s*(['\"])((?:\\.|(?!\1).)*?)\1\s*,",
                         taal.read_text(encoding="utf-8"), re.S):
        sleutels.add(plat(m.group(2).replace('\\"', '"').replace("\\'", "'")))

    mist = set()
    for m in re.finditer(r"\bt\(\s*(['\"])((?:\\.|(?!\1).)*?)\1\s*\)",
                         app.read_text(encoding="utf-8"), re.S):
        zin = plat(m.group(2).replace('\\"', '"').replace("\\'", "'"))
        if zin and zin not in sleutels:
            mist.add(zin)
    return sorted(mist)


def entiteiten():
    """Sleutels in taal.js met een HTML-entiteit erin.

    De browser decodeert `&middot;` bij het inlezen, dus `innerHTML` geeft het
    teken terug en niet de entiteit. Staat de entiteit in de sleutel, dan matcht
    hij nooit - zonder fout, zonder melding, en de zin blijft in het Nederlands
    staan. Zo bleef de hele voetnootregel van de app onvertaald.

    `&amp;`, `&lt;` en `&gt;` mogen wel: die komen er ook weer als entiteit uit.
    """
    import re
    pad = WORTEL / "static" / "taal.js"
    if not pad.exists():
        return []
    tekst = pad.read_text(encoding="utf-8")
    verdacht = re.compile(r"&(?!amp;|lt;|gt;)[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;")
    uit = []
    # Twee alternatieven in plaats van een backreference: een `\1` in een
    # regex overleeft de reis door een shell niet en wordt een 0x01-teken.
    sleutel = re.compile(r"""\[\s*(?:'([^']*)'|"([^"]*)")\s*,""")
    for m in sleutel.finditer(tekst):
        zin = m.group(1) if m.group(1) is not None else m.group(2)
        if zin and verdacht.search(zin):
            uit.append(zin[:90])
    return uit


def main():
    gevonden = []
    for pad in bestanden():
        try:
            tekst = pad.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, teken in enumerate(tekst):
            code = ord(teken)
            if code < 32 and code not in GOED:
                regel = tekst[:i].count("\n") + 1
                kolom = i - (tekst.rfind("\n", 0, i) + 1) + 1
                # De regel erbij, met het teken zichtbaar gemaakt.
                begin = tekst.rfind("\n", 0, i) + 1
                eind = tekst.find("\n", i)
                inhoud = tekst[begin:eind if eind != -1 else len(tekst)]
                zichtbaar = "".join(
                    c if ord(c) >= 32 else "<%s>" % NAMEN.get(ord(c), "0x%02x" % ord(c))
                    for c in inhoud).strip()
                gevonden.append((pad.relative_to(WORTEL), regel, kolom, code, zichtbaar))

    zwevend = css_variabelen()
    onvertaald = vertalingen()
    gecodeerd = entiteiten()

    if not gevonden and not zwevend and not onvertaald and not gecodeerd:
        print("Geen stuurtekens, elke CSS-variabele bestaat, elke t()-zin heeft "
              "een vertaling, geen entiteiten in de sleutels.")
        return 0

    if gecodeerd:
        print("Sleutels in taal.js met een HTML-entiteit erin. De browser")
        print("decodeert die bij het inlezen, dus innerHTML geeft het teken")
        print("terug en de sleutel matcht nooit:")
        print("")
        for zin in gecodeerd:
            print("  %s" % zin)
        print("")
        if not gevonden and not zwevend and not onvertaald:
            return 1

    if onvertaald:
        print("Zinnen uit app.js zonder regel in taal.js. Die blijven in het")
        print("Nederlands staan zodra iemand op English drukt:")
        print("")
        for zin in onvertaald:
            print("  %s" % zin[:100])
        print("")
        if not gevonden and not zwevend:
            return 1

    if zwevend:
        print("CSS-variabelen die gebruikt worden maar nergens gezet zijn.")
        print("De browser slaat zo'n regel stil over; je ziet alleen dat er")
        print("iets niet kleurt:")
        print("")
        for naam in zwevend:
            print("  %s" % naam)
        print("")
        if not gevonden:
            return 1

    print("Stuurtekens in de broncode - bedoeld was bijna zeker de tekst,")
    print("niet het teken zelf:")
    print("")
    for pad, regel, kolom, code, inhoud in gevonden:
        naam = NAMEN.get(code, "0x%02x" % code)
        print("  %s:%s:%s  %s" % (pad, regel, kolom, naam))
        print("    %s" % inhoud[:120])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
