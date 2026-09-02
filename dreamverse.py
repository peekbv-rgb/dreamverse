"""Dreamverse — een droom erin, een verbeelding eruit.

Eén droom wordt een verbeelding in vijf panelen met een duiding in drie delen:
waarom je dit droomde, wat het zegt, en wat eraan zit te komen. Elke eerdere
droom telt mee, want daar zit het hele idee in: terugkerende plaatsen, personen
en dieren maken er na een paar maanden één wereld van.

Zonder ANTHROPIC_API_KEY draait alles behalve het schrijven: dan komt er een
vast voorbeeld terug met demo=True. Zo is de app te starten en te
demonstreren voordat er een cent aan tokens is uitgegeven.
"""

import json
import os
import re
import threading
from datetime import date
from pathlib import Path

import accounts
import kling
import plans
import stem
import usage

ROOT = Path(__file__).parent
DATA = ROOT / "data"

MODEL = "claude-opus-5"
MAX_ARCHIVE_IN_PROMPT = 15  # meer geschiedenis maakt de duiding niet beter, wel duurder
# De kleurvelden zijn de chakra's. Dat is niet alleen sfeer: het dwingt het model
# om per paneel te kiezen welk gevoel er speelt, en de kijker ziet die keuze terug.
PALETTES = ("root", "sacral", "solar", "heart", "throat", "third_eye", "crown")
MOTIFS = ("flight", "water", "figure", "structure", "expanse", "close")

CHAKRA_HINT = (
    "root = overleven, angst, aarde (rood) · sacral = verlangen, water, schepping (oranje) · "
    "solar = wil, kracht, spanning (geel) · heart = liefde, verlies, verbinding (groen) · "
    "throat = spreken, gehoord worden, zwijgen (blauw) · third_eye = zien, weten, inzicht (indigo) · "
    "crown = overgave, licht, het grotere geheel (violet)"
)

_lock = threading.Lock()


def credentials_available():
    """Kunnen we bij de API, hoe dan ook?

    Twee routes: een sleutel in de omgeving, of een profiel van `ant auth login`
    dat de SDK zelf oppikt. Alleen op de sleutel controleren zou de app in
    voorbeeldmodus houden terwijl hij prima kan schrijven.
    """
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    for basis in (os.environ.get("ANTHROPIC_CONFIG_DIR"),
                  os.path.join(os.environ.get("APPDATA", ""), "Anthropic"),
                  os.path.expanduser("~/.config/anthropic")):
        if not basis:
            continue
        map_ = Path(basis) / "credentials"
        if map_.is_dir() and any(map_.glob("*.json")):
            return True
    return False


class DreamverseError(Exception):
    """Iets ging mis bij het schrijven; de melding is bedoeld voor de gebruiker."""


# --------------------------------------------------------------------------- #
# Archief
# --------------------------------------------------------------------------- #

def uid():
    """Het nummer van de ingelogde gebruiker."""
    return accounts.huidige()["id"]


def sleutel(number):
    """De bestandsnaam-sleutel van een droom: "3_12" voor droom 12 van gebruiker 3.

    De panelen liggen in één map, maar droom 12 van de een is niet droom 12 van
    de ander. Door het gebruikersnummer in de naam te zetten blijven alle
    bestaande patronen werken - kling.py, stem.py en video.py krijgen deze
    sleutel waar ze eerst een nummer kregen, en zoeken nog steeds op
    "<sleutel>-*". Zo hoefde er in die drie modules niets te veranderen.
    """
    return "{}_{}".format(uid(), number)


def load_archive():
    """De dromen van de ingelogde gebruiker, oud naar nieuw."""
    return accounts.dromen(uid())


def next_number(archive=None):
    return accounts.volgend_nummer(uid())


def load_profile():
    """Voor de code die nog een profiel-woordenboek verwacht."""
    u = accounts.huidige()
    return {"name": u["naam"], "birthdate": u["geboortedatum"],
            "gender": u["geslacht"], "language": u["taal"],
            "guardian_ok": bool(u["voogd_ok"]),
            "plan": u["pakket"], "tokens": u["tokens"]}


GESLACHTEN = ("man", "vrouw", "beide", "onbekend")
TALEN = ("nl", "en")


def leeftijd_uit(geboortedatum):
    """Leeftijd in hele jaren, of None als de datum niet klopt."""
    try:
        jaar, maand, dag = (int(x) for x in str(geboortedatum).split("-"))
        vandaag = date.today()
        jaren = vandaag.year - jaar - ((vandaag.month, vandaag.day) < (maand, dag))
        return jaren if 0 <= jaren <= 120 else None
    except (ValueError, AttributeError, TypeError):
        return None


def set_profile(velden):
    """Naam, geboortedatum, geslacht en taal bewaren.

    De leeftijd wordt afgeleid uit de geboortedatum en niet los opgeslagen: dan
    klopt hij volgend jaar nog. Onder de achttien mag er niets gekocht worden
    zonder dat een ouder of voogd het heeft bevestigd.
    """
    u = accounts.zet_profiel(uid(), velden)
    accounts.zet_huidige(u)
    return public_profile()


def public_profile():
    """Het profiel zoals de app het mag zien, met de leeftijd erbij gerekend."""
    u = accounts.huidige()
    leeftijd = leeftijd_uit(u["geboortedatum"])
    return {
        "email": u["email"],
        "name": u["naam"],
        "birthdate": u["geboortedatum"],
        "age": leeftijd,
        "minor": leeftijd is not None and leeftijd < 18,
        "guardian_ok": bool(u["voogd_ok"]),
        "gender": u["geslacht"],
        "language": u["taal"],
        "verified": bool(u["bevestigd"]),
    }


def set_name(name):
    return set_profile({"name": name})


def save_episode(number, episode):
    """Bewaar de hele verbeelding, zodat hij terug te kijken is.

    Zonder dit is een verbeelding weg zodra je de pagina ververst, en zou iemand
    opnieuw moeten betalen voor beelden die al gemaakt zijn. De panelen en de
    video staan als bestand in data/panels; hier komt de tekst bij die erbij
    hoort.
    """
    accounts.zet_verbeelding(uid(), number, episode)


def load_episode(number):
    """Een eerder gemaakte verbeelding terughalen. None als hij er niet is."""
    episode = accounts.verbeelding(uid(), number)
    if episode is None:
        # Dromen van voor het bewaren bestaan alleen nog als panelen op schijf.
        # Daar valt genoeg uit af te leiden om er beeld bij te kunnen kopen.
        panelen = sorted(kling.PANELS.glob("{}-[0-9].*".format(sleutel(number))))
        beelden = [p for p in panelen if p.suffix.lower() in (".png", ".jpg", ".webp")]
        if not beelden:
            return None
        titel = next((x.get("title") for x in load_archive() if x.get("n") == number), None)
        episode = {
            "number": number,
            "title": titel or "Droom {}".format(number),
            "panels": [{"narration": "", "image": "", "palette": "crown", "motif": "expanse"}
                       for _ in beelden],
            "key_panel": min(2, len(beelden) - 1),
            "threads": [], "why": "", "meaning": "", "future": "", "question": "",
            "together": "", "night": "", "task": "", "people": [], "symbols": [],
            "onvolledig": True,
        }
    for d in load_archive():
        if d.get("n") == number:
            if d.get("answer"):
                episode["answer"] = d["answer"]
            if not episode.get("dream"):
                episode["dream"] = d.get("text", "")
            episode["when"] = d.get("when", "")
            episode["future_check"] = d.get("future_check", "")
    return episode


def latest_together():
    """De nieuwste lijn door alle dromen heen, plus de draden erbij.

    Dit blok staat altijd op de pagina, ook als er geen verbeelding open is: het
    is de reden dat iemand een tweede en een tiende keer terugkomt. Bij elke
    nieuwe droom wordt hij herschreven, dus de nieuwste is de geldige.
    """
    for n, episode in accounts.alle_verbeeldingen(uid()):
        if (episode.get("together") or "").strip():
            return {"number": n,
                    "together": episode["together"],
                    "threads": episode.get("threads") or []}
    return {"number": None, "together": "", "threads": []}


def spectrum():
    """Welk kleurveld elke droom koos, op volgorde van de tijd.

    Het model kiest per paneel het chakra dat bij het gevoel past. Over tientallen
    dromen wordt dat een grafiek van waar iemands nachten zich ophouden - en dat
    is iets wat je nergens anders over jezelf te zien krijgt. De gegevens lagen er
    al; er hoefde alleen naar gekeken te worden.
    """
    rijen = []
    titels = {d.get("n"): d for d in load_archive()}
    for n, episode in sorted(accounts.alle_verbeeldingen(uid())):
        d = titels.get(n, {"n": n})
        velden = [p.get("palette") for p in (episode.get("panels") or [])
                  if p.get("palette") in PALETTES]
        if not velden:
            continue
        telling = {veld: velden.count(veld) for veld in PALETTES if veld in velden}
        # Het overheersende veld: dat bepaalt de kleur van de droom als geheel.
        hoofd = max(telling, key=lambda k: (telling[k], PALETTES.index(k)))
        rijen.append({
            "n": d.get("n"),
            "title": d.get("title") or "",
            "when": d.get("when") or "",
            "counts": telling,
            "main": hoofd,
        })

    # En het totaal, zodat je in één blik ziet waar je jaar zich ophield.
    totaal = {veld: 0 for veld in PALETTES}
    for r in rijen:
        for veld, n in r["counts"].items():
            totaal[veld] += n
    return {"dreams": rijen, "total": totaal, "palettes": list(PALETTES)}


def archive_with_media():
    """Het archief met bij elke droom het kernmoment erbij.

    Een lijst titels zegt weinig; het beeld van het kernmoment zegt meteen welke
    nacht dit was. Bewoog dat moment, dan is er een video en die wint -- dat is
    het duurste en het mooiste wat er van die droom bestaat.
    """
    uit = []
    for d in sorted(load_archive(), key=lambda x: x.get("n", 0), reverse=True):
        n = d.get("n")
        k = sleutel(n)
        rij = dict(d)
        clip = kling.PANELS / "{}-hero.mp4".format(k)
        rij["clip"] = "/panels/{}-hero.mp4".format(k) if clip.is_file() else None

        # Welk paneel het kernmoment was staat in de bewaarde verbeelding; is die
        # er niet, dan is het middelste beeld de beste gok.
        bewaard = accounts.verbeelding(uid(), n) or {}
        kern = bewaard.get("key_panel")
        beelden = sorted(p for p in kling.PANELS.glob("{}-[0-9].*".format(k))
                         if p.suffix.lower() in (".png", ".jpg", ".webp"))
        if beelden:
            i = kern if isinstance(kern, int) and 0 <= kern < len(beelden) else len(beelden) // 2
            rij["thumb"] = "/panels/" + beelden[i].name
        else:
            rij["thumb"] = None
        uit.append(rij)
    return uit


def repair_episode(number):
    """Schrijf de duiding opnieuw bij panelen die er al liggen.

    Dromen van voor het bewaren bestaan alleen nog als beeld op schijf: de
    verteltekst en de duiding zijn nooit weggeschreven. De oorspronkelijke
    droomtekst staat wel in het archief, dus de verbeelding is terug te schrijven.
    Dit kost geen beeld en geen tokens -- daar is al voor betaald.
    """
    archive = load_archive()
    bron = next((d for d in archive if d.get("n") == number), None)
    if not bron or not (bron.get("text") or "").strip():
        raise DreamverseError("De oorspronkelijke droomtekst is niet meer te vinden.")

    eerder = [d for d in archive if d.get("n", 0) < number]
    profiel = load_profile()
    episode = write_episode(bron["text"], eerder, number, profiel.get("name"),
                            profiel.get("language", "nl"))
    episode["number"] = number
    episode["hersteld"] = True
    episode["dream"] = bron["text"]

    # De panelen die er liggen zijn leidend: de nieuwe verteltekst wordt eroverheen
    # gelegd, zodat tekst en beeld even lang zijn en niets uit de pas loopt.
    beelden = sorted(p for p in kling.PANELS.glob("{}-[0-9].*".format(sleutel(number)))
                     if p.suffix.lower() in (".png", ".jpg", ".webp"))
    if beelden:
        panels = episode.get("panels") or []
        while len(panels) < len(beelden):
            panels.append({"narration": "", "image": "", "palette": "crown", "motif": "expanse"})
        episode["panels"] = panels[:len(beelden)]
        episode["key_panel"] = min(episode.get("key_panel", 2), len(beelden) - 1)

    # De titel uit het archief blijft staan: daaronder kent de dromer hem al.
    if bron.get("title"):
        episode["title"] = bron["title"]
    if bron.get("answer"):
        episode["answer"] = bron["answer"]

    u = episode.get("usage") or {}
    usage.episode(number, u.get("input_tokens", 0), u.get("output_tokens", 0),
                  demo=episode.get("demo"))
    save_episode(number, episode)
    return episode


OORDELEN = ("raak", "deels", "mis")


def judge_future(number, verdict):
    """De dromer zegt zelf of de vooruitblik uitkwam.

    Bewust alleen de dromer: zodra wij zouden scoren, wordt de vooruitblik een
    claim, en dan houdt "vermaak, geen voorspelling" geen stand. Het oordeel gaat
    ook niet mee in de prompt - een model dat weet dat het op raak gescoord wordt,
    gaat voorzichtiger en vager schrijven, of juist gokken.
    """
    if verdict not in OORDELEN:
        raise DreamverseError("Dat oordeel bestaat niet.")
    try:
        accounts.zet_veld(uid(), number, "vooruitblik", verdict)
    except accounts.AccountError as e:
        raise DreamverseError(str(e))
    return next(d for d in load_archive() if d.get("n") == number)


def answer_question(number, answer):
    """Bewaar wat de dromer op de slotvraag antwoordde.

    Dat antwoord is het waardevolste wat er is: het is het enige stuk tekst dat
    de dromer schrijft nadat hij zijn droom heeft teruggezien. Het gaat mee in
    het geheugen en dus in de volgende duiding.
    """
    answer = (answer or "").strip()[:1000]
    if not answer:
        raise DreamverseError("Er stond niets in je antwoord.")
    try:
        accounts.zet_veld(uid(), number, "antwoord", answer)
    except accounts.AccountError as e:
        raise DreamverseError(str(e))
    return next(d for d in load_archive() if d.get("n") == number)


def delete_dream(number):
    """Een droom weghalen: uit het archief, de bewaarde verbeelding en de beelden.

    Alles weg betekent hier ook echt alles. Iemand die zijn droom wist verwacht
    niet dat de panelen ervan nog op de schijf staan.
    """
    _ruim_nummer_op(number)          # eerst de bestanden, dan pas de rij weghalen
    if not accounts.weg_droom(uid(), number):
        raise DreamverseError("Die droom staat niet in je archief.")
    return {"deleted": number, "over": len(load_archive())}


def _bestanden_van(number):
    """Alles wat bij één droom van deze gebruiker hoort."""
    k = sleutel(number)
    uit = [kling.PANELS / "{}.json".format(k)]
    uit.extend(kling.PANELS.glob("{}-*".format(k)))
    return uit


def _ruim_nummer_op(number):
    for pad in _bestanden_van(number):
        try:
            pad.unlink(missing_ok=True)
        except OSError:
            pass


def clear_archive():
    """Het archief wissen: ook de beelden, de video, de stem en de duiding.

    Alleen archive.json legen was fout en op een nare manier: de nummering begint
    daarna weer bij 1, en de nieuwe Droom 1 vond de panelen van de oude Droom 1
    nog op schijf. Dan zie je in je archief een droom met het beeld van een droom
    die je jaren eerder had.
    """
    nummers = accounts.weg_alles(uid())
    for n in nummers:
        _ruim_nummer_op(n)

    # En alles wat er verder nog van deze gebruiker ligt, ook van dromen die al
    # eens los gewist zijn terwijl de verteller nog schreef. Bestanden van andere
    # gebruikers beginnen met een ander nummer en blijven staan; check.png en
    # ander niet-genummerd materiaal ook.
    mijn = "{}_".format(uid())
    if kling.PANELS.is_dir():
        for pad in kling.PANELS.iterdir():
            if pad.name.startswith(mijn):
                try:
                    pad.unlink(missing_ok=True)
                except OSError:
                    pass


# --------------------------------------------------------------------------- #
# De prompt
# --------------------------------------------------------------------------- #

RULES = f"""Je schrijft een verbeelding voor Dreamverse: de droom van de gebruiker als korte,
literaire film in vijf panelen.

Toon en taal:
- Alles in {{TAAL}}, in de je-vorm (in het Engels: "you"), tegenwoordige tijd. Beeldend,
  maar zonder bloemrijke overdaad. Kort is beter dan mooi. Het veld "image" blijft
  altijd Engels, want dat gaat naar een beeldmodel.
- Altijd hoopvol en welwillend. Ook een akelige droom krijgt een duiding die de
  dromer iets geeft.
- Bij geweld, verlies, ziekte of een overledene: erken het eerst eerlijk en buig het
  niet weg. Zoek daarna pas het licht. Opgewekt wegwuiven is erger dan niets zeggen.

De vooruitblik ("future") en de liefdesparagraaf ("love") zijn vermaak, geen voorspelling. Schrijf hem concreet en
uitnodigend over de komende weken. Nooit over gezondheid, ziekte, geld, zwangerschap
of iemands dood — ook niet als de droom daarover ging.

Gebruik de eerdere dromen: benoem terugkerende plaatsen, personen, dieren of gevoelens
en wat er sindsdien veranderd is. Verzin nooit een eerdere droom die niet in de lijst
staat. Staat er niets bruikbaars in, laat "threads" dan leeg.

"together" is iets anders dan "threads". Draden zijn losse echo's; "together" is de
lijn door alles heen: wat al deze dromen bij elkaar over de dromer zeggen, welke
richting erin zit en wat er sinds de eerste droom veranderd is. Twee tot vier zinnen,
en spreek de dromer aan. Dit is de reden dat iemand blijft dromen bij ons: één droom
is een anekdote, tien dromen zijn een portret. Is dit de eerste of tweede droom, laat
"together" dan leeg -- doen alsof er al een patroon is, is niet eerlijk.

Antwoord met uitsluitend geldige JSON, zonder tekst eromheen, in deze vorm:

{{"title": string,
 "panels": [{{"narration": string, "image": string, "palette": string, "motif": string}}],
 "threads": [{{"ref": string, "was": string, "now": string}}],
 "why": string, "meaning": string, "future": string, "love": string,
 "people": [{{"who": string, "role": string}}],
 "symbols": [{{"sign": string, "meaning": string}}],
 "night": string, "task": string,
 "today": string, "season": string, "together": string,
 "question": string, "motifs": [string], "key_panel": number}}

Regels voor de velden:
- Precies 5 panelen. "narration" is 1 tot 2 zinnen Nederlands.
- "image" is een korte Engelse beschrijving van wat er te zien is, voor een
  illustratiemodel: alleen het beeld, geen namen, geen tekst in beeld, geen
  emoties benoemen. Bijvoorbeeld: "a figure gliding high above dark mountain
  ridges, a lit rectangular pool far below in the valley".
- palette is het kleurveld dat bij het gevoel van dat paneel past, een van:
  {", ".join(PALETTES)}. Betekenis: {CHAKRA_HINT}.
  Laat het door de verbeelding heen verschuiven; vijf keer hetzelfde veld is bijna nooit waar.
- motif is een van: {", ".join(MOTIFS)}.
- 0 tot 3 threads. "ref" is bijvoorbeeld "Droom 12". "was" is hoe het toen was,
  "now" is wat er nu anders aan is.
- why, meaning en future elk 2 tot 4 zinnen.
- love gaat over verbinding: wie de dromer opzoekt, wie hem opzoekt, waar warmte
  zit of juist afstand. Twee tot drie zinnen, uitnodigend en concreet over de
  komende weken. HARDE GRENZEN: nooit beweren dat iemand vreemdgaat, weggaat of
  dat een relatie eindigt; nooit iets beweren over een specifieke derde persoon;
  nooit over zwangerschap. Gaat de droom nergens over mensen, schrijf dan iets
  over hoe hij zich tot anderen verhoudt in plaats van een liefdesvoorspelling
  te verzinnen.
- people is wie er in de droom voorkwam en wat die van de dromer leek te willen.
  "who" is hoe de dromer die persoon zelf zou noemen ("een vriendin", "mijn broer",
  "een onbekende man"); "role" is in een of twee zinnen wat die daar deed en wat
  het bij de dromer losmaakte. Nul tot vier personen; verzin er nooit een bij.
  Dieren mogen erbij als ze zich als personage gedroegen. Nooit beweren wat een
  echt bestaand mens denkt of voelt - schrijf over hoe die in de droom verscheen.
- symbols zijn de terugkerende tekens in DEZE dromer zijn dromen, niet uit een
  droomwoordenboek. "sign" is het teken ("water", "vliegen"); "meaning" is wat
  het bij hem betekent, afgeleid uit de eerdere dromen in de lijst hierboven.
  Kwam een teken maar een keer voor, laat het dan weg. Nul tot drie.
  Schrijf nooit "water staat voor emotie" - dat kan iedereen opzoeken en het is
  bij deze dromer misschien niet eens waar.
- night is een nuchtere observatie over wat voor soort droom dit was en waar in
  de nacht hij waarschijnlijk viel: een droom met een doorlopend verhaal en
  wisselende scenes hoort bij de late REM-slaap vlak voor het wakker worden, een
  kort en statisch beeld eerder in de nacht, en een droom waarin de dromer merkt
  dat hij droomt zit op de grens. Een tot twee zinnen, feitelijk van toon. Geen
  duiding, geen advies, en nooit iets over gezondheid of slaapkwaliteit.
- task is de opdracht die in de droom zit als je hem als opdracht leest. Precies
  een, gebiedende wijs, concreet, uitvoerbaar deze week. Iets anders dan "today":
  today is klein en van vandaag, task mag groter zijn en over de week gaan.
  Nooit iets dat geld kost, gezondheid raakt of een ander mens onder druk zet.
- today is een enkel klein voorstel voor vandaag dat uit de droom volgt. Iets dat
  binnen tien minuten kan en niets kost: iemand appen, een raam openzetten, een
  blokje om voor de koffie. Eén zin, geen lijstje, geen levensles.
- season is de naam van het hoofdstuk waar de dromer nu in zit, gezien over al
  zijn dromen samen. Drie tot zes woorden, als de titel van een seizoen van een
  serie. Verandert alleen als het patroon echt verschuift; anders houd je
  dezelfde naam aan als de vorige keer.
- question is een enkele open vraag aan de dromer.
- motifs is een korte lijst kernwoorden uit deze droom voor het geheugen,
  bijvoorbeeld ["zwembad", "vliegen", "een huilende vriendin"].
- key_panel is het nummer van het paneel dat het draaipunt van de droom is,
  geteld vanaf 0. Dat ene paneel wordt echte video, de andere blijven stil.
  Kies het moment waar de droom kantelt of waar het beeld het sterkst is -
  niet het openingsbeeld en meestal niet het slot.
"""


def _history(archive):
    if not archive:
        return "Er zijn nog geen eerdere dromen."
    recent = sorted(archive, key=lambda d: d.get("n", 0))[-MAX_ARCHIVE_IN_PROMPT:]
    regels = []
    for d in recent:
        regel = "Droom {}{}: {}".format(
            d.get("n"),
            " (" + d["when"] + ")" if d.get("when") else "",
            d.get("text", ""),
        )
        if d.get("answer"):
            # Wat de dromer zelf antwoordde weegt zwaarder dan de droom: dat is
            # het enige dat hij wakend heeft opgeschreven, nadat hij het terugzag.
            regel += "\n  Daarop antwoordde hij: " + d["answer"]
        regels.append(regel)
    return "\n".join(regels)


TALEN = {"nl": "het Nederlands", "en": "American English"}


def build_prompt(dream, archive, number, name=None, language="nl"):
    wie = ""
    if name:
        # Spaarzaam gebruiken: een duiding die elke zin je naam noemt klinkt als
        # een verkooptelefoontje, niet als iemand die naar je luistert.
        wie = ("\n\nDe dromer heet {}. Gebruik die naam hooguit een of twee keer "
               "in de hele verbeelding, op een moment dat het iets doet.").format(name)
    return (
        RULES.replace("{TAAL}", TALEN.get(language, TALEN["nl"]))
        + wie
        + "\n\n--- eerdere dromen ---\n"
        + _history(archive)
        + "\n\n--- de droom van vannacht (dit wordt Droom {}) ---\n".format(number)
        + dream
        # De hele prompt staat in het Nederlands; één regel over de taal verdrinkt
        # daarin. Daarom staat de opdracht hier onderaan nog een keer.
        + "\n\n--- taal ---\n"
        + ('Schrijf elk tekstveld in {}. Dat geldt voor "title", "narration", '
           '"threads", "why", "meaning", "future", "love", "people", "symbols", '
           '"night", "task", "today", "season", "together" en "question". Alleen '
           '"image" blijft Engels, want dat gaat naar een beeldmodel.'
           ).format(TALEN.get(language, TALEN["nl"]))
    )


# --------------------------------------------------------------------------- #
# Antwoord opschonen
# --------------------------------------------------------------------------- #

def parse_episode(raw):
    """Haal het JSON-object uit het antwoord en maak het veilig om te tonen."""
    text = raw.strip()
    if text.startswith("```"):
        # Soms komt het in een codeblok terug, ondanks de instructie.
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise DreamverseError("Het antwoord kwam verminkt terug. Probeer het nog een keer.")
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            raise DreamverseError("Het antwoord kwam verminkt terug. Probeer het nog een keer.")

    panels = []
    for p in (data.get("panels") or [])[:5]:
        if not isinstance(p, dict) or not p.get("narration"):
            continue
        panels.append({
            "narration": str(p["narration"]),
            "image": str(p.get("image") or ""),
            # Een onbekende kleur of motief mag de speler niet laten struikelen.
            "palette": p.get("palette") if p.get("palette") in PALETTES else "crown",
            "motif": p.get("motif") if p.get("motif") in MOTIFS else "expanse",
        })
    if not panels:
        raise DreamverseError("Er kwamen geen panelen terug. Probeer het nog een keer.")

    threads = []
    for t in (data.get("threads") or [])[:3]:
        if isinstance(t, dict) and t.get("ref"):
            threads.append({
                "ref": str(t.get("ref", "")),
                "was": str(t.get("was", "")),
                "now": str(t.get("now", "")),
            })

    sleutel = data.get("key_panel")
    try:
        sleutel = int(sleutel)
    except (TypeError, ValueError):
        sleutel = None
    if sleutel is None or not (0 <= sleutel < len(panels)):
        sleutel = min(2, len(panels) - 1)   # bij twijfel het midden

    # Personen en tekens: kort houden en alleen wat volledig is ingevuld.
    mensen = []
    for m in (data.get("people") or [])[:4]:
        if isinstance(m, dict) and str(m.get("who") or "").strip():
            mensen.append({"who": str(m.get("who"))[:60], "role": str(m.get("role") or "")[:400]})
    tekens = []
    for k in (data.get("symbols") or [])[:3]:
        if isinstance(k, dict) and str(k.get("sign") or "").strip():
            tekens.append({"sign": str(k.get("sign"))[:40],
                           "meaning": str(k.get("meaning") or "")[:400]})

    return {
        "key_panel": sleutel,
        "title": str(data.get("title") or "Naamloze droom"),
        "panels": panels,
        "threads": threads,
        "why": str(data.get("why") or ""),
        "love": str(data.get("love") or ""),
        "today": str(data.get("today") or ""),
        "season": str(data.get("season") or ""),
        "together": str(data.get("together") or ""),
        "night": str(data.get("night") or ""),
        "task": str(data.get("task") or ""),
        "people": mensen,
        "symbols": tekens,
        "meaning": str(data.get("meaning") or ""),
        "future": str(data.get("future") or ""),
        "question": str(data.get("question") or ""),
        "motifs": [str(m) for m in (data.get("motifs") or [])][:8],
    }


# --------------------------------------------------------------------------- #
# Schrijven
# --------------------------------------------------------------------------- #

def voorbeeld(reden):
    """Wat we tonen als er niet geschreven kan worden.

    Ligt er een met de hand geschreven exemplaar in data/handmade.json, dan die —
    veel overtuigender om te laten zien dan de ingebouwde tekst. Altijd gemarkeerd
    als demo, met de reden erbij, zodat niemand denkt dat dit zijn eigen droom is.
    """
    try:
        with (DATA / "handmade.json").open(encoding="utf-8") as f:
            episode = parse_episode(f.read())
    except (FileNotFoundError, OSError, DreamverseError, json.JSONDecodeError):
        episode = dict(DEMO_EPISODE)
    episode["demo"] = True
    episode["demo_reason"] = reden
    return episode


def write_episode(dream, archive, number, name=None, language="nl"):
    """Vraag Claude om de verbeelding. Zonder sleutel: het voorbeeld."""
    if not credentials_available():
        return voorbeeld("Er zijn geen inloggegevens; dit is een voorbeeld.")

    try:
        import anthropic
    except ImportError:
        raise DreamverseError("De anthropic-bibliotheek ontbreekt. Draai: pip install -r requirements.txt")

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            # Middelhoge effort: dit is schrijfwerk, geen redeneerpuzzel, en het
            # scheelt direct in de kostprijs per verbeelding.
            output_config={"effort": "medium"},
            messages=[{"role": "user",
                       "content": build_prompt(dream, archive, number, name, language)}],
        )
    except anthropic.RateLimitError:
        raise DreamverseError("Te veel aanvragen achter elkaar. Wacht even en probeer opnieuw.")
    except anthropic.AuthenticationError:
        raise DreamverseError("De inloggegevens worden niet geaccepteerd. Controleer "
                              "ANTHROPIC_API_KEY in .env, of draai `ant auth login` opnieuw.")
    except anthropic.APIConnectionError:
        raise DreamverseError("Geen verbinding met de API. Controleer je internetverbinding.")
    except anthropic.APIStatusError as e:
        # Deze komt vaak genoeg voor om apart te benoemen: ingelogd zijn en
        # tegoed hebben zijn twee verschillende dingen.
        if "credit balance" in str(e).lower():
            # Wel ingelogd, geen tegoed. De verbeelding kan dan niet geschreven
            # worden; we tonen de voorbeeldverbeelding en zeggen erbij waarom.
            return voorbeeld(
                "Geen tegoed op je Anthropic-account, dus dit is een voorbeeld. "
                "Waardeer op via console.anthropic.com onder Plans & Billing; "
                "een droom kost ongeveer vijf cent.")
        raise DreamverseError("De API gaf een fout ({}). Probeer het later opnieuw.".format(e.status_code))

    if response.stop_reason == "refusal":
        raise DreamverseError("Deze droom kon niet worden uitgewerkt. Probeer hem anders te beschrijven.")

    text = "".join(b.text for b in response.content if b.type == "text")
    if not text.strip():
        raise DreamverseError("Er kwam niets terug. Probeer het nog een keer.")

    episode = parse_episode(text)
    episode["demo"] = False
    episode["usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return episode


def create(dream, kwaliteit=None):
    """De hele stap: schrijven, opslaan, teruggeven."""
    dream = (dream or "").strip()
    if not dream:
        raise DreamverseError("Schrijf eerst je droom op.")
    if len(dream) > 4000:
        raise DreamverseError("Dat is een lange droom. Vat hem samen in maximaal 4000 tekens.")

    # Twee poortjes vóór het geld uitgeven: mag er een droom bij, en mag deze
    # kwaliteit. Allebei kunnen tokens kosten.
    kosten_tokens = plans.check_dream()
    niveau, kwaliteit_tokens = plans.check_kwaliteit(kwaliteit or plans.DEFAULT_KWALITEIT)

    archive = load_archive()
    number = next_number()

    profiel = load_profile()
    episode = write_episode(dream, archive, number, profiel.get("name"),
                            profiel.get("language", "nl"))

    # Opnieuw bepalen: het schrijven duurt een minuut, en in die tijd kan deze
    # gebruiker in een tweede tabblad een droom hebben ingestuurd.
    number = next_number()
    episode["number"] = number
    # Ligt er nog materiaal onder dit nummer van een gewiste droom, dan gaat dat
    # er nu af. Anders erft deze droom beelden die niet bij hem horen.
    _ruim_nummer_op(number)
    accounts.zet_droom(uid(), number, dream, episode["title"],
                       episode.get("motifs", []), date.today().isoformat())

    plans.charge_dream(kosten_tokens + kwaliteit_tokens)
    # De droom zelf hoort bij de verbeelding: de hele duiding verwijst ernaar,
    # en zonder die tekst is het bij het terugkijken raden waar het over ging.
    episode["dream"] = dream
    episode["tokens_charged"] = kosten_tokens + kwaliteit_tokens
    episode["quality"] = kwaliteit or plans.DEFAULT_KWALITEIT

    u = episode.get("usage") or {}
    usage.episode(number, u.get("input_tokens", 0), u.get("output_tokens", 0),
                  demo=episode.get("demo"))

    save_episode(number, episode)

    # Het tekenwerk loopt op de achtergrond verder; de verbeelding is al leesbaar.
    # In het gratis pakket blijft het bij de getekende composities.
    # Wat er gemaakt wordt hangt van de gekozen kwaliteit af, niet van het pakket:
    # wie alleen de duiding wil, betaalt ook niet voor beeld.
    instelling = plans.VIDEO.get(niveau["video"]) if niveau["video"] else None
    if niveau["panelen"]:
        # Het kernmoment volgt op de panelen: dat heeft het getekende beeld nodig
        # als startframe, anders verspringt de stijl.
        episode["images_pending"] = kling.render_async(
            sleutel(number), episode["panels"], episode.get("key_panel"), instelling)
        episode["video_pending"] = bool(instelling)
    else:
        episode["images_pending"] = False
        episode["video_pending"] = False
    # De stem hoort bij de tekst, niet bij het beeld: die komt er altijd.
    episode["voice_pending"] = stem.render_async(sleutel(number), episode["panels"])

    return episode


# --------------------------------------------------------------------------- #
# Het voorbeeld — draait zonder API-sleutel
# --------------------------------------------------------------------------- #

DEMO_EPISODE = {
    "title": "De rechthoek blauw licht",
    "panels": [
        {"narration": "Je bent al boven de kam voordat je merkt dat je niet loopt. "
                      "De lucht draagt je alsof dat altijd zo geweest is.",
         "image": "a lone figure gliding high above dark mountain ridges at night, seen from behind and above",
         "palette": "crown", "motif": "flight"},
        {"narration": "Onder je schuiven de bergen weg als lakens. Er is geen angst om te vallen, "
                      "en dat is het vreemdste eraan. Alleen ruimte.",
         "image": "vast mountain ranges sliding away below, clouds far under the viewer, open sky",
         "palette": "third_eye", "motif": "expanse"},
        {"narration": "Dan, diep in het dal, een rechthoek blauw licht. Water waar geen water "
                      "hoort te zijn. Je gaat er vanzelf naartoe.",
         "image": "a lit rectangular swimming pool glowing blue deep in a dark valley, seen from high above",
         "palette": "throat", "motif": "structure"},
        {"narration": "Aan de rand zit ze, en je kent haar meteen. Ze huilt, en het geluid draagt "
                      "tot hierboven — het eerste geluid in deze droom.",
         "image": "a seated figure at the edge of a glowing pool at night, head bowed, water reflecting light",
         "palette": "heart", "motif": "figure"},
        {"narration": "Je landt zonder te landen. Ze kijkt op. Het water beweegt nog, alsof er net "
                      "iemand in gesprongen is.",
         "image": "close on the surface of water at dawn, wide ripples spreading outward, warm light on the water",
         "palette": "sacral", "motif": "close"},
    ],
    "threads": [
        {"ref": "Droom 12", "was": "Hetzelfde zwembad, maar leeg, en het water stond stil.",
         "now": "Nu zit er iemand aan de rand."},
        {"ref": "Droom 29", "was": "Vliegen kostte moeite; je moest je afzetten om niet te zakken.",
         "now": "Nu draagt de lucht je zonder dat je iets doet."},
        {"ref": "Droom 38", "was": "Dezelfde vriendin wilde spreken, maar er kwam geen geluid.",
         "now": "Nu draagt haar stem tot boven de bergen."},
    ],
    "why": "Je slaap werkt de laatste maanden aan één ding: moeite die verdwijnt. In april was het bad "
           "leeg, in juni was vliegen zwaar, in augustus viel er geen woord. Vannacht kwamen die drie "
           "samen en waren ze alle drie opgelost.",
    "meaning": "Het beeld is vriendelijker dan het klinkt. Je ziet iemand huilen, maar wat er werkelijk "
               "gebeurt is dat je haar hóórt. Verdriet dat gehoord wordt, is verdriet dat mag bestaan. "
               "En je hoefde niet te besluiten om te dalen: het blauwe licht trok je.",
    "future": "De komende weken word je waarschijnlijk degene naar wie iemand toe komt. Reken op een "
              "gesprek dat je niet zelf begint en dat langer duurt dan gepland. En let op je eigen tempo: "
              "iets waar je maanden op hebt moeten duwen, gaat binnenkort vanzelf.",
    "question": "Is er iemand die je deze week iets zou willen laten zeggen, gewoon door er te zijn?",
    "motifs": ["zwembad", "vliegen", "een huilende vriendin", "bergen"],
}
