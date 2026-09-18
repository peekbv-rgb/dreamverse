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

from pathlib import Path

import accounts
import usage


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
    gidsview = Counter()
    gidspaginas = Counter()
    stappen = Counter()
    bronnen = Counter()
    # Hoeveel van die bezoeken ook de stylesheet ophaalden. Zie het commentaar
    # bij de teller in server.py: een browser die tekent doet dat, een scraper
    # die alleen de HTML binnenhaalt niet.
    cssview = Counter()
    # Elke soort in zijn eigen bak. Dit stond eerst als "landing of anders app",
    # en daarmee kwamen de gidspagina's - die met "gids" en "gids:<slug>" ook
    # geteld worden - in de kolom van de app terecht. Dan lijkt het alsof er
    # mensen in de app zijn die op een publieke pagina van Google stonden.
    for r in tellingen:
        naam = r["pagina"]
        if naam == "landing":
            landing[r["datum"]] += r["aantal"]
        elif naam == "app":
            appview[r["datum"]] += r["aantal"]
        elif naam.startswith("bron:"):
            bronnen[naam[5:]] += r["aantal"]
        elif naam == "css":
            cssview[r["datum"]] += r["aantal"]
        elif naam in accounts.GEBEURTENISSEN:
            # De stappen die alleen in de browser te zien zijn. Ze staan in
            # dezelfde tabel als de paginatellers, met dezelfde soort inhoud:
            # een naam en een aantal per dag, en verder niets.
            stappen[naam] += r["aantal"]
        elif naam == "gids" or naam.startswith("gids:"):
            gidsview[r["datum"]] += r["aantal"]
            # En apart per onderwerp. Dit stond er al in de database en werd
            # alleen nooit uit elkaar gehaald; het is het enige cijfer dat
            # zegt welk onderwerp bezoek trekt en dus welke erbij moeten.
            if naam.startswith("gids:"):
                gidspaginas[naam[5:]] += r["aantal"]
    # De gratis duidingen. Dit is de stap die sinds 14 september tussen bezoek
    # en account zit, en de reden dat hij er is: iemand krijgt eerst een duiding
    # te lezen en wordt pas daarna om een account gevraagd. Zonder deze kolom is
    # niet te zien of dat werkt - je ziet dan alleen dat er bezoek is en of er
    # accounts bij komen, en niet of wat ertussen zit iets doet.
    #
    # De telling komt uit `usage.jsonl` en niet uit de database: er wordt bij een
    # gratis duiding met opzet niets in de database geschreven. In die regel
    # staat de datum, het aantal tokens en verder niets - geen adres, geen
    # droomtekst, geen duiding.
    proef_per_dag = Counter()
    proef_kosten = 0.0
    tarieven = usage.rates()
    for r in usage.read():
        if r.get("kind") != "proef":
            continue
        dag = str(r.get("at", ""))[:10]
        if dag:
            proef_per_dag[dag] += 1
        proef_kosten += (r.get("input_tokens", 0) / 1e6) * tarieven["eur_per_m_input"]
        proef_kosten += (r.get("output_tokens", 0) / 1e6) * tarieven["eur_per_m_output"]

    nieuw_per_dag = Counter(
        u["sinds"].isoformat() for u in gebruikers.values() if u["sinds"])
    dromen_per_dag = Counter()
    for u in gebruikers.values():
        for d in u["dagen"]:
            dromen_per_dag[d.isoformat()] += 1

    return {
        "feedback": terugkoppeling,
        "trechter": [
            {"datum": d, "landing": landing.get(d, 0), "gids": gidsview.get(d, 0),
             "app": appview.get(d, 0), "proef": proef_per_dag.get(d, 0),
             "nieuw": nieuw_per_dag.get(d, 0), "dromen": dromen_per_dag.get(d, 0)}
            for d in sorted(set(landing) | set(appview) | set(gidsview)
                            | set(proef_per_dag)
                            | set(nieuw_per_dag) | set(dromen_per_dag),
                            reverse=True)
        ],
        # Twee getallen die naast elkaar horen: wat er geserveerd is en hoeveel
        # daarvan ook een stylesheet ophaalde. Het tweede is een ondergrens -
        # een browser bewaart die stylesheet - dus een hoog getal bewijst
        # mensen en een laag getal maakt ze onwaarschijnlijk.
        "css": sum(cssview.values()),
        "paginas_totaal": (sum(landing.values()) + sum(appview.values())
                           + sum(gidsview.values())),
        "css_per_dag": dict(sorted(cssview.items(), reverse=True)),
        "proef": sum(proef_per_dag.values()),
        "proef_kosten": round(proef_kosten, 2),
        "bronnen": dict(bronnen.most_common()),
        "gidspaginas": dict(gidspaginas.most_common()),
        "stappen": {k: stappen.get(k, 0) for k in accounts.GEBEURTENISSEN},
        # Alle onderwerpen die bestaan, zodat het rapport kan zeggen
        # welke nog nul bezoeken hadden - dat is net zo bruikbaar als
        # de lijst met wat het wél doet.
        "gids_alle": sorted(
            p.stem for p in (Path(__file__).resolve().parent
                             / "knowledge" / "droomgids").glob("*.json")),
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
    print("  DE TRECHTER  (bezoek -> gratis duiding -> account -> droom)")
    print("    %-12s %8s %8s %8s %8s %8s %8s" % (
        "datum", "landing", "gids", "app", "duiding", "nieuw", "dromen"))
    tot = {"landing": 0, "gids": 0, "app": 0, "proef": 0, "nieuw": 0, "dromen": 0}
    # Alleen dagen waarop er ook echt geteld is. Het tellen begon later dan de
    # eerste accounts, en dan deel je twee getallen op elkaar die over
    # verschillende weken gaan - dat leest als een percentage en is het niet.
    gemeten = {"landing": 0, "nieuw": 0}
    for r in c["trechter"][:14]:
        print("    %-12s %8d %8d %8d %8d %8d %8d" % (
            r["datum"], r["landing"], r["gids"], r["app"], r["proef"],
            r["nieuw"], r["dromen"]))
        for k in tot:
            tot[k] += r[k]
        if r["landing"] or r["app"]:
            gemeten["landing"] += r["landing"]
            gemeten["nieuw"] += r["nieuw"]
    print("    %-12s %8d %8d %8d %8d %8d %8d" % (
        "samen", tot["landing"], tot["gids"], tot["app"], tot["proef"],
        tot["nieuw"], tot["dromen"]))
    if c["proef"]:
        # Wat de gratis duiding tot nu toe gekost heeft, en wat hij opleverde.
        # Dit zijn de twee getallen waarop dit onderdeel beoordeeld hoort te
        # worden: het is het enige eindpunt waar een vreemde geld laat uitgeven.
        print("")
        print("    %d gratis duidingen, samen EUR %.2f (EUR %.3f per stuk)."
              % (c["proef"], c["proef_kosten"], c["proef_kosten"] / c["proef"]))
    if gemeten["landing"] >= 10:
        print("")
        print("    Van %d bezoeken aan de landingspagina werden er %d een account: %.0f%%."
              % (gemeten["landing"], gemeten["nieuw"],
                 100 * gemeten["nieuw"] / gemeten["landing"]))
    elif gemeten["landing"]:
        print("")
        print("    Nog te weinig bezoek (%d) om er een percentage van te maken."
              % gemeten["landing"])
    # Waar ze afhaken. Dit is het stuk dat de dagtabel hierboven niet kan
    # laten zien: wie begon en niet afmaakte.
    st = c.get("stappen") or {}
    if any(st.values()):
        print("")
        print("  WAAR ZE AFHAKEN")
        # "account gemaakt" staat hier bewust **niet** bij, hoe verleidelijk ook.
        # Dat cijfer komt uit `users.gemaakt` en loopt over de hele periode,
        # terwijl deze stappen pas tellen sinds ze erin zitten. Die twee op
        # elkaar delen geeft een percentage boven de honderd - gemeten, de
        # eerste keer dat dit blok draaide - en dat is dezelfde fout als bij de
        # trechter hierboven: twee getallen uit verschillende weken.
        rijen = [
            ("op 'Lees deze droom' gedrukt", st.get("proef:start", 0)),
            ("duiding gekregen", st.get("proef:klaar", 0)),
            ("op 'Maak een account' gedrukt", st.get("proef:account", 0)),
            ("aanmeldformulier bereikt", st.get("poort:account", 0)),
        ]
        eerste = rijen[0][1] or 0
        for naam, aantal in rijen:
            deel = ("%3d%%" % round(100 * aantal / eerste)) if eerste else "   -"
            print("    %-32s %5d  %s" % (naam, aantal, deel))
        print("")
        print("    Percentages ten opzichte van de eerste regel. Deze tellers")
        print("    begonnen later dan de rest; vergelijk ze niet met de tabel")
        print("    hierboven maar alleen met elkaar.")
        if st.get("proef:start", 0) > st.get("proef:klaar", 0):
            print("")
            print("    %d begonnen zonder duiding te krijgen - te korte droom,"
                  % (st["proef:start"] - st.get("proef:klaar", 0)))
            print("    dagplafond bereikt, of het ging mis.")

    # Welk onderwerp bezoek trekt. Dit stond al in de database en werd alleen
    # nooit uit elkaar gehaald; het is het cijfer waarop je besluit welke
    # onderwerpen erbij moeten - en welke je niet nog eens hoeft te schrijven.
    if c.get("gidspaginas"):
        print("")
        print("  WELK GIDSONDERWERP BEZOEK TREKT")
        for naam, aantal in list(c["gidspaginas"].items())[:15]:
            print("    %-22s %5d" % (naam, aantal))
        rest = len(c["gidspaginas"]) - 15
        if rest > 0:
            print("    (en %d onderwerpen met minder)" % rest)
        stil = [s for s in c.get("gids_alle", []) if s not in c["gidspaginas"]]
        if stil:
            print("")
            print("    Nog geen enkel bezoek: %s" % ", ".join(stil[:12]))

    # Hoeveel van die bezoeken een echte browser waren, voor zover te zien.
    # Zie het commentaar bij de teller in server.py: dit is een ondergrens.
    css = c.get("css") or 0
    paginas = c.get("paginas_totaal") or 0
    if paginas:
        print("")
        print("  WAS HET EEN BROWSER?")
        print("    paginas geserveerd   %6d" % paginas)
        print("    stylesheet opgehaald %6d" % css)
        if css * 3 < paginas:
            print("")
            print("    Minder dan een derde haalde de stylesheet op. Een browser")
            print("    die een pagina tekent doet dat wel, dus het grootste deel")
            print("    van dit verkeer tekent niets - vrijwel zeker geen mensen.")
        elif css * 2 >= paginas:
            print("")
            print("    Ruim de helft haalde de stylesheet op: dit zijn browsers.")
            print("    Dan is het geen publiek dat ontbreekt maar een reden om")
            print("    iets te doen.")

    if c["bronnen"]:
        print("")
        print("  WAAR ZE VANDAAN KWAMEN")
        for naam, aantal in c["bronnen"].items():
            print("    %-12s %8d" % (naam, aantal))
        print("")
        print("    Wat op -app eindigt komt uit de eigen browser van die app")
        print("    (ig-app, fb-app, tiktok-app) en wordt ook zonder tag in de")
        print("    link herkend. De rest komt van ?van=... achter het adres,")
        print("    en die is preciezer: die weet bio van post te scheiden.")
    else:
        print("")
        print("  WAAR ZE VANDAAN KWAMEN: nog niets gemeten. Zet ?van=ig achter")
        print("  het adres in de Instagram-bio; de eigen browser van Instagram")
        print("  wordt ook zonder dat herkend.")
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
