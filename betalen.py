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
# maakt een aankoop van twee tokens (EUR 0,50) verlieslatend. Vanaf twintig
# klopt het.
#
# De staffel loopt van EUR 0,35 naar EUR 0,25 per token - bijna dertig procent
# korting op het grote pakket. Hij loopt bewust naar beneden vanaf 0,35 en niet
# vanaf 0,25 naar beneden, en dat komt door een getal: een kernmoment op het
# beste model kost 10 tokens en ons EUR 1,47, dus EUR 0,147 per token. Netto
# houden we van EUR 0,25 per token ongeveer EUR 0,19 over, en daaronder wordt
# dat kernmoment verlieslatend. Wie zijn hele pakket aan kernmomenten uitgeeft
# is dus het slechtste geval, en ook dat blijft nu positief.
TOKENPAKKETTEN = {
    "tokens20": {"tokens": 20, "cent": 700, "naam": "20 tokens"},
    "tokens40": {"tokens": 40, "cent": 1200, "naam": "40 tokens"},
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

def _bestaand_product(c, merk):
    """Een product met deze naam, of None.

    Nodig omdat de instelwizard van Managed Payments je dwingt met de hand een
    eerste product te maken voordat je verder mag. Zou setup() daarna blind
    aanmaken, dan staat er een tweede "Dreamverse Lite" naast de eerste, hangen
    er twee prijzen aan hetzelfde pakket, en is achteraf niet meer te zien welke
    de klant betaalde.
    """
    try:
        lijst = c.v1.products.list(params={"limit": 100, "active": True})
    except Exception:
        return None
    for p in getattr(lijst, "data", []) or []:
        if getattr(p, "name", "") == merk:
            return p
    return None


def _prijs_erop(c, product, bedrag_cent, terugkerend=False):
    """Een nieuwe prijs aan een bestaand product hangen en die standaard maken.

    Een prijs is bij Stripe onveranderlijk; je maakt er een nieuwe naast. De
    oude blijft bestaan maar wordt niet meer aangeboden, en wie er al op betaalde
    houdt hem. Dat is precies de bedoeling.
    """
    gegevens = {
        "product": product.id,
        "unit_amount": bedrag_cent,
        "currency": "eur",
        "tax_behavior": "inclusive",
    }
    if terugkerend:
        gegevens["recurring"] = {"interval": "month"}
    prijs = c.v1.prices.create(gegevens)
    c.v1.products.update(product.id, params={"default_price": prijs.id})
    # De belastingcode van een handgemaakt product klopt zelden; die zetten we
    # hier alsnog goed, want Managed Payments rekent daarop af.
    try:
        c.v1.products.update(product.id, params={"tax_code": BELASTINGCODE})
    except Exception as e:
        print("     let op: belastingcode niet gezet (%s)" % str(e)[:80])
    return prijs.id


def setup():
    """Maak de producten en prijzen in Stripe en druk de id's af.

    Eenmalig per omgeving; live en sandbox hebben elk hun eigen id's, dus die
    staan in .env en niet in de code.

    Bestaat een product al onder dezelfde naam, dan wordt dat hergebruikt en
    krijgt het alleen een nieuwe prijs. Zo kun je dit veilig nog eens draaien,
    en zo pikt hij ook het product op dat de wizard van Managed Payments je
    dwong met de hand te maken.
    """
    if not enabled():
        sys.exit("Geen STRIPE_SECRET_KEY in de omgeving.")
    c = klant()
    regels = []
    print("Account: %s" % modus())
    print("")

    for naam in ABONNEMENTEN:
        p = plans.PLANS[naam]
        merk = "Dreamverse {}".format(p["naam"])
        cent = int(round(p["prijs"] * 100))
        bestaand = _bestaand_product(c, merk)
        if bestaand is not None:
            prijs_id = _prijs_erop(c, bestaand, cent, terugkerend=True)
            print("  %-22s %s  (hergebruikt %s)" % (merk, prijs_id, bestaand.id))
        else:
            product = c.v1.products.create({
                "name": merk,
                "description": "{} dromen per maand met de volledige duiding.".format(p["dromen"]),
                "tax_code": BELASTINGCODE,
                "default_price_data": {
                    "unit_amount": cent,
                    "currency": "eur",
                    # inclusive: de getoonde prijs is wat de klant betaalt.
                    "tax_behavior": "inclusive",
                    "recurring": {"interval": "month"},
                },
            })
            prijs_id = product.default_price
            print("  %-22s %s  (nieuw %s)" % (merk, prijs_id, product.id))
        regels.append(("STRIPE_PRICE_{}".format(naam.upper()), prijs_id))

    for naam, pak in TOKENPAKKETTEN.items():
        merk = "Dreamverse {}".format(pak["naam"])
        bestaand = _bestaand_product(c, merk)
        if bestaand is not None:
            prijs_id = _prijs_erop(c, bestaand, pak["cent"])
            print("  %-22s %s  (hergebruikt %s)" % (merk, prijs_id, bestaand.id))
        else:
            product = c.v1.products.create({
                "name": merk,
                "description": "Tegoed voor een bewegend kernmoment, een gesprek met "
                               "Vera of een extra droom.",
                "tax_code": BELASTINGCODE,
                "default_price_data": {
                    "unit_amount": pak["cent"],
                    "currency": "eur",
                    "tax_behavior": "inclusive",
                },
            })
            prijs_id = product.default_price
            print("  %-22s %s  (nieuw %s)" % (merk, prijs_id, product.id))
        regels.append(("STRIPE_PRICE_{}".format(naam.upper()), prijs_id))

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
    c = klant()

    # Bestaat de bewaarde klant nog? Bij de overstap van sandbox naar live niet:
    # een cus_... uit de sandbox bestaat in het live-account eenvoudigweg niet,
    # en dan mislukt elke afrekensessie met "No such customer" - een 502 en een
    # knop die niets doet, precies op het moment dat iemand wil betalen.
    #
    # Dat is niet met een migratie op te lossen: het zijn twee losse werelden en
    # het kan bij elke sleutelwissel opnieuw. Dus controleren we het hier, en
    # maken we er stilzwijgend een nieuwe aan als de oude weg is. De ene extra
    # aanroep per aankoop weegt niet op tegen een betaling die niet doorgaat.
    if user.get("stripe_klant"):
        try:
            bestaand = c.v1.customers.retrieve(user["stripe_klant"])
            if not getattr(bestaand, "deleted", False):
                return bestaand.id
        except Exception as e:
            print("stripe-klant {} bestaat hier niet ({}); we maken een nieuwe".format(
                user["stripe_klant"], str(e)[:80]), flush=True)

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
        gebeurtenis = stripe.Webhook.construct_event(lichaam, handtekening, geheim)
        # Als gewoon woordenboek verder, want de nieuwere SDK weigert .get() op
        # zijn eigen objecten: "'get' is a dict method, but a Session is not a
        # dict". Dat liet de eerste echte betaling stuklopen - het geld binnen,
        # het pakket niet omgezet - en de foutafhandeling zelf viel er ook over,
        # want die deed gebeurtenis.get("type"). Eén omzetting hier houdt alles
        # erachter simpel en laat het niet afhangen van de SDK-versie.
        if hasattr(gebeurtenis, "to_dict"):
            # to_dict() gaat diep genoeg: data.object komt er als gewoon
            # woordenboek uit. dict() eromheen werkt niet, want een Event is
            # geen mapping.
            return gebeurtenis.to_dict()
        return gebeurtenis
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


def tokenprijzen():
    """Alleen de drie tokenpakketten opnieuw prijzen.

    `--setup` maakt alles opnieuw aan, ook de abonnementen, en laat dan zes
    verweesde producten achter. Als je alleen de tokenprijzen aanpast wil je dat
    niet: je krijgt een catalogus vol dubbelingen en je weet straks niet meer
    welk product bij welke prijs hoort.

    Deze zoekt het bestaande product op naam op en hangt er een nieuwe prijs aan.
    Een prijs bij Stripe is onveranderlijk - je maakt er een nieuwe en zet die als
    standaard; de oude blijft bestaan maar wordt niet meer gebruikt. Dat is ook
    precies wat je wilt: wie gisteren betaalde hield zijn eigen prijs.
    """
    import stripe
    if not enabled():
        print("Geen STRIPE_SECRET_KEY in de omgeving.")
        return 1
    c = klant()

    print("Account: %s" % modus())
    print("")
    regels = []
    for naam, pak in TOKENPAKKETTEN.items():
        merk = "Dreamverse {}".format(pak["naam"])

        # Het bestaande product zoeken. Zonder is er niets om aan te hangen en
        # maken we er alsnog een - dan is dit de eerste keer.
        product = None
        try:
            lijst = c.v1.products.list(params={"limit": 100, "active": True})
            for p in getattr(lijst, "data", []) or []:
                if getattr(p, "name", "") == merk:
                    product = p
                    break
        except Exception as e:
            print("Producten ophalen mislukte: %s" % str(e)[:160])
            return 1

        if product is None:
            product = c.v1.products.create({
                "name": merk,
                "description": "Tegoed voor een bewegend kernmoment, een gesprek "
                               "met Vera of een extra droom.",
                "tax_code": BELASTINGCODE,
                "default_price_data": {
                    "unit_amount": pak["cent"],
                    "currency": "eur",
                    "tax_behavior": "inclusive",
                },
            })
            prijs_id = product.default_price
            print("  %-22s nieuw product   %s" % (merk, prijs_id))
        else:
            oud = getattr(product, "default_price", None)
            prijs = c.v1.prices.create({
                "product": product.id,
                "unit_amount": pak["cent"],
                "currency": "eur",
                "tax_behavior": "inclusive",
            })
            c.v1.products.update(product.id, params={"default_price": prijs.id})
            prijs_id = prijs.id
            print("  %-22s EUR %5.2f       %s   (was %s)" % (
                merk, pak["cent"] / 100, prijs_id, oud))

        regels.append(("STRIPE_PRICE_{}".format(naam.upper()), prijs_id))

    print("")
    print("Zet dit in Render onder Environment (en in .env als je lokaal test):")
    print("")
    for k, v in regels:
        print("%s=%s" % (k, v))
    print("")
    print("De oude prijzen blijven bestaan maar worden niet meer gebruikt. Wie er")
    print("al op betaalde houdt zijn eigen prijs; dat is bij Stripe zo bedoeld.")
    return 0


def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="staat alles klaar?")
    ap.add_argument("--setup", action="store_true", help="producten en prijzen aanmaken")
    ap.add_argument("--webhooks", action="store_true",
                    help="welke endpoints staan er, en in welk account?")
    ap.add_argument("--tokenprijzen", action="store_true",
                    help="alleen de drie tokenpakketten opnieuw prijzen")
    args = ap.parse_args()
    if args.setup:
        return setup()
    if args.tokenprijzen:
        return tokenprijzen()
    if args.webhooks:
        return webhooks()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
