"""Afrekenen via Stripe Managed Payments.

    python betalen.py --check      # staat alles klaar?
    python betalen.py --setup      # producten en prijzen aanmaken in Stripe

Managed Payments betekent dat **Stripe de verkoper is**, niet wij. Zij innen de
btw en dragen hem af in ruim tachtig landen. Dat kost 5% + $0,50 per transactie
in plaats van de ongeveer 1,5% + €0,25 van gewoon Stripe, en dat verschil koop je
bewust: zelf OSS-aangifte doen over 27 btw-tarieven kost meer tijd en
accountantsgeld dan het scheelt.

Drie dingen die makkelijk fout gaan en hier daarom expliciet staan.

**tax_behavior is `inclusive`.** Zonder die instelling telt Stripe de btw *boven
op* je prijs, en rekent een klant bij € 7,99 dus € 9,67 af. Voor een
consumentenapp hoort de getoonde prijs de prijs te zijn die je betaalt.

**De belastingcode is `txcd_10105001`** — AI as a Service, cloud, particulier
gebruik. Managed Payments accepteert alleen codes uit een vaste lijst, en met de
verkeerde code kloppen de tarieven niet.

**Elke webhook wordt één keer verwerkt.** Stripe stuurt opnieuw als hij geen 200
terugkrijgt, en soms twee keer zonder aanleiding. Het gebeurtenis-id gaat in de
tabel `betalingen`; komt hij nog eens langs, dan gebeurt er niets.
"""

import argparse
import json
import os
import sys

import accounts
import plans

# AI as a Service, cloud based, personal use. Een van de codes die Managed
# Payments toestaat; met een andere code klopt de btw niet.
BELASTINGCODE = "txcd_10105001"

# De abonnementen. De sleutel is het pakket in plans.py.
ABONNEMENTEN = ("lite", "plus", "ultra")

# De tokenpakketten. Losse tokens kunnen niet: de vaste $0,50 per transactie
# maakt een aankoop van twee tokens (€0,50) verlieslatend. Vanaf twintig klopt
# het, en groter kopen wordt iets voordeliger per token.
TOKENPAKKETTEN = {
    "tokens20": {"tokens": 20, "cent": 500, "naam": "20 tokens"},
    "tokens40": {"tokens": 40, "cent": 1000, "naam": "40 tokens"},
    "tokens100": {"tokens": 100, "cent": 2500, "naam": "100 tokens"},
}


def sleutel():
    return os.environ.get("STRIPE_SECRET_KEY", "").strip()


def enabled():
    return bool(sleutel())


def webhook_geheim():
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()


def basis_url():
    """Waar Stripe de klant naartoe terugstuurt."""
    return (os.environ.get("PUBLIEKE_URL") or "http://127.0.0.1:8000").rstrip("/")


def prijs_id(naam):
    """Het prijs-id uit de omgeving: STRIPE_PRICE_PLUS, STRIPE_PRICE_TOKENS20, ..."""
    return os.environ.get("STRIPE_PRICE_{}".format(naam.upper()), "").strip()


class BetaalError(Exception):
    """Iets ging mis; de melding is bedoeld voor de gebruiker."""


def klant():
    import stripe
    return stripe.StripeClient(sleutel())


# --------------------------------------------------------------------------- #
# Producten en prijzen aanmaken
# --------------------------------------------------------------------------- #

def setup():
    """Maak de producten en prijzen in Stripe en druk de id's af.

    Eenmalig, per omgeving. De id's komen in .env; ze staan niet in de code,
    want een test- en een productieomgeving hebben andere id's.
    """
    if not enabled():
        sys.exit("Geen STRIPE_SECRET_KEY in de omgeving.")
    c = klant()
    regels = []

    for naam in ABONNEMENTEN:
        p = plans.PLANS[naam]
        product = c.v1.products.create({
            "name": "Dreamverse {}".format(p["naam"]),
            "description": "{} dromen per maand met de volledige duiding.".format(p["dromen"]),
            "tax_code": BELASTINGCODE,
            "default_price_data": {
                "unit_amount": int(round(p["prijs"] * 100)),
                "currency": "eur",
                # inclusive: de getoonde prijs is wat de klant betaalt.
                "tax_behavior": "inclusive",
                "recurring": {"interval": "month"},
            },
        })
        regels.append(("STRIPE_PRICE_{}".format(naam.upper()), product.default_price))
        print("  %-22s %s  (%s)" % (product.name, product.default_price, product.id))

    for naam, pak in TOKENPAKKETTEN.items():
        product = c.v1.products.create({
            "name": "Dreamverse {}".format(pak["naam"]),
            "description": "Tegoed voor een bewegend kernmoment, een gesprek met "
                           "Vera of een extra droom.",
            "tax_code": BELASTINGCODE,
            "default_price_data": {
                "unit_amount": pak["cent"],
                "currency": "eur",
                "tax_behavior": "inclusive",
            },
        })
        regels.append(("STRIPE_PRICE_{}".format(naam.upper()), product.default_price))
        print("  %-22s %s  (%s)" % (product.name, product.default_price, product.id))

    print("\nZet dit in .env:\n")
    for k, v in regels:
        print("%s=%s" % (k, v))
    return 0


# --------------------------------------------------------------------------- #
# Afrekenen
# --------------------------------------------------------------------------- #

def _klant_id(user):
    """Het Stripe-klantnummer van deze gebruiker; maak het aan als het er niet is.

    Eén klant per gebruiker, hergebruikt bij elke aankoop. Anders krijgt iemand
    bij zijn tweede aankoop een tweede klantdossier en klopt het abonnement niet
    meer bij het saldo.
    """
    if user.get("stripe_klant"):
        return user["stripe_klant"]
    c = klant()
    gemaakt = c.v1.customers.create({
        "email": user["email"],
        "name": user["naam"] or None,
        "metadata": {"dreamverse_user": str(user["id"])},
    })
    accounts.zet_stripe_klant(user["id"], gemaakt.id)
    return gemaakt.id


def _sessie(user, prijs, modus, soort, waarde):
    if not enabled():
        raise BetaalError("Afrekenen staat nog niet aan.")
    if not prijs:
        raise BetaalError("Voor dit product is nog geen prijs ingesteld.")
    c = klant()
    sessie = c.v1.checkout.sessions.create({
        "mode": modus,
        "line_items": [{"price": prijs, "quantity": 1}],
        # Stripe wordt de verkoper en draagt de btw af.
        "managed_payments": {"enabled": True},
        "customer": _klant_id(user),
        "success_url": basis_url() + "/?betaald=1",
        "cancel_url": basis_url() + "/?betaald=0",
        # In de metadata staat wie het was en wat hij kocht. De webhook heeft dat
        # nodig: die komt binnen zonder sessie en moet weten bij wie het hoort.
        "metadata": {"dreamverse_user": str(user["id"]), "soort": soort,
                     "waarde": str(waarde)},
        "subscription_data": ({"metadata": {"dreamverse_user": str(user["id"]),
                                            "soort": soort, "waarde": str(waarde)}}
                              if modus == "subscription" else None),
    })
    return sessie.url


def koop_pakket(user, pakket):
    if pakket not in ABONNEMENTEN:
        raise BetaalError("Dat pakket is niet te koop.")
    return _sessie(user, prijs_id(pakket), "subscription", "pakket", pakket)


def koop_tokens(user, welk):
    if welk not in TOKENPAKKETTEN:
        raise BetaalError("Dat tokenpakket bestaat niet.")
    return _sessie(user, prijs_id(welk), "payment", "tokens",
                   TOKENPAKKETTEN[welk]["tokens"])


def zeg_op(abo_id):
    """Een abonnement meteen beëindigen.

    Niet "aan het eind van de periode": wie zijn account verwijdert wil niet
    volgende maand nog een afschrijving zien van iets wat niet meer bestaat.
    """
    if not enabled() or not abo_id:
        return False
    klant().v1.subscriptions.cancel(abo_id)
    return True


def portaal(user):
    """De pagina van Stripe waar je je abonnement opzegt of je kaart wijzigt.

    Zelf bouwen zou betekenen dat wij opzeggen, wijzigen en facturen moeten
    afhandelen. Dat is precies wat je niet zelf wilt doen.
    """
    if not user.get("stripe_klant"):
        raise BetaalError("Er is nog niets gekocht met dit account.")
    c = klant()
    sessie = c.v1.billing_portal.sessions.create({
        "customer": user["stripe_klant"],
        "return_url": basis_url() + "/",
    })
    return sessie.url


# --------------------------------------------------------------------------- #
# De webhook
# --------------------------------------------------------------------------- #

def lees_gebeurtenis(lichaam, handtekening):
    """De melding van Stripe openen, met controle op de handtekening.

    Zonder die controle kan iedereen die het adres kent zichzelf Ultra geven met
    een nagemaakt bericht. Dit is het gevaarlijkste eindpunt van de hele app.
    """
    import stripe
    geheim = webhook_geheim()
    if not geheim:
        raise BetaalError("STRIPE_WEBHOOK_SECRET ontbreekt; meldingen worden geweigerd.")
    try:
        return stripe.Webhook.construct_event(lichaam, handtekening, geheim)
    except ValueError:
        raise BetaalError("Onleesbare melding.")
    except stripe.SignatureVerificationError as e:
        # Twee heel verschillende oorzaken achter een en dezelfde fout, en het
        # scheelt uren om te weten welke. Een klok die uit de pas loopt repareer
        # je bij de server; een geheim dat bij een andere endpoint hoort repareer
        # je in de omgeving.
        if "tolerance" in str(e).lower():
            raise BetaalError("De melding is te oud; de klok van de server loopt uit de pas.")
        raise BetaalError(
            "De handtekening klopt niet. Bijna altijd hoort STRIPE_WEBHOOK_SECRET "
            "bij een andere endpoint dan degene die dit stuurt - sandbox en live "
            "hebben elk hun eigen geheim. Draai `python betalen.py --webhooks`.")


def _gebruiker_uit(obj):
    """Bij wie hoort deze gebeurtenis?

    Eerst de metadata, want die zetten we zelf. Anders het klantnummer, want dat
    hangt bij Stripe aan de gebruiker. Lukt het allebei niet, dan doen we niets -
    liever een melding laten liggen dan het pakket van de verkeerde aanpassen.
    """
    meta = obj.get("metadata") or {}
    if meta.get("dreamverse_user"):
        try:
            return accounts.gebruiker(int(meta["dreamverse_user"]))
        except (ValueError, TypeError):
            pass
    if obj.get("customer"):
        return accounts.bij_stripe_klant(obj["customer"])
    return None


def verwerk(gebeurtenis):
    """Wat er moet gebeuren na een betaling. Geeft een korte omschrijving terug."""
    soort = gebeurtenis["type"]
    obj = gebeurtenis["data"]["object"]

    if accounts.al_verwerkt(gebeurtenis["id"]):
        return "al verwerkt"

    if soort == "checkout.session.completed":
        user = _gebruiker_uit(obj)
        if not user:
            return "geen gebruiker gevonden"
        meta = obj.get("metadata") or {}
        if obj.get("customer"):
            accounts.zet_stripe_klant(user["id"], obj["customer"])

        if meta.get("soort") == "tokens":
            aantal = int(meta.get("waarde") or 0)
            accounts.tel_op(user["id"], tokens=aantal)
            accounts.boek_betaling(gebeurtenis["id"], user["id"], "tokens",
                                   obj.get("amount_total") or 0,
                                   obj.get("currency") or "eur", json.dumps(meta))
            return "{} tokens bijgeschreven voor {}".format(aantal, user["email"])

        if meta.get("soort") == "pakket":
            pakket = meta.get("waarde") or "gratis"
            accounts.zet_pakket(user["id"], pakket, abo=obj.get("subscription") or "")
            accounts.boek_betaling(gebeurtenis["id"], user["id"], "pakket",
                                   obj.get("amount_total") or 0,
                                   obj.get("currency") or "eur", json.dumps(meta))
            return "pakket {} voor {}".format(pakket, user["email"])
        return "onbekende aankoop"

    if soort in ("customer.subscription.updated", "customer.subscription.deleted"):
        user = accounts.bij_stripe_abo(obj.get("id") or "") or _gebruiker_uit(obj)
        if not user:
            return "geen gebruiker gevonden"
        staat = obj.get("status")
        # active en trialing horen bij een lopend abonnement. Al het andere -
        # opgezegd, onbetaald, verlopen - valt terug naar gratis. Niet meteen
        # bij "past_due": Stripe probeert dan nog een paar keer te incasseren.
        if staat in ("active", "trialing"):
            meta = obj.get("metadata") or {}
            pakket = meta.get("waarde")
            if pakket in ABONNEMENTEN:
                accounts.zet_pakket(user["id"], pakket, abo=obj.get("id") or "")
            return "abonnement loopt ({})".format(staat)
        if staat in ("canceled", "unpaid", "incomplete_expired"):
            accounts.zet_pakket(user["id"], "gratis", abo="")
            accounts.boek_betaling(gebeurtenis["id"], user["id"], "opgezegd", 0, "eur",
                                   json.dumps({"status": staat}))
            return "terug naar gratis voor {} ({})".format(user["email"], staat)
        return "abonnement staat op {}".format(staat)

    return "niets te doen voor {}".format(soort)


# --------------------------------------------------------------------------- #
# Controle vanaf de opdrachtregel
# --------------------------------------------------------------------------- #

def check():
    print("sleutel        : %s" % ("staat er" if enabled() else "ONTBREEKT"))
    print("webhookgeheim  : %s" % ("staat er" if webhook_geheim() else "ONTBREEKT"))
    print("terugkeer-url  : %s" % basis_url())
    print("belastingcode  : %s" % BELASTINGCODE)
    print("\nprijzen:")
    ontbreekt = 0
    for naam in list(ABONNEMENTEN) + list(TOKENPAKKETTEN):
        p = prijs_id(naam)
        print("  %-12s %s" % (naam, p or "ONTBREEKT"))
        ontbreekt += 0 if p else 1
    if not enabled():
        return 1
    try:
        c = klant()
        saldo = c.v1.balance.retrieve()
        print("\nverbinding met Stripe: in orde (%s)" %
              ("sandbox" if sleutel().startswith("sk_test") else "LIVE"))
    except Exception as e:
        print("\nverbinding met Stripe mislukte: %s" % str(e)[:160])
        return 1
    if ontbreekt:
        print("\n%d prijzen ontbreken. Draai: python betalen.py --setup" % ontbreekt)
    return 0


def modus():
    """Sandbox of live? Dat staat in de sleutel zelf."""
    s = sleutel()
    if s.startswith("sk_test_") or s.startswith("rk_test_"):
        return "sandbox"
    if s.startswith("sk_live_") or s.startswith("rk_live_"):
        return "live"
    return "onbekend"


def webhooks():
    """De webhook-endpoints van dit account op een rij.

    Dit bestaat omdat een verkeerd geheim er precies hetzelfde uitziet als een
    nagemaakte melding: `SignatureVerificationError`, en niets zegt welke van de
    twee het is. Het gebeurde ook echt - een endpoint aangemaakt in het
    live-account terwijl de app op de sandbox draait, en dan wordt elke betaling
    geweigerd terwijl Stripe zegt dat hij hem heeft afgeleverd.

    De ondertekengeheimen staan hier niet in: Stripe geeft ze alleen bij het
    aanmaken terug, en een geheim in een terminal is een geheim in je
    shell-geschiedenis. Wat je hier ziet is genoeg om te weten of je in het
    juiste account kijkt.
    """
    import stripe
    if not enabled():
        print("STRIPE_SECRET_KEY ontbreekt.")
        return 1

    doel = basis_url() + "/api/stripe/webhook"
    print("Dit account       : %s" % modus())
    print("Verwachte URL     : %s" % doel)
    geheim = webhook_geheim()
    print("STRIPE_WEBHOOK_SECRET: %s" % (
        "staat er (%d tekens%s)" % (
            len(geheim), ", begint met whsec_" if geheim.startswith("whsec_") else
            ", begint NIET met whsec_ - dat is geen ondertekengeheim")
        if geheim else "ONTBREEKT - dan wordt elke melding geweigerd"))
    print("")

    try:
        lijst = stripe.StripeClient(sleutel()).v1.webhook_endpoints.list(params={"limit": 50})
    except Exception as e:
        print("Ophalen mislukte: %s" % str(e)[:200])
        return 1

    endpoints = list(getattr(lijst, "data", []) or [])
    if not endpoints:
        print("Dit account heeft GEEN webhook-endpoints.")
        print("")
        print("Dat is de storing: Stripe stuurt dan niets, of je endpoint staat in")
        print("het andere account (sandbox tegenover live). Maak hem aan in het")
        print("account dat hierboven staat, op de verwachte URL.")
        return 1

    raak = False
    for e in endpoints:
        # Een WebhookEndpoint is geen dict; attributen dus, niet .get().
        url = getattr(e, "url", "") or ""
        stand = getattr(e, "status", "?")
        soorten = getattr(e, "enabled_events", None) or []
        hier = url == doel
        raak = raak or hier
        print("  %s%s" % ("-> " if hier else "   ", url))
        print("     %s | %s" % (getattr(e, "id", "?"), stand))
        print("     %s" % (", ".join(soorten) if soorten else "GEEN gebeurtenissen"))
        if stand != "enabled":
            print("     LET OP: deze endpoint staat uit.")
        if "checkout.session.completed" not in soorten:
            print("     LET OP: checkout.session.completed staat er niet bij, en dat")
            print("     is degene die een pakket laat omslaan na een aankoop.")

    print("")
    if not raak:
        print("Geen endpoint op %s." % doel)
        print("Dat is hier geen storing als je dit op je eigen machine draait:")
        print("PUBLIEKE_URL staat lokaal op 127.0.0.1 en daar kan Stripe niet bij.")
        print("Vergelijk de URL's hierboven met de plek waar de app echt draait.")
        print("")

    print("Wordt er geweigerd op de handtekening terwijl de endpoint hierboven")
    print("staat, dan hoort STRIPE_WEBHOOK_SECRET bij een ándere endpoint - de")
    print("endpoint die je eerst in het live-account maakte, bijvoorbeeld. Elk")
    print("endpoint heeft zijn eigen geheim, en aan het geheim zelf is niet te")
    print("zien bij welke het hoort. Open de endpoint bij Stripe, 'Reveal' bij het")
    print("ondertekengeheim, en zet precies dat in de omgeving van de server.")
    return 0


def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="staat alles klaar?")
    ap.add_argument("--setup", action="store_true", help="producten en prijzen aanmaken")
    ap.add_argument("--webhooks", action="store_true",
                    help="welke endpoints staan er, en in welk account?")
    args = ap.parse_args()
    if args.setup:
        return setup()
    if args.webhooks:
        return webhooks()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
