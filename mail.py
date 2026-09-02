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
"""

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr


def host():
    return os.environ.get("SMTP_HOST", "").strip()


def enabled():
    return bool(host())


def _van():
    rauw = os.environ.get("SMTP_VAN", "").strip()
    if rauw:
        naam, adres = parseaddr(rauw)
        if adres:
            return formataddr((naam or "Dreamverse", adres))
    gebruiker = os.environ.get("SMTP_USER", "").strip()
    return formataddr(("Dreamverse", gebruiker)) if gebruiker else "Dreamverse"


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

    poort = int(os.environ.get("SMTP_PORT") or 587)
    gebruiker = os.environ.get("SMTP_USER", "").strip()
    wachtwoord = os.environ.get("SMTP_PASSWORD", "")
    context = ssl.create_default_context()

    try:
        if poort == 465:
            with smtplib.SMTP_SSL(host(), poort, timeout=20, context=context) as s:
                if gebruiker:
                    s.login(gebruiker, wachtwoord)
                s.send_message(bericht)
        else:
            with smtplib.SMTP(host(), poort, timeout=20) as s:
                s.starttls(context=context)
                if gebruiker:
                    s.login(gebruiker, wachtwoord)
                s.send_message(bericht)
        print("mail: verstuurd aan {} ({})".format(naar, onderwerp), flush=True)
        return True
    except Exception as e:
        print("mail: versturen aan {} mislukte: {}".format(naar, str(e)[:200]), flush=True)
        return False


def herstelbericht(naar, link):
    return verstuur(
        naar,
        "Een nieuw wachtwoord voor Dreamverse",
        "Je hebt gevraagd om een nieuw wachtwoord voor Dreamverse.\n\n"
        "Open deze link om er een te kiezen:\n\n"
        "{}\n\n"
        "De link werkt een uur en daarna niet meer. Heb je dit niet gevraagd, dan\n"
        "hoef je niets te doen: je huidige wachtwoord blijft gewoon werken.\n".format(link),
    )
