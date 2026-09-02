"""Wat er in je pakket zit, en wat het kost als je meer wilt.

Hier worden de grenzen echt afgedwongen. Tot nu toe stonden de drie prijskaartjes
alleen als tekst in de pagina en kon iedereen alles; nu weigert de server.

Er is nog geen betaling. Pakket en tokensaldo staan gewoon in data/profile.json en
worden met de hand gezet. Dat is met opzet de volgorde: eerst moet kloppen wie wat
mag, daarna pas hoe er wordt afgerekend. Een betaalknop op een systeem dat niet
kan tellen levert alleen ruzie op.

De tarieven komen uit usage.py, dus wat hier "kost" heet is te herleiden tot een
echte factuur:

    droom, alleen stilstaande panelen        EUR 0,14
    droom met bewegend kernmoment (snel)     EUR 0,67
    droom met bewegend kernmoment (top)      EUR 1,59
    avatar, per gesprekminuut                EUR 0,18
    avatar, gesprek van vijf minuten         EUR 0,94

Video is duur en dat bepaalt de hele prijslijst. Vier seconden op het beste model
kost EUR 1,47; een hele verbeelding van twintig seconden kost EUR 7,36. Daarom
krijgt elke verbeelding een kernmoment en niet vijf, en daarom is een volledige
film iets dat je met tokens koopt in plaats van iets dat in een pakket zit.
"""

from datetime import datetime, timezone

import usage

# Eén token is EUR 0,25 bij verkoop. Bij EUR 0,18 kosten per gesprekminuut houdt
# twee tokens per minuut ongeveer 64% marge over.
EUR_PER_TOKEN = 0.25
TOKENS_PER_AVATAR_MINUTE = 2
TOKENS_PER_EXTRA_DREAM = 3

# Wat je los kunt kopen. De marges staan erbij omdat ze anders wegzakken zodra
# iemand een tarief aanpast.
EXTRAS = {
    "film_snel": {"naam": "Hele verbeelding als film, 20 seconden", "tokens": 30, "kost": 2.76},
    "film_top": {"naam": "Hele verbeelding als film op het beste model", "tokens": 60, "kost": 7.36},
    "kernmoment_top": {"naam": "Kernmoment op het beste model", "tokens": 10, "kost": 1.47},
}

# Welk videomodel hoort bij welk pakket. gen4_turbo laten we links liggen: dat is
# het model dat eruitzag als een bewegend plaatje.
VIDEO = {
    "geen": None,
    "snel": {"model": "veo3.1_fast", "audio": True, "seconden": 4, "kost": 0.55},
    "top": {"model": "veo3.1", "audio": True, "seconden": 4, "kost": 1.47},
}

# Wat je van een droom wilt. Alleen de duiding is bijna gratis; elke stap
# daarboven kost beeld en dus geld. Wat je pakket al dekt is inbegrepen, de rest
# betaal je met tokens.
KWALITEIT = {
    "duiding": {
        "naam_en": "Only the reading", "bevat_en": "text only",
        "uitleg_en": "The words, the memory and the look ahead. No images.",
        "bevat": "alleen tekst",
        "naam": "Alleen de duiding", "rang": 0, "panelen": False, "video": None,
        "tokens": 0, "kost": 0.04,
        "uitleg": "De tekst, het geheugen en de vooruitblik. Geen beeld.",
    },
    "eenvoudig": {
        "naam_en": "Simple", "bevat_en": "5 panels",
        "uitleg_en": "Five drawn panels with your dream.",
        "bevat": "5 panelen",
        "naam": "Eenvoudig", "rang": 1, "panelen": True, "video": None,
        "tokens": 1, "kost": 0.14,
        "uitleg": "Vijf getekende panelen bij je droom.",
    },
    "standaard": {
        "naam_en": "Standard", "bevat_en": "5 panels + key moment",
        "uitleg_en": "Five panels plus a moving key moment of four seconds.",
        "bevat": "5 panelen + kernmoment",
        "naam": "Standaard", "rang": 2, "panelen": True, "video": "snel",
        "tokens": 4, "kost": 0.69,
        "uitleg": "Vijf panelen plus een bewegend kernmoment van vier seconden.",
    },
    "supreme": {
        "naam_en": "Supreme", "bevat_en": "5 panels + best video",
        "uitleg_en": "The same, but the key moment on the best video model.",
        "bevat": "5 panelen + beste video",
        "naam": "Supreme", "rang": 3, "panelen": True, "video": "top",
        "tokens": 10, "kost": 1.61,
        "uitleg": "Hetzelfde, maar het kernmoment op het beste videomodel.",
    },
}
DEFAULT_KWALITEIT = "standaard"

# Tot welke rang je pakket je gratis brengt. Gratis reikt tot en met "eenvoudig":
# wie voor het eerst binnenkomt moet vijf getekende panelen bij zijn droom zien,
# anders begrijpt hij het product niet. Bewegend beeld begint bij het abonnement.
PLAN_RANG = {"gratis": 1, "lite": 1, "plus": 2, "ultra": 3}

PLANS = {
    "gratis": {
        "naam": "Gratis",
        "prijs": 0.00,
        # Eén droom, niet drie. Gratis is een proefje en geen abonnement: bij drie
        # dromen kostte een gratis gebruiker EUR 0,42 per maand, en vier van hen
        # aten één betalende op. Nu EUR 0,14.
        "dromen": 1,            # per maand
        "panelen": True,
        "video": "geen",
        "avatar_minuten": 0,    # alleen met tokens
    },
    "lite": {
        "naam": "Lite",
        # De instap. Bij een klein maandbedrag is de vaste $0,50 transactiekosten
        # het probleem en niet het percentage: op EUR 1,99 is dat 23% van de
        # prijs. Op EUR 2,99 met drie dromen blijft er 48% over.
        "prijs": 2.99,
        "dromen": 3,
        "panelen": True,
        "video": "geen",        # het kernmoment gaat op tokens
        "avatar_minuten": 0,
    },
    "plus": {
        "naam": "Plus",
        "prijs": 7.99,          # starttarief
        "dromen": 6,
        "panelen": True,
        "video": "snel",        # EUR 4,14 aan kosten, 48% marge
        "avatar_minuten": 0,
    },
    "ultra": {
        "naam": "Ultra",
        "prijs": 29.99,
        "dromen": 10,
        "panelen": True,
        "video": "top",         # EUR 17,77 aan kosten, 41% marge
        "avatar_minuten": 10,
    },
}

DEFAULT_PLAN = "gratis"


class Refused(Exception):
    """Mag niet, met een uitleg die de gebruiker te zien krijgt."""

    def __init__(self, message, need_tokens=0):
        super().__init__(message)
        self.need_tokens = need_tokens


def _month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def account():
    """Pakket, saldo en wat er deze maand al verbruikt is, van de ingelogde gebruiker.

    De tellers stonden eerst in usage.jsonl, dat één stroom voor de hele
    installatie is. Met accounts hoort dat per gebruiker, en dat staat nu in de
    gebruikerstabel: dromen_op en avatar_sec, die aan het begin van elke maand
    op nul gaan.
    """
    import accounts
    u = accounts.huidige()
    accounts.rol_maand_om(u["id"])
    u = accounts.gebruiker(u["id"])          # opnieuw lezen: de maand kan net omgerold zijn
    accounts.zet_huidige(u)

    key = u["pakket"] if u["pakket"] in PLANS else DEFAULT_PLAN
    plan = PLANS[key]
    maand = _month()
    dromen = u["dromen_op"]
    avatar_seconden = u["avatar_sec"]
    profile = {"tokens": u["tokens"]}

    inbegrepen_seconden = plan["avatar_minuten"] * 60
    return {
        "plan": key,
        "plan_naam": plan["naam"],
        "prijs": plan["prijs"],
        "tokens": int(profile.get("tokens", 0)),
        "maand": maand,
        "dromen_gebruikt": dromen,
        "dromen_inbegrepen": plan["dromen"],
        "dromen_over": max(0, plan["dromen"] - dromen),
        "panelen_inbegrepen": plan["panelen"],
        "video": plan["video"],
        "video_omschrijving": {
            "geen": "stilstaande panelen",
            "snel": "een bewegend kernmoment van vier seconden",
            "top": "een kernmoment van vier seconden op het beste model",
        }[plan["video"]],
        "avatar_seconden_gebruikt": avatar_seconden,
        "avatar_seconden_inbegrepen": inbegrepen_seconden,
        "avatar_seconden_over": max(0, inbegrepen_seconden - avatar_seconden),
        "tokens_per_minuut": TOKENS_PER_AVATAR_MINUTE,
        "tokens_per_extra_droom": TOKENS_PER_EXTRA_DREAM,
        "euro_per_token": EUR_PER_TOKEN,
    }


def set_plan(key):
    if key not in PLANS:
        raise Refused("Onbekend pakket.")
    import accounts
    accounts.zet_pakket(accounts.huidige()["id"], key)
    _verversen()
    return account()


def add_tokens(aantal):
    import accounts
    accounts.tel_op(accounts.huidige()["id"], tokens=int(aantal))
    _verversen()
    return account()


def _verversen():
    """De ingelogde gebruiker opnieuw uit de database halen.

    Zonder dit blijft account() het saldo van vóór de wijziging teruggeven, want
    de gebruiker in deze thread is een momentopname.
    """
    import accounts
    u = accounts.huidige_of_none()
    if u:
        accounts.zet_huidige(accounts.gebruiker(u["id"]))


# --------------------------------------------------------------------------- #
# De poortjes
# --------------------------------------------------------------------------- #

def kwaliteiten(taal="nl"):
    """Alle keuzes met wat ze deze gebruiker kosten, in zijn eigen taal."""
    a = account()
    eng = taal == "en"
    grens = PLAN_RANG.get(a["plan"], 0)
    saldo = a["tokens"]
    uit = []
    for sleutel, k in sorted(KWALITEIT.items(), key=lambda kv: kv[1]["rang"]):
        inbegrepen = k["rang"] <= grens
        tokens = 0 if inbegrepen else k["tokens"]
        uit.append({
            "key": sleutel,
            "naam": k["naam_en"] if eng else k["naam"],
            "uitleg": k["uitleg_en"] if eng else k["uitleg"],
            "bevat": k["bevat_en"] if eng else k["bevat"],
            "inbegrepen": inbegrepen, "tokens": tokens,
            # Alles onder je pakket valt er vanzelf ook in, dus "inbegrepen" bij
            # drie knoppen zegt niets. Alleen de hoogste die je hebt is nieuws.
            "beste": k["rang"] == grens,
            "betaalbaar": tokens == 0 or saldo >= tokens,
        })
    return uit


def check_kwaliteit(sleutel):
    """Mag deze kwaliteit? Geeft (instelling, tokens) terug."""
    if sleutel not in KWALITEIT:
        raise Refused("Die kwaliteit bestaat niet.")
    k = KWALITEIT[sleutel]
    a = account()
    if k["rang"] <= PLAN_RANG.get(a["plan"], 0):
        return k, 0
    if a["tokens"] >= k["tokens"]:
        return k, k["tokens"]
    raise Refused(
        "{} kost {} tokens en je hebt er {}. In je pakket {} zit {} inbegrepen.".format(
            k["naam"], k["tokens"], a["tokens"], a["plan_naam"], a["video_omschrijving"]),
        need_tokens=k["tokens"] - a["tokens"])


def check_dream():
    """Mag deze droom? Geeft terug hoeveel tokens het kost (0 als inbegrepen)."""
    a = account()
    if a["dromen_over"] > 0:
        return 0
    if a["tokens"] >= TOKENS_PER_EXTRA_DREAM:
        return TOKENS_PER_EXTRA_DREAM
    raise Refused(
        "Je {} dromen van deze maand zijn op. Een extra droom kost {} tokens en je "
        "hebt er {}.".format(a["dromen_inbegrepen"], TOKENS_PER_EXTRA_DREAM, a["tokens"]),
        need_tokens=TOKENS_PER_EXTRA_DREAM - a["tokens"],
    )


def panels_allowed():
    """Getekende illustraties zitten niet in het gratis pakket."""
    return account()["panelen_inbegrepen"]


def video_for_plan():
    """De video-instelling van het huidige pakket, of None bij gratis."""
    return VIDEO[account()["video"]]


def check_call():
    """Mag er gebeld worden, en hoe lang? Geeft de maximale duur in seconden."""
    a = account()
    if a["avatar_seconden_over"] >= 60:
        return a["avatar_seconden_over"], False

    betaalbare_minuten = a["tokens"] // TOKENS_PER_AVATAR_MINUTE
    if betaalbare_minuten >= 1:
        return betaalbare_minuten * 60, True

    raise Refused(
        "Praten met Vera kost {} tokens per minuut en je hebt er {}. "
        "Een gesprek van vijf minuten is {} tokens.".format(
            TOKENS_PER_AVATAR_MINUTE, a["tokens"], 5 * TOKENS_PER_AVATAR_MINUTE),
        need_tokens=TOKENS_PER_AVATAR_MINUTE - a["tokens"],
    )


def check_extra(soort):
    """Mag deze losse aankoop? Geeft het aantal tokens terug dat het kost."""
    if soort not in EXTRAS:
        raise Refused("Dat is niet te koop.")
    prijs = EXTRAS[soort]["tokens"]
    saldo = account()["tokens"]
    if saldo < prijs:
        raise Refused(
            "{} kost {} tokens en je hebt er {}.".format(EXTRAS[soort]["naam"], prijs, saldo),
            need_tokens=prijs - saldo)
    return prijs


def charge_extra(soort):
    prijs = EXTRAS[soort]["tokens"]
    add_tokens(-prijs)
    return prijs


def charge_dream(tokens):
    """Een droom afboeken: de maandteller omhoog, en tokens eraf als het er waren."""
    import accounts
    accounts.tel_op(accounts.huidige()["id"], dromen=1, tokens=-int(tokens or 0))
    _verversen()


def charge_call(seconds):
    """Afrekenen na afloop, op werkelijk gesproken tijd.

    Eerst de inbegrepen minuten opmaken, de rest uit tokens. Naar boven afronden
    per begonnen minuut — Runway rekent zelf ook per aangebroken zes seconden, en
    een gesprek van tien seconden kost jou al iets.
    """
    if seconds <= 0:
        return 0
    a = account()
    uit_pakket = min(seconds, a["avatar_seconden_over"])
    rest = seconds - uit_pakket
    if rest <= 0:
        import accounts
        accounts.tel_op(accounts.huidige()["id"], avatar_sec=seconds)
        _verversen()
        return 0
    minuten = -(-rest // 60)  # naar boven
    tokens = minuten * TOKENS_PER_AVATAR_MINUTE
    import accounts
    accounts.tel_op(accounts.huidige()["id"], avatar_sec=seconds, tokens=-tokens)
    _verversen()
    return tokens
