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

    if not gevonden:
        print("Geen stuurtekens gevonden.")
        return 0

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
