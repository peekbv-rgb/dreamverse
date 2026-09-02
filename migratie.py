"""Het archief van vóór de accounts overzetten naar één gebruiker.

    python migratie.py --naar ruud@catyra.com

Tot de accountlaag was er één profiel per installatie: `data/profile.json` met
een naam, een pakket en een tokensaldo, en `data/archive.json` met alle dromen.
De duidingen stonden los in `data/episodes/`, de panelen heetten `12-0.png`.

Dit script tilt dat naar één gebruiker: de dromen en duidingen naar de database,
en de bestanden naar hun nieuwe naam `<gebruikersnummer>_12-0.png`. Het is
bedoeld om één keer te draaien. Draai je het twee keer, dan gebeurt er niets
extra: bestaande dromen worden overgeschreven met dezelfde inhoud en bestanden
die al hernoemd zijn worden overgeslagen.

Het laat het oude spul staan in plaats van het weg te gooien. Wie een migratie
schrijft die zijn eigen bron opruimt, heeft één poging.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import accounts

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUD_ARCHIEF = DATA / "archive.json"
OUD_PROFIEL = DATA / "profile.json"
OUD_EPISODES = DATA / "episodes"
PANELS = DATA / "panels"


def lees(pad, standaard):
    try:
        with pad.open(encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return standaard


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--naar", required=True, help="e-mailadres van het doelaccount")
    ap.add_argument("--echt", action="store_true",
                    help="daadwerkelijk uitvoeren; zonder dit alleen vertellen wat er zou gebeuren")
    args = ap.parse_args()

    rij = accounts.db().execute("SELECT * FROM users WHERE email = ?",
                                (args.naar,)).fetchone()
    if rij is None:
        sys.exit("Er is nog geen account met {}. Maak het eerst aan in de app."
                 .format(args.naar))
    u = dict(rij)
    uid = u["id"]
    print("Doel: %s (gebruiker %d)" % (u["email"], uid))

    archief = lees(OUD_ARCHIEF, [])
    profiel = lees(OUD_PROFIEL, {})
    if not archief and not profiel:
        print("Er staat niets van vóór de accounts. Niets te doen.")
        return 0

    print("\nGevonden: %d dromen, profiel %s" % (len(archief), sorted(profiel) or "leeg"))

    # --- het profiel ------------------------------------------------------- #
    velden = {}
    for oud, nieuw in (("name", "name"), ("birthdate", "birthdate"),
                       ("gender", "gender"), ("language", "language"),
                       ("guardian_ok", "guardian_ok")):
        if profiel.get(oud) not in (None, ""):
            velden[nieuw] = profiel[oud]
    if velden:
        print("Profiel: %s" % ", ".join("%s=%s" % kv for kv in velden.items()))
    if profiel.get("plan"):
        print("Pakket: %s" % profiel["plan"])
    if profiel.get("tokens"):
        print("Tokens: %d" % profiel["tokens"])

    # --- de dromen --------------------------------------------------------- #
    for d in sorted(archief, key=lambda x: x.get("n", 0)):
        n = d.get("n")
        if not n:
            continue
        verbeelding = lees(OUD_EPISODES / ("%d.json" % n), None)
        bestanden = sorted(PANELS.glob("%d-*" % n)) + \
            ([PANELS / ("%d.json" % n)] if (PANELS / ("%d.json" % n)).is_file() else [])
        print("  droom %-3d %-34s duiding=%-3s bestanden=%d"
              % (n, (d.get("title") or "")[:34], "ja" if verbeelding else "nee",
                 len(bestanden)))

    if not args.echt:
        print("\nDit was een proefrun. Draai opnieuw met --echt om het te doen.")
        return 0

    # --- overzetten -------------------------------------------------------- #
    if velden:
        accounts.zet_profiel(uid, velden)
    if profiel.get("plan"):
        accounts.zet_pakket(uid, profiel["plan"])
    if profiel.get("tokens"):
        # tel_op en niet zetten: als het account al tokens had, blijven die staan.
        nu = accounts.gebruiker(uid)["tokens"]
        accounts.tel_op(uid, tokens=int(profiel["tokens"]) - nu)

    overgezet = 0
    hernoemd = 0
    for d in sorted(archief, key=lambda x: x.get("n", 0)):
        n = d.get("n")
        if not n:
            continue
        accounts.zet_droom(uid, n, d.get("text", ""), d.get("title", ""),
                           d.get("motifs", []), d.get("when", ""))
        if d.get("answer"):
            accounts.zet_veld(uid, n, "antwoord", d["answer"])
        if d.get("future_check"):
            accounts.zet_veld(uid, n, "vooruitblik", d["future_check"])

        verbeelding = lees(OUD_EPISODES / ("%d.json" % n), None)
        if verbeelding is not None:
            accounts.zet_verbeelding(uid, n, verbeelding)
        overgezet += 1

        # De bestanden krijgen het gebruikersnummer ervoor. Kopiëren en niet
        # verplaatsen: dan staat het oude er nog als dit misgaat.
        for pad in list(PANELS.glob("%d-*" % n)) + \
                [PANELS / ("%d.json" % n)]:
            if not pad.is_file():
                continue
            nieuw = PANELS / ("%d_%s" % (uid, pad.name))
            if nieuw.exists():
                continue
            shutil.copy2(pad, nieuw)
            hernoemd += 1

    print("\n%d dromen overgezet, %d bestanden gekopieerd naar de nieuwe naam."
          % (overgezet, hernoemd))
    print("Het oude archive.json, profile.json en episodes/ staan er nog. Controleer")
    print("eerst in de app of alles klopt; daarna kun je ze weggooien.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
