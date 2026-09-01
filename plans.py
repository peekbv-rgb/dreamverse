"""Wat er in je pakket zit, en wat het kost als je meer wilt.

Hier worden de grenzen echt afgedwongen. Tot nu toe stonden de drie prijskaartjes
alleen als tekst in de pagina en kon iedereen alles; nu weigert de server.

Er is nog geen betaling. Pakket en tokensaldo staan gewoon in data/profile.json en
worden met de hand gezet. Dat is met opzet de volgorde: eerst moet kloppen wie wat
mag, daarna pas hoe er wordt afgerekend. Een betaalknop op een systeem dat niet
kan tellen levert alleen ruzie op.

De tarieven komen uit usage.py, dus wat hier "kost" heet is te herleiden tot een
echte factuur:

    droom (tekst + vijf panelen)   ongeveer EUR 0,15
    avatar, per gesprekminuut      EUR 0,18
    avatar, gesprek van vijf min   EUR 0,94

Daarom zit de avatar in geen enkel vast pakket volledig inbegrepen: bij EUR 4,99
per maand is een gesprek van vijf minuten al een vijfde van je omzet.
"""

from datetime import datetime, timezone

import usage

# Eén token is EUR 0,25 bij verkoop. Bij EUR 0,18 kosten per gesprekminuut houdt
# twee tokens per minuut ongeveer 64% marge over.
EUR_PER_TOKEN = 0.25
TOKENS_PER_AVATAR_MINUTE = 2
TOKENS_PER_EXTRA_DREAM = 2

PLANS = {
    "gratis": {
        "naam": "Gratis",
        "prijs": 0.00,
        "dromen": 3,            # per maand
        "panelen": False,       # alleen de getekende composities
        "avatar_minuten": 0,    # alleen met tokens
    },
    "plus": {
        "naam": "Plus",
        "prijs": 4.99,
        "dromen": 10,
        "panelen": True,
        "avatar_minuten": 0,    # bewust nul: EUR 0,94 per gesprek past hier niet in
    },
    "ultra": {
        "naam": "Ultra",
        "prijs": 17.99,
        "dromen": 30,
        "panelen": True,
        "avatar_minuten": 10,   # EUR 1,88 aan kosten, ruim 10% van de prijs
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
    """Pakket, saldo en wat er deze maand al verbruikt is."""
    import dreamverse
    profile = dreamverse.load_profile()
    key = profile.get("plan") if profile.get("plan") in PLANS else DEFAULT_PLAN
    plan = PLANS[key]

    maand = _month()
    dromen = 0
    avatar_seconden = 0
    for rec in usage.read():
        if not (rec.get("at") or "").startswith(maand):
            continue
        if rec.get("kind") == "episode":
            dromen += 1
        elif rec.get("kind") == "session_end":
            avatar_seconden += rec.get("seconds", 0)

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
    import dreamverse
    with dreamverse._lock:
        profile = dreamverse.load_profile()
        profile["plan"] = key
        dreamverse.save_profile(profile)
    return account()


def add_tokens(aantal):
    import dreamverse
    with dreamverse._lock:
        profile = dreamverse.load_profile()
        profile["tokens"] = max(0, int(profile.get("tokens", 0)) + int(aantal))
        dreamverse.save_profile(profile)
    return account()


# --------------------------------------------------------------------------- #
# De poortjes
# --------------------------------------------------------------------------- #

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


def charge_dream(tokens):
    if tokens:
        add_tokens(-tokens)


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
        return 0
    minuten = -(-rest // 60)  # naar boven
    tokens = minuten * TOKENS_PER_AVATAR_MINUTE
    add_tokens(-tokens)
    return tokens
