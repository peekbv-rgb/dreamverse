"""Het cijfer waar dit project op staat of valt.

Tien testpersonen, drie dagen, en kijken wie er op dag vier uit zichzelf
terugkomt. Alles wat daarvoor nodig is stond al in de database; er was alleen
geen scherm dat het liet zien.

**Geen derde partij, geen cookies, geen banner.** Er wordt niets bijgehouden wat
er niet al was: aanmeldingen staan in `users.gemaakt`, dromen in `dromen.wanneer`,
vragen in de bewaarde verbeelding, betalingen in `betalingen`, en of iemand naar
Stripe is doorgestuurd in `usage`. Voor een app waarin mensen over hun angsten en
hun overledenen schrijven, is het gedrag van die mensen doorgeven aan een
advertentiebedrijf een zwaardere prijs dan bij een webshop.

Wat er dus **niet** in staat: waar mensen klikken, hoe ver ze scrollen, waar ze
afhaken op een pagina. Dat zou clientmeting vragen en dat is precies de stap die
een cookiebanner oplevert.

    python rapport.py            # afdrukken in de terminal
"""

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

import accounts


def _datum(waarde):
    """Een datum uit de database, hoe hij ook is opgeschreven."""
    if not waarde:
        return None
    tekst = str(waarde)[:10]
    try:
        return date.fromisoformat(tekst)
    except ValueError:
        return None


def cijfers(dagen=30):
    """Alles bij elkaar. Eén doorloop, want het zijn hooguit een paar duizend rijen."""
    db = accounts.db()
    vandaag = date.today()
    grens = vandaag - timedelta(days=dagen)

    gebruikers = {}
    for r in db.execute("SELECT id, email, pakket, tokens, gemaakt FROM users"):
        gebruikers[r["id"]] = {
            "email": r["email"], "pakket": r["pakket"], "tokens": r["tokens"],
            "sinds": _datum(r["gemaakt"]), "dagen": set(), "dromen": 0, "vragen": 0,
        }

    for r in db.execute("SELECT user_id, n, wanneer FROM dromen"):
        u = gebruikers.get(r["user_id"])
        if not u:
            continue
        u["dromen"] += 1
        d = _datum(r["wanneer"])
        if d:
            u["dagen"].add(d)

    # Vragen zitten in de bewaarde verbeelding; die is een woordenboek.
    for r in db.execute("SELECT user_id, data FROM verbeeldingen"):
        u = gebruikers.get(r["user_id"])
        if not u:
            continue
        try:
            u["vragen"] += len((json.loads(r["data"]) or {}).get("vragen") or [])
        except (ValueError, TypeError):
            pass

    betaald = Counter()
    omzet = 0.0
    for r in db.execute("SELECT soort, bedrag FROM betalingen"):
        betaald[r["soort"] or "?"] += 1
        omzet += (r["bedrag"] or 0) / 100.0

    # Per dag: hoeveel aanmeldingen, hoeveel dromen.
    per_dag = defaultdict(lambda: {"nieuw": 0, "dromen": 0})
    for u in gebruikers.values():
        if u["sinds"] and u["sinds"] >= grens:
            per_dag[u["sinds"]]["nieuw"] += 1
        for d in u["dagen"]:
            if d >= grens:
                per_dag[d]["dromen"] += 1

    # Het cijfer zelf: wie kwam er terug op dag vier of later?
    #
    # "Terug" is bewust streng: een dróom op dag vier of later, niet een bezoek.
    # Iemand die alleen even kijkt is geen gebruiker; iemand die opnieuw een
    # droom vertelt wel.
    rijp = [u for u in gebruikers.values()
            if u["sinds"] and (vandaag - u["sinds"]).days >= 3]
    terug = [u for u in rijp
             if any((d - u["sinds"]).days >= 3 for d in u["dagen"])]
    meerdaags = [u for u in gebruikers.values() if len(u["dagen"]) > 1]

    # Wat mensen zelf opschreven. Het enige stuk van dit rapport dat vertelt
    # waarom iemand wegblijft in plaats van dat hij wegblijft.
    terugkoppeling = accounts.alle_feedback()

    # De trechter ervoor. Zonder dit zie je pas iets zodra iemand een account
    # maakt, en weet je nooit of er honderd mensen keken en afhaakten of dat er
    # simpelweg niemand langskwam. Dat zijn twee heel verschillende problemen.
    tellingen = accounts.weergaven(dagen)
    landing = Counter()
    appview = Counter()
    for r in tellingen:
        (landing if r["pagina"] == "landing" else appview)[r["datum"]] += r["aantal"]
    nieuw_per_dag = Counter(
        u["sinds"].isoformat() for u in gebruikers.values() if u["sinds"])
    dromen_per_dag = Counter()
    for u in gebruikers.values():
        for d in u["dagen"]:
            dromen_per_dag[d.isoformat()] += 1

    return {
        "feedback": terugkoppeling,
        "trechter": [
            {"datum": d, "landing": landing.get(d, 0), "app": appview.get(d, 0),
             "nieuw": nieuw_per_dag.get(d, 0), "dromen": dromen_per_dag.get(d, 0)}
            for d in sorted(set(landing) | set(appview) | set(nieuw_per_dag)
                            | set(dromen_per_dag), reverse=True)
        ],
        "gebruikers": len(gebruikers),
        "met_droom": sum(1 for u in gebruikers.values() if u["dromen"]),
        "dromen": sum(u["dromen"] for u in gebruikers.values()),
        "vragen": sum(u["vragen"] for u in gebruikers.values()),
        "vragers": sum(1 for u in gebruikers.values() if u["vragen"]),
        "meerdaags": len(meerdaags),
        "oud_genoeg": len(rijp),
        "terug_dag4": len(terug),
        "pakketten": dict(Counter(u["pakket"] for u in gebruikers.values())),
        "betalingen": dict(betaald),
        "omzet": round(omzet, 2),
        "per_dag": [
            {"datum": d.isoformat(), "nieuw": v["nieuw"], "dromen": v["dromen"]}
            for d, v in sorted(per_dag.items(), reverse=True)
        ],
        "mensen": sorted(
            [{"email": u["email"], "pakket": u["pakket"], "tokens": u["tokens"],
              "sinds": u["sinds"].isoformat() if u["sinds"] else "",
              "dromen": u["dromen"], "actieve_dagen": len(u["dagen"]),
              "vragen": u["vragen"],
              "terug": bool(u["sinds"] and any((d - u["sinds"]).days >= 3
                                               for d in u["dagen"]))}
             for u in gebruikers.values()],
            key=lambda x: (-x["dromen"], x["sinds"])),
    }


def main():
    import os
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

    c = cijfers()
    print("Dreamverse - de cijfers van vandaag")
    print("")
    print("  gebruikers      %d, waarvan %d met minstens een droom" % (
        c["gebruikers"], c["met_droom"]))
    print("  dromen          %d" % c["dromen"])
    print("  vragen          %d, door %d mensen" % (c["vragen"], c["vragers"]))
    print("  meer dan een dag actief: %d" % c["meerdaags"])
    print("")
    if c["oud_genoeg"]:
        print("  DAG VIER: %d van de %d mensen die er lang genoeg zijn kwamen terug (%d%%)"
              % (c["terug_dag4"], c["oud_genoeg"],
                 round(100 * c["terug_dag4"] / c["oud_genoeg"])))
    else:
        print("  DAG VIER: nog niemand is drie dagen onderweg.")
    print("")
    print("  pakketten       %s" % c["pakketten"])
    print("  betalingen      %s, samen EUR %.2f" % (c["betalingen"], c["omzet"]))
    print("")
    print("  DE TRECHTER  (bezoek -> account -> droom)")
    print("    %-12s %8s %8s %8s %8s" % ("datum", "landing", "app", "nieuw", "dromen"))
    tot = {"landing": 0, "app": 0, "nieuw": 0, "dromen": 0}
    # Alleen dagen waarop er ook echt geteld is. Het tellen begon later dan de
    # eerste accounts, en dan deel je twee getallen op elkaar die over
    # verschillende weken gaan - dat leest als een percentage en is het niet.
    gemeten = {"landing": 0, "nieuw": 0}
    for r in c["trechter"][:14]:
        print("    %-12s %8d %8d %8d %8d" % (
            r["datum"], r["landing"], r["app"], r["nieuw"], r["dromen"]))
        for k in tot:
            tot[k] += r[k]
        if r["landing"] or r["app"]:
            gemeten["landing"] += r["landing"]
            gemeten["nieuw"] += r["nieuw"]
    print("    %-12s %8d %8d %8d %8d" % (
        "samen", tot["landing"], tot["app"], tot["nieuw"], tot["dromen"]))
    if gemeten["landing"] >= 10:
        print("")
        print("    Van %d bezoeken aan de landingspagina werden er %d een account: %.0f%%."
              % (gemeten["landing"], gemeten["nieuw"],
                 100 * gemeten["nieuw"] / gemeten["landing"]))
    elif gemeten["landing"]:
        print("")
        print("    Nog te weinig bezoek (%d) om er een percentage van te maken."
              % gemeten["landing"])
    print("")
    print("  Bezoeken zijn weergaven, geen personen: er wordt niets bewaard")
    print("  waarmee twee bezoeken aan dezelfde mens zijn toe te schrijven.")

    if c["feedback"]:
        print("")
        print("  WAT MENSEN ZELF SCHREVEN (%d):" % len(c["feedback"]))
        for f in c["feedback"][:15]:
            print("")
            print("    %s  %s  (na %d dromen)" % (
                (f["wanneer"] or "")[:10], f["email"] or "(verwijderd)", f["dromen"]))
            for regel in _omslaan(f["tekst"], 68):
                print("      %s" % regel)
    else:
        print("")
        print("  Nog niemand heeft iets opgeschreven.")
    return 0


def _omslaan(tekst, breedte):
    """Zelf omslaan; textwrap slikt de lege regels tussen alinea's op."""
    import textwrap
    uit = []
    for alinea in (tekst or "").splitlines():
        uit.extend(textwrap.wrap(alinea, breedte) or [""])
    return uit


if __name__ == "__main__":
    raise SystemExit(main())
