"""Accounts: wie is er ingelogd, en wat is van wie.

Tot nu toe was er één profiel per installatie: `data/profile.json` met een naam,
een pakket en een tokensaldo, en één `data/archive.json` met alle dromen. Dat
werkt zolang jij de enige gebruiker bent. Geef je tien mensen een link, dan
dromen ze in hetzelfde archief en zien ze elkaars nachten.

Hier staat de gebruikerslaag. SQLite, uit de standaardbibliotheek: geen nieuwe
afhankelijkheid, en het is precies waar het voor gemaakt is — één bestand op de
schijf van Render, met vergrendeling die klopt als er tien mensen tegelijk een
droom insturen. Losse JSON-bestanden gaan daar stuk.

Wachtwoorden gaan door `hashlib.scrypt`. Dat is opzettelijk langzaam en
geheugenhongerig, waardoor het raden van een gestolen hash duur wordt. De
parameters staan in de hash zelf, zodat ze later omhoog kunnen zonder dat oude
wachtwoorden ongeldig worden.

Sessies zijn een willekeurig token in een cookie: HttpOnly, zodat JavaScript er
niet bij kan, en SameSite=Lax. Er staat geen gebruikers-id in het token en het is
niet te raden, dus er valt niets uit af te leiden.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DB = DATA / "dreamverse.db"

# scrypt met deze parameters kost ongeveer een tiende seconde per poging. Dat is
# onmerkbaar bij inloggen en pijnlijk bij het doorrekenen van een woordenlijst.
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
# scrypt met deze n en r vraagt 128 * n * r = 32 MB, en dat is precies de
# standaardgrens van OpenSSL. Dus expliciet ruimer, anders weigert hij.
SCRYPT_MAXMEM = 128 * 1024 * 1024

SESSIE_COOKIE = "dv_sessie"
SESSIE_DAGEN = 60

GESLACHTEN = ("man", "vrouw", "beide", "onbekend")
TALEN = ("nl", "en")

# Geen volledige RFC-controle: die bestaat niet in één reguliere expressie, en
# streng zijn kost je echte gebruikers met een geldig adres. Dit vangt de
# tikfouten en laat de rest aan de verificatiemail.
EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")

_lock = threading.Lock()
_lokaal = threading.local()


class AccountError(Exception):
    """Iets mag niet; de melding is bedoeld voor de gebruiker."""


def nu():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def maand():
    return datetime.now(timezone.utc).strftime("%Y-%m")


# --------------------------------------------------------------------------- #
# De database
# --------------------------------------------------------------------------- #

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL COLLATE NOCASE UNIQUE,
    wachtwoord    TEXT NOT NULL,
    naam          TEXT NOT NULL DEFAULT '',
    geboortedatum TEXT NOT NULL DEFAULT '',
    geslacht      TEXT NOT NULL DEFAULT 'onbekend',
    taal          TEXT NOT NULL DEFAULT 'nl',
    voogd_ok      INTEGER NOT NULL DEFAULT 0,
    pakket        TEXT NOT NULL DEFAULT 'gratis',
    tokens        INTEGER NOT NULL DEFAULT 0,
    maand         TEXT NOT NULL DEFAULT '',
    dromen_op     INTEGER NOT NULL DEFAULT 0,
    avatar_sec    INTEGER NOT NULL DEFAULT 0,
    bevestigd     INTEGER NOT NULL DEFAULT 0,
    bevestig_code TEXT NOT NULL DEFAULT '',
    gemaakt       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS betalingen (
    id       TEXT PRIMARY KEY,          -- het gebeurtenis-id van Stripe
    user_id  INTEGER,
    soort    TEXT NOT NULL DEFAULT '',
    bedrag   INTEGER NOT NULL DEFAULT 0,
    munt     TEXT NOT NULL DEFAULT 'eur',
    wanneer  TEXT NOT NULL DEFAULT '',
    ruw      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sessies (
    token   TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gemaakt TEXT NOT NULL DEFAULT '',
    gezien  TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS sessies_user ON sessies(user_id);

CREATE TABLE IF NOT EXISTS dromen (
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    n            INTEGER NOT NULL,
    tekst        TEXT NOT NULL DEFAULT '',
    titel        TEXT NOT NULL DEFAULT '',
    motieven     TEXT NOT NULL DEFAULT '[]',
    wanneer      TEXT NOT NULL DEFAULT '',
    antwoord     TEXT NOT NULL DEFAULT '',
    vooruitblik  TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (user_id, n)
);

CREATE TABLE IF NOT EXISTS verbeeldingen (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    n       INTEGER NOT NULL,
    data    TEXT NOT NULL,
    PRIMARY KEY (user_id, n)
);
"""


def db():
    """Eén verbinding per thread. SQLite-verbindingen zijn niet te delen."""
    verbinding = getattr(_lokaal, "db", None)
    if verbinding is not None:
        return verbinding
    DATA.mkdir(parents=True, exist_ok=True)
    verbinding = sqlite3.connect(str(DB), timeout=20, isolation_level=None)
    verbinding.row_factory = sqlite3.Row
    # WAL: lezers blokkeren de schrijver niet. Met tien mensen die tegelijk een
    # droom insturen is dat het verschil tussen werken en wachten.
    verbinding.execute("PRAGMA journal_mode=WAL")
    verbinding.execute("PRAGMA foreign_keys=ON")
    verbinding.execute("PRAGMA busy_timeout=20000")
    verbinding.executescript(SCHEMA)
    _migreer(verbinding)
    _lokaal.db = verbinding
    return verbinding


# Kolommen die er later bij kwamen. CREATE TABLE IF NOT EXISTS raakt een
# bestaande tabel niet aan, dus die moeten er los bij - anders staat een
# database die al draait ineens een kolom tekort.
LATERE_KOLOMMEN = (
    ("users", "stripe_klant", "TEXT NOT NULL DEFAULT ''"),
    ("users", "stripe_abo", "TEXT NOT NULL DEFAULT ''"),
    ("users", "pakket_tot", "TEXT NOT NULL DEFAULT ''"),
)


def _migreer(verbinding):
    for tabel, kolom, soort in LATERE_KOLOMMEN:
        bestaat = any(r["name"] == kolom for r in
                      verbinding.execute("PRAGMA table_info({})".format(tabel)))
        if not bestaat:
            verbinding.execute("ALTER TABLE {} ADD COLUMN {} {}".format(tabel, kolom, soort))


# --------------------------------------------------------------------------- #
# Wachtwoorden
# --------------------------------------------------------------------------- #

def hash_wachtwoord(wachtwoord):
    zout = secrets.token_bytes(16)
    sleutel = hashlib.scrypt(wachtwoord.encode("utf-8"), salt=zout,
                             n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32,
                             maxmem=SCRYPT_MAXMEM)
    # De parameters staan in de hash, zodat ze later omhoog kunnen zonder dat
    # bestaande wachtwoorden ongeldig worden.
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N, SCRYPT_R, SCRYPT_P, zout.hex(), sleutel.hex())


def klopt_wachtwoord(wachtwoord, opgeslagen):
    try:
        soort, n, r, p, zout, sleutel = opgeslagen.split("$")
        if soort != "scrypt":
            return False
        opnieuw = hashlib.scrypt(wachtwoord.encode("utf-8"), salt=bytes.fromhex(zout),
                                 n=int(n), r=int(r), p=int(p), dklen=len(sleutel) // 2,
                                 maxmem=SCRYPT_MAXMEM)
    except (ValueError, TypeError):
        return False
    # compare_digest en niet ==: een gewone vergelijking stopt bij het eerste
    # verschil en verraadt daarmee hoe ver je goed zat.
    return hmac.compare_digest(opnieuw.hex(), sleutel)


# --------------------------------------------------------------------------- #
# Registreren en inloggen
# --------------------------------------------------------------------------- #

def registreer(email, wachtwoord, naam=""):
    email = (email or "").strip()
    if not EMAIL.match(email) or len(email) > 200:
        raise AccountError("Dat lijkt geen geldig e-mailadres.")
    if len(wachtwoord or "") < 8:
        raise AccountError("Kies een wachtwoord van minstens acht tekens.")
    if len(wachtwoord) > 200:
        raise AccountError("Dat wachtwoord is te lang.")

    code = secrets.token_urlsafe(24)
    with _lock:
        try:
            db().execute(
                "INSERT INTO users (email, wachtwoord, naam, maand, bevestig_code, gemaakt)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (email, hash_wachtwoord(wachtwoord), (naam or "").strip()[:60],
                 maand(), code, nu()))
        except sqlite3.IntegrityError:
            # Niet verklappen dát het adres bestaat: dan is dit eindpunt een
            # manier om uit te zoeken wie er een account heeft.
            raise AccountError("Dat lukte niet. Bestaat er al een account met dit "
                               "adres? Probeer dan in te loggen.")
        rij = db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(rij)


def inloggen(email, wachtwoord):
    email = (email or "").strip()
    rij = db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if rij is None or not klopt_wachtwoord(wachtwoord or "", rij["wachtwoord"]):
        # Eén melding voor beide gevallen: anders is dit een manier om te
        # achterhalen welke adressen bestaan.
        raise AccountError("Dat e-mailadres en wachtwoord horen niet bij elkaar.")
    return nieuwe_sessie(rij["id"])


def nieuwe_sessie(user_id):
    token = secrets.token_urlsafe(32)
    with _lock:
        db().execute("INSERT INTO sessies (token, user_id, gemaakt, gezien)"
                     " VALUES (?, ?, ?, ?)", (token, user_id, nu(), nu()))
    return token


def sessie_weg(token):
    if not token:
        return
    with _lock:
        db().execute("DELETE FROM sessies WHERE token = ?", (token,))


def alle_sessies_weg(user_id):
    """Overal uitloggen. Nodig na een wachtwoordwijziging."""
    with _lock:
        db().execute("DELETE FROM sessies WHERE user_id = ?", (user_id,))


def uit_sessie(token):
    """De gebruiker bij dit sessietoken, of None."""
    if not token:
        return None
    rij = db().execute(
        "SELECT u.* FROM users u JOIN sessies s ON s.user_id = u.id WHERE s.token = ?",
        (token,)).fetchone()
    if rij is None:
        return None
    # Bijhouden wanneer een sessie voor het laatst gebruikt is, zodat oude
    # sessies opgeruimd kunnen worden. Niet bij elk verzoek schrijven: dat is
    # een schrijfactie per plaatje.
    return dict(rij)


def raak_sessie_aan(token):
    with _lock:
        db().execute("UPDATE sessies SET gezien = ? WHERE token = ?", (nu(), token))


# --------------------------------------------------------------------------- #
# Het profiel
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Wie is er nu bezig?
# --------------------------------------------------------------------------- #

# De server draait één thread per verzoek, dus de ingelogde gebruiker kan daar
# gewoon in staan. Dat is veel minder invasief dan een user_id door twintig
# functies heen doorgeven, en het gaat niet mis in achtergrondthreads: die
# krijgen hun bestandsnaam mee en raken de gebruikerslaag niet aan.
def zet_huidige(user):
    _lokaal.huidige = user


def huidige():
    """De ingelogde gebruiker. Gooit als er niemand is - liever hard stuk dan
    stil de gegevens van iemand anders aanraken."""
    u = getattr(_lokaal, "huidige", None)
    if u is None:
        raise AccountError("Niet ingelogd.")
    return u


def huidige_of_none():
    return getattr(_lokaal, "huidige", None)


def gebruiker(user_id):
    rij = db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(rij) if rij else None


def zet_profiel(user_id, velden):
    kolom = {"name": "naam", "birthdate": "geboortedatum", "gender": "geslacht",
             "language": "taal", "guardian_ok": "voogd_ok"}
    zetten = {}
    if "name" in velden:
        zetten["naam"] = (velden.get("name") or "").strip()[:60]
    if "birthdate" in velden:
        zetten["geboortedatum"] = (velden.get("birthdate") or "").strip()[:10]
    if "gender" in velden:
        g = velden.get("gender")
        zetten["geslacht"] = g if g in GESLACHTEN else "onbekend"
    if "language" in velden:
        t = velden.get("language")
        zetten["taal"] = t if t in TALEN else "nl"
    if "guardian_ok" in velden:
        zetten["voogd_ok"] = 1 if velden.get("guardian_ok") else 0
    if not zetten:
        return gebruiker(user_id)
    stukken = ", ".join("{} = ?".format(k) for k in zetten)
    with _lock:
        db().execute("UPDATE users SET {} WHERE id = ?".format(stukken),
                     list(zetten.values()) + [user_id])
    return gebruiker(user_id)


def zet_wachtwoord(user_id, oud, nieuw):
    rij = db().execute("SELECT wachtwoord FROM users WHERE id = ?", (user_id,)).fetchone()
    if rij is None or not klopt_wachtwoord(oud or "", rij["wachtwoord"]):
        raise AccountError("Je huidige wachtwoord klopt niet.")
    if len(nieuw or "") < 8:
        raise AccountError("Kies een wachtwoord van minstens acht tekens.")
    with _lock:
        db().execute("UPDATE users SET wachtwoord = ? WHERE id = ?",
                     (hash_wachtwoord(nieuw), user_id))
    # Overal uitloggen: wie je wachtwoord wijzigt, doet dat meestal omdat hij
    # denkt dat iemand anders erbij kan.
    alle_sessies_weg(user_id)
    return nieuwe_sessie(user_id)


def bevestig(code):
    rij = db().execute("SELECT id FROM users WHERE bevestig_code = ? AND bevestig_code != ''",
                       (code,)).fetchone()
    if rij is None:
        raise AccountError("Die bevestigingslink is niet geldig of al gebruikt.")
    with _lock:
        db().execute("UPDATE users SET bevestigd = 1, bevestig_code = '' WHERE id = ?",
                     (rij["id"],))
    return rij["id"]


# --------------------------------------------------------------------------- #
# Pakket, saldo en verbruik — per gebruiker
# --------------------------------------------------------------------------- #

def rol_maand_om(user_id):
    """Aan het begin van een nieuwe maand staan de tellers weer op nul."""
    rij = db().execute("SELECT maand FROM users WHERE id = ?", (user_id,)).fetchone()
    if rij is None or rij["maand"] == maand():
        return
    with _lock:
        db().execute("UPDATE users SET maand = ?, dromen_op = 0, avatar_sec = 0"
                     " WHERE id = ?", (maand(), user_id))


def tel_op(user_id, dromen=0, avatar_sec=0, tokens=0):
    with _lock:
        db().execute(
            "UPDATE users SET dromen_op = dromen_op + ?, avatar_sec = avatar_sec + ?,"
            " tokens = MAX(0, tokens + ?) WHERE id = ?",
            (dromen, avatar_sec, tokens, user_id))


def zet_pakket(user_id, pakket, tot="", abo=None):
    """Het pakket zetten, en waar het vandaan komt.

    `tot` is de datum waarop het afloopt als er niet opnieuw betaald wordt. Leeg
    betekent: gezet met de hand, loopt niet af.
    """
    with _lock:
        if abo is None:
            db().execute("UPDATE users SET pakket = ?, pakket_tot = ? WHERE id = ?",
                         (pakket, tot, user_id))
        else:
            db().execute("UPDATE users SET pakket = ?, pakket_tot = ?, stripe_abo = ?"
                         " WHERE id = ?", (pakket, tot, abo, user_id))


def zet_stripe_klant(user_id, klant_id):
    with _lock:
        db().execute("UPDATE users SET stripe_klant = ? WHERE id = ?", (klant_id, user_id))


def bij_stripe_klant(klant_id):
    rij = db().execute("SELECT * FROM users WHERE stripe_klant = ?", (klant_id,)).fetchone()
    return dict(rij) if rij else None


def bij_stripe_abo(abo_id):
    rij = db().execute("SELECT * FROM users WHERE stripe_abo = ?", (abo_id,)).fetchone()
    return dict(rij) if rij else None


def al_verwerkt(gebeurtenis_id):
    """Is deze gebeurtenis van Stripe al eens langsgekomen?

    Stripe stuurt een webhook opnieuw als hij geen 200 terugkrijgt, en soms
    twee keer zonder aanleiding. Zonder deze controle krijgt iemand zijn tokens
    dubbel - of, erger, een terugboeking wordt twee keer verwerkt.
    """
    return db().execute("SELECT 1 FROM betalingen WHERE id = ?",
                        (gebeurtenis_id,)).fetchone() is not None


def boek_betaling(gebeurtenis_id, user_id, soort, bedrag, munt, ruw=""):
    with _lock:
        db().execute("INSERT OR IGNORE INTO betalingen (id, user_id, soort, bedrag,"
                     " munt, wanneer, ruw) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (gebeurtenis_id, user_id, soort, bedrag, munt, nu(), ruw[:2000]))


def aantal_gebruikers():
    return db().execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]


# --------------------------------------------------------------------------- #
# Dromen en verbeeldingen — per gebruiker
# --------------------------------------------------------------------------- #

def dromen(user_id):
    rijen = db().execute(
        "SELECT n, tekst, titel, motieven, wanneer, antwoord, vooruitblik"
        " FROM dromen WHERE user_id = ? ORDER BY n", (user_id,)).fetchall()
    uit = []
    for r in rijen:
        d = {"n": r["n"], "text": r["tekst"], "title": r["titel"],
             "when": r["wanneer"]}
        try:
            d["motifs"] = json.loads(r["motieven"])
        except (ValueError, TypeError):
            d["motifs"] = []
        if r["antwoord"]:
            d["answer"] = r["antwoord"]
        if r["vooruitblik"]:
            d["future_check"] = r["vooruitblik"]
        uit.append(d)
    return uit


def volgend_nummer(user_id):
    rij = db().execute("SELECT MAX(n) AS hoogste FROM dromen WHERE user_id = ?",
                       (user_id,)).fetchone()
    return (rij["hoogste"] or 0) + 1


def zet_droom(user_id, n, tekst, titel, motieven, wanneer):
    with _lock:
        db().execute(
            "INSERT OR REPLACE INTO dromen (user_id, n, tekst, titel, motieven, wanneer,"
            " antwoord, vooruitblik) VALUES (?, ?, ?, ?, ?, ?,"
            " COALESCE((SELECT antwoord FROM dromen WHERE user_id = ? AND n = ?), ''),"
            " COALESCE((SELECT vooruitblik FROM dromen WHERE user_id = ? AND n = ?), ''))",
            (user_id, n, tekst, titel, json.dumps(motieven, ensure_ascii=False),
             wanneer, user_id, n, user_id, n))


def zet_veld(user_id, n, veld, waarde):
    if veld not in ("antwoord", "vooruitblik", "titel"):
        raise AccountError("Onbekend veld.")
    with _lock:
        raakte = db().execute(
            "UPDATE dromen SET {} = ? WHERE user_id = ? AND n = ?".format(veld),
            (waarde, user_id, n))
    if raakte.rowcount == 0:
        raise AccountError("Die droom staat niet in je archief.")


def weg_droom(user_id, n):
    with _lock:
        raakte = db().execute("DELETE FROM dromen WHERE user_id = ? AND n = ?",
                              (user_id, n))
        db().execute("DELETE FROM verbeeldingen WHERE user_id = ? AND n = ?", (user_id, n))
    return raakte.rowcount > 0


def weg_alles(user_id):
    """Alle nummers teruggeven, zodat de bestanden erbij opgeruimd kunnen worden."""
    nummers = [r["n"] for r in db().execute(
        "SELECT n FROM dromen WHERE user_id = ?", (user_id,)).fetchall()]
    with _lock:
        db().execute("DELETE FROM dromen WHERE user_id = ?", (user_id,))
        db().execute("DELETE FROM verbeeldingen WHERE user_id = ?", (user_id,))
    return nummers


def zet_verbeelding(user_id, n, episode):
    with _lock:
        db().execute("INSERT OR REPLACE INTO verbeeldingen (user_id, n, data)"
                     " VALUES (?, ?, ?)",
                     (user_id, n, json.dumps(episode, ensure_ascii=False)))


def verbeelding(user_id, n):
    rij = db().execute("SELECT data FROM verbeeldingen WHERE user_id = ? AND n = ?",
                       (user_id, n)).fetchone()
    if rij is None:
        return None
    try:
        return json.loads(rij["data"])
    except (ValueError, TypeError):
        return None


def alle_verbeeldingen(user_id):
    """Van nieuw naar oud, voor wie de laatste analyse zoekt."""
    rijen = db().execute(
        "SELECT n, data FROM verbeeldingen WHERE user_id = ? ORDER BY n DESC",
        (user_id,)).fetchall()
    for r in rijen:
        try:
            yield r["n"], json.loads(r["data"])
        except (ValueError, TypeError):
            continue
