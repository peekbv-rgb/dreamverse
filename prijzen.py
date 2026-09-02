"""Wat blijft er over van een abonnement, na btw en betaalkosten?

    python prijzen.py                 # de pakketten zoals ze nu zijn
    python prijzen.py --scan          # wat er overblijft bij andere prijzen
    python prijzen.py --btw 21        # ander btw-tarief doorrekenen

De prijslijst in plans.py rekent kostprijs tegen omzet. Dat is te optimistisch,
want er gaan twee dingen af die er nog niet in zaten.

**Btw.** Een consumentenprijs is een prijs inclusief btw: wie €7,99 betaalt, geeft
je €6,60 en de rest is van de belastingdienst. Bij digitale diensten aan
particulieren geldt het tarief van het land van de klant, dus over de hele EU is
21% een planningsgetal en geen exact bedrag - Luxemburg zit op 17%, Hongarije op
27%.

**Betaalkosten.** Met een merchant of record (Stripe Managed Payments, Paddle,
Polar) is dat 5% + $0,50 per transactie. Dat is duurder dan kaal Stripe, en dat
verschil koop je bewust: zij worden de verkoper en doen de btw-aangifte in de
hele EU. Zelf OSS-aangifte doen over 27 tarieven kost meer dan het scheelt.

De kostprijzen komen uit plans.py, dus deze berekening loopt automatisch mee als
die veranderen.
"""

import argparse

import plans

# 5% + $0,50 per transactie. De dollar is hier op €0,92 gezet; dat schuift, dus
# het is een planningsgetal.
FEE_DEEL = 0.05
FEE_VAST = 0.46
BTW = 0.21

# Wat een gratis gebruiker kost: drie dromen op de kwaliteit die gratis inzit.
GRATIS = plans.PLANS["gratis"]


def netto(prijs, btw=BTW):
    """Wat er van de consumentenprijs overblijft na btw en betaalkosten.

    De betaalkosten gaan over het hele bedrag dat de klant afrekent, inclusief
    btw - dat is wat er door de betaalterminal gaat.
    """
    if not prijs:
        return 0.0     # geen prijs, geen transactie, dus ook geen transactiekosten
    zonder_btw = prijs / (1 + btw)
    kosten = prijs * FEE_DEEL + FEE_VAST
    return zonder_btw - kosten


def kostprijs(dromen, rang, avatar_minuten=0):
    """Wat een maand van dit pakket ons kost als iemand alles opmaakt."""
    per_droom = next(k["kost"] for k in plans.KWALITEIT.values() if k["rang"] == rang)
    return dromen * per_droom + avatar_minuten * 0.18


def regel(naam, prijs, dromen, rang, avatar_minuten=0, btw=BTW):
    over = netto(prijs, btw)
    kost = kostprijs(dromen, rang, avatar_minuten)
    winst = over - kost
    return {
        "naam": naam,
        "prijs": prijs,
        "btw": prijs - prijs / (1 + btw),
        "fee": (prijs * FEE_DEEL + FEE_VAST) if prijs else 0.0,
        "over": over,
        "kost": kost,
        "winst": winst,
        "marge": (winst / prijs * 100) if prijs else 0.0,
    }


def toon(rijen, kop):
    print("\n" + kop)
    print("-" * 86)
    print("%-22s %8s %7s %7s %8s %8s %8s %7s" %
          ("", "prijs", "btw", "kosten", "over", "kostprs", "winst", "marge"))
    for r in rijen:
        print("%-22s %8.2f %7.2f %7.2f %8.2f %8.2f %8.2f %6.0f%%" %
              (r["naam"], r["prijs"], -r["btw"], -r["fee"], r["over"],
               -r["kost"], r["winst"], r["marge"]))


def nu(btw=BTW):
    rangen = plans.PLAN_RANG
    rijen = []
    for sleutel in ("plus", "ultra"):
        p = plans.PLANS[sleutel]
        rijen.append(regel(p["naam"] + " (alles opgemaakt)", p["prijs"], p["dromen"],
                           rangen[sleutel], p["avatar_minuten"], btw))
    toon(rijen, "ZOALS HET NU IS - iemand die zijn pakket helemaal opmaakt")

    # Niet iedereen maakt alles op. Bij zestig procent verbruik ziet het er
    # anders uit, en dat is het getal waar je op stuurt.
    rijen = []
    for sleutel in ("plus", "ultra"):
        p = plans.PLANS[sleutel]
        rijen.append(regel(p["naam"] + " (60% verbruikt)", p["prijs"],
                           round(p["dromen"] * 0.6, 1), rangen[sleutel],
                           p["avatar_minuten"] * 0.6, btw))
    toon(rijen, "REALISTISCHER - de meeste mensen maken hun pakket niet op")

    gratis_kost = kostprijs(GRATIS["dromen"], rangen["gratis"])
    print("\nEen gratis gebruiker kost EUR %.2f per maand." % gratis_kost)
    for sleutel in ("plus", "ultra"):
        p = plans.PLANS[sleutel]
        r = regel("", p["prijs"], p["dromen"], rangen[sleutel], p["avatar_minuten"], btw)
        if r["winst"] > 0:
            print("  Een %s die alles opmaakt draagt %.1f gratis gebruikers." %
                  (p["naam"], r["winst"] / gratis_kost))


def scan(btw=BTW):
    print("\nWAT BLIJFT ER OVER BIJ ANDERE PRIJZEN")
    print("Zes dromen per maand, iemand die alles opmaakt.\n")
    rangen = [(0, "duiding"), (1, "eenvoudig"), (2, "standaard"), (3, "supreme")]
    print("%-9s" % "prijs", end="")
    for _, naam in rangen:
        print("%12s" % naam, end="")
    print()
    print("-" * 57)
    for prijs in (4.99, 5.99, 6.99, 7.99, 8.99, 9.99, 11.99, 14.99):
        print("EUR %5.2f" % prijs, end="")
        for rang, _ in rangen:
            r = regel("", prijs, 6, rang, 0, btw)
            print("%11.0f%%" % r["marge"], end="")
        print()
    print("\nEen marge onder de 40% houdt geen bedrijf overeind: daar moeten")
    print("hosting, ondersteuning, terugboekingen en jouw uren nog uit.")


def voorstel(btw=BTW):
    """Een prijslijst die de btw en de betaalkosten wél overleeft.

    Wat de scan laat zien: het bewegende kernmoment is wat de marge opeet. Vijf
    getekende panelen kosten EUR 0,14 per droom, met het kernmoment erbij EUR
    0,69 - en bij zes dromen voor EUR 7,99 is de netto opbrengst per droom maar
    EUR 0,96. Dus hetzelfde besluit dat al voor de avatar gold: het kernmoment
    hoort niet onbeperkt in een pakket, het hoort op tokens.
    """
    rijen = [
        regel("Gratis (3x eenvoudig)", 0.00, 3, 1, 0, btw),
        regel("Plus (6x eenvoudig)", 7.99, 6, 1, 0, btw),
        regel("Ultra (10x standaard)", 29.99, 10, 2, 10, btw),
    ]
    toon(rijen, "VOORSTEL - het kernmoment uit het pakket, op tokens")


def tokens(btw=BTW):
    """Hoe groot moet een tokenpakket zijn om niet op verlies te draaien?

    De vaste EUR 0,46 per transactie is bij een klein bedrag moordend: wie voor
    EUR 0,50 twee tokens koopt, kost je geld. Tokens moeten dus in pakketten.
    """
    print("")
    print("TOKENS - de vaste kosten per transactie maken kleine bedragen onmogelijk")
    print("-" * 74)
    print("%-16s %8s %8s %8s %10s %10s" %
          ("pakket", "prijs", "netto", "p/token", "avatarmin", "supreme"))
    print("-" * 74)
    for aantal in (2, 10, 20, 40, 100):
        prijs = aantal * plans.EUR_PER_TOKEN
        over = netto(prijs, btw)
        per = over / aantal
        if over <= 0:
            # Bij een negatief bedrag zou een percentage omklappen en er goed
            # uitzien; dan liever het woord.
            print("%-16s %8.2f %8.2f %8s %10s %10s" %
                  ("%d tokens" % aantal, prijs, over, "-", "verlies", "verlies"))
            continue
        # Een avatarminuut kost twee tokens en ons EUR 0,18.
        m_avatar = (per * plans.TOKENS_PER_AVATAR_MINUTE - 0.18) / (per * 2) * 100
        # Supreme in plaats van standaard kost tien tokens en ons EUR 0,92 extra.
        m_supreme = (per * 10 - 0.92) / (per * 10) * 100
        print("%-16s %8.2f %8.2f %8.3f %9.0f%% %9.0f%%" %
              ("%d tokens" % aantal, prijs, over, per, m_avatar, m_supreme))
    print("")
    print("Onder de twintig tokens (EUR 5,00) is de marge te dun of negatief.")
    print("Verkoop tokens dus per twintig of meer, nooit per stuk.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scan", action="store_true", help="andere prijzen doorrekenen")
    ap.add_argument("--btw", type=float, default=21.0, help="btw-tarief in procenten")
    args = ap.parse_args()
    btw = args.btw / 100

    print("Btw %.0f%% | betaalkosten %.0f%% + EUR %.2f (merchant of record)"
          % (args.btw, FEE_DEEL * 100, FEE_VAST))
    nu(btw)
    if args.scan:
        scan(btw)
        voorstel(btw)
        tokens(btw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
