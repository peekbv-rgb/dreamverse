"""E-mail versturen, als dat is ingesteld.

Zonder SMTP-gegevens doet deze module niets en zegt dat ook: `verstuur()` geeft
`False` terug en schrijft de tekst naar de log. Dat is bewust. Een knop
"wachtwoord vergeten" die stilletjes niets doet is erger dan geen knop, en een
app die niet start omdat er geen mailserver is, is nog erger.

Nodig in de omgeving:

    SMTP_HOST=smtp.jouwprovider.nl
    SMTP_PORT=587
    SMTP_USER=...
    SMTP_PASSWORD=...
    SMTP_VAN="Dreamverse <geen-antwoord@jouwdomein.nl>"

Poort 587 met STARTTLS is de gewone route; 465 is TLS vanaf de eerste byte en
wordt hier ook herkend.

    python mail.py --test jij@voorbeeld.nl

Met Gmail
---------

    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=dreamverse@gmail.com
    SMTP_PASSWORD=<app-wachtwoord van zestien tekens, zonder spaties>
    SMTP_VAN=Dreamverse <dreamverse@gmail.com>

Drie dingen die bij Gmail fout gaan:

1. **Je gewone wachtwoord werkt niet.** Google eist sinds 2022 een
   *app-wachtwoord*, en dat kun je alleen maken als tweestapsverificatie
   aanstaat. Het is zestien tekens; de spaties die Google erin zet mag je
   weglaten.
2. **Het afzenderadres moet je Gmail-adres zijn.** Zet je in SMTP_VAN een ander
   domein, dan weigert Gmail de mail of herschrijft hem. Deze module waarschuwt
   in de log als die twee niet overeenkomen.
3. **Een gratis Gmail mag ongeveer 500 berichten per dag**, en herstelmails van
   een gmail.com-adres komen bij ontvangers vaker in de spam dan mail van een
   eigen domein. Voor tien testpersonen prima; voor een product hoort daar een
   eigen verzenddomein met SPF en DKIM bij.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr


def host():
    return os.environ.get("SMTP_HOST", "").strip()


def wachtwoord():
    """Het wachtwoord, met de spaties eruit als het een app-wachtwoord is.

    Google toont een app-wachtwoord in vier groepjes van vier, en iedereen
    kopieert die spaties mee. Gmail zelf trekt zich er niets van aan, maar andere
    providers wel - dus hier weghalen, en alleen als het er ook echt een is:
    zestien tekens na het weghalen. Een wachtwoord met opzettelijke spaties
    erin blijft heel.
    """
    rauw = os.environ.get("SMTP_PASSWORD", "").strip()
    zonder = rauw.replace(" ", "")
    return zonder if len(zonder) == 16 and " " in rauw else rauw


def enabled():
    """Kan er echt verstuurd worden?

    Niet alleen kijken of er een server staat. Met een host maar zonder
    wachtwoord mislukt elke poging, en dan zegt de app "kijk in je mail" terwijl
    er niets is verstuurd. Dat is erger dan eerlijk zeggen dat het uitstaat.

    Een server zonder inloggegevens bestaat wel (een relay in je eigen netwerk),
    dus alleen als er een gebruiker is ingesteld hoort er ook een wachtwoord bij.
    """
    if not host():
        return False
    if os.environ.get("SMTP_USER", "").strip():
        return bool(wachtwoord())
    return True


def _van():
    rauw = os.environ.get("SMTP_VAN", "").strip()
    if rauw:
        naam, adres = parseaddr(rauw)
        if adres:
            return formataddr((naam or "Dreamverse", adres))
    gebruiker = os.environ.get("SMTP_USER", "").strip()
    return formataddr(("Dreamverse", gebruiker)) if gebruiker else "Dreamverse"


def _waarschuw_afzender():
    """Klopt het afzenderadres met het account waarmee we inloggen?

    Dit is de meest voorkomende oorzaak van "Sender address rejected": je logt
    in als de een en zet de ander als afzender. Providers als Gmail staan dat
    niet toe.
    """
    gebruiker = os.environ.get("SMTP_USER", "").strip()
    _, afzender = parseaddr(_van())
    if gebruiker and afzender and gebruiker.lower() != afzender.lower():
        print("mail: LET OP - je logt in als {} maar verstuurt namens {}. "
              "Veel providers, waaronder Gmail, weigeren dat.".format(
                  gebruiker, afzender), flush=True)


def verstuur(naar, onderwerp, tekst):
    """Eén bericht versturen. Geeft terug of het gelukt is.

    Nooit een uitzondering naar de aanroeper: een mail die niet aankomt mag geen
    verzoek laten klappen. Wat er misging staat in de log.
    """
    if not enabled():
        print("mail: SMTP staat niet ingesteld. Bericht aan {} niet verstuurd:\n"
              "--- {} ---\n{}\n---".format(naar, onderwerp, tekst), flush=True)
        return False

    bericht = EmailMessage()
    bericht["From"] = _van()
    bericht["To"] = naar
    bericht["Subject"] = onderwerp
    bericht.set_content(tekst)

    _waarschuw_afzender()
    poort = int(os.environ.get("SMTP_PORT") or 587)
    gebruiker = os.environ.get("SMTP_USER", "").strip()
    geheim = wachtwoord()
    context = ssl.create_default_context()

    try:
        if poort == 465:
            with smtplib.SMTP_SSL(host(), poort, timeout=20, context=context) as s:
                if gebruiker:
                    s.login(gebruiker, geheim)
                s.send_message(bericht)
        else:
            with smtplib.SMTP(host(), poort, timeout=20) as s:
                s.starttls(context=context)
                if gebruiker:
                    s.login(gebruiker, geheim)
                s.send_message(bericht)
        print("mail: verstuurd aan {} ({})".format(naar, onderwerp), flush=True)
        return True
    except smtplib.SMTPAuthenticationError as e:
        print("mail: inloggen bij {} geweigerd. Bij Gmail heb je een "
              "app-wachtwoord nodig, niet je gewone wachtwoord, en daarvoor moet "
              "tweestapsverificatie aanstaan. ({})".format(
                  host(), str(e)[:160]), flush=True)
        return False
    except Exception as e:
        print("mail: versturen aan {} mislukte: {}".format(naar, str(e)[:200]), flush=True)
        return False


HERSTEL = {
    "nl": (
        "Een nieuw wachtwoord voor Dreamverse",
        "Je hebt gevraagd om een nieuw wachtwoord voor Dreamverse.\n\n"
        "Open deze link om er een te kiezen:\n\n"
        "{link}\n\n"
        "De link werkt een uur en daarna niet meer. Heb je dit niet gevraagd,\n"
        "dan hoef je niets te doen: je huidige wachtwoord blijft gewoon werken.\n"
    ),
    "en": (
        "A new password for Dreamverse",
        "You asked for a new password for Dreamverse.\n\n"
        "Open this link to choose one:\n\n"
        "{link}\n\n"
        "The link works for one hour and then stops working. If you did not ask\n"
        "for this, you can ignore it: your current password keeps working.\n"
    ),
}


def herstelbericht(naar, link, taal="nl"):
    """De herstelmail, in de taal die de gebruiker in de app gekozen heeft.

    Iemand die de app in het Engels gebruikt en dan een Nederlandse mail krijgt,
    vertrouwt die mail niet - en bij een wachtwoordmail is vertrouwen precies
    waar het om gaat.
    """
    onderwerp, tekst = HERSTEL.get(taal, HERSTEL["nl"])
    return verstuur(naar, onderwerp, tekst.format(link=link))


def main():
    import argparse
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

    ap = argparse.ArgumentParser(description="Controleer of e-mail versturen werkt.")
    ap.add_argument("--test", metavar="ADRES", help="een proefbericht sturen")
    args = ap.parse_args()

    geheim = wachtwoord()
    print("SMTP_HOST     : %s" % (host() or "ONTBREEKT"))
    print("SMTP_PORT     : %s" % (os.environ.get("SMTP_PORT") or "587 (standaard)"))
    print("SMTP_USER     : %s" % (os.environ.get("SMTP_USER") or "ONTBREEKT"))
    print("SMTP_PASSWORD : %s" % ("staat er (%d tekens)" % len(geheim)
                                  if geheim else "ONTBREEKT"))
    print("afzender      : %s" % _van())

    if not enabled():
        print("")
        print("Zonder SMTP_HOST doet de app niets met mail; herstellinks gaan "
              "naar de log.")
        return 1

    _waarschuw_afzender()

    if not args.test:
        print("")
        print("Geef --test jij@voorbeeld.nl om echt een bericht te sturen.")
        return 0

    print("")
    print("Proefbericht versturen aan %s ..." % args.test)
    gelukt = verstuur(
        args.test, "Dreamverse: proefbericht",
        "Als je dit leest, werkt het versturen van e-mail.\n\n"
        "Daarmee werkt ook 'wachtwoord vergeten', en kan e-mailverificatie aan.\n")
    print("gelukt" if gelukt else "mislukt - de reden staat hierboven")
    return 0 if gelukt else 1


if __name__ == "__main__":
    raise SystemExit(main())
