"""Dreamverse — een droom erin, een aflevering eruit.

Eén droom wordt een aflevering van vijf panelen met een duiding in drie delen:
waarom je dit droomde, wat het zegt, en wat eraan zit te komen. Elke eerdere
droom telt mee, want daar zit het hele idee in: terugkerende plaatsen, personen
en dieren maken er na een paar maanden één wereld van.

Zonder ANTHROPIC_API_KEY draait alles behalve het schrijven: dan komt er een
vaste voorbeeldaflevering terug met demo=True. Zo is de app te starten en te
demonstreren voordat er een cent aan tokens is uitgegeven.
"""

import json
import os
import re
import threading
from datetime import date
from pathlib import Path

import kling
import plans
import stem
import usage

ROOT = Path(__file__).parent
DATA = ROOT / "data"
ARCHIVE = DATA / "archive.json"
PROFILE = DATA / "profile.json"
EPISODES = DATA / "episodes"

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

def load_archive():
    try:
        with ARCHIVE.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, OSError):
        # Liever een leeg archief dan een app die niet start.
        return []


def save_archive(archive):
    DATA.mkdir(exist_ok=True)
    tmp = ARCHIVE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)
    tmp.replace(ARCHIVE)  # atomisch: nooit een half weggeschreven archief


def next_number(archive):
    return max((d.get("n", 0) for d in archive), default=0) + 1


def load_profile():
    try:
        with PROFILE.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_profile(profile):
    DATA.mkdir(exist_ok=True)
    tmp = PROFILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    tmp.replace(PROFILE)


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
    with _lock:
        profile = load_profile()
        if "name" in velden:
            profile["name"] = (velden.get("name") or "").strip()[:60]
        if "birthdate" in velden:
            datum = (velden.get("birthdate") or "").strip()[:10]
            profile["birthdate"] = datum
        if "gender" in velden:
            g = velden.get("gender")
            profile["gender"] = g if g in GESLACHTEN else "onbekend"
        if "language" in velden:
            t = velden.get("language")
            profile["language"] = t if t in TALEN else "nl"
        if "guardian_ok" in velden:
            profile["guardian_ok"] = bool(velden.get("guardian_ok"))
        save_profile(profile)
    return public_profile()


def public_profile():
    """Het profiel zoals de app het mag zien, met de leeftijd erbij gerekend."""
    profile = load_profile()
    leeftijd = leeftijd_uit(profile.get("birthdate"))
    return {
        "name": profile.get("name", ""),
        "birthdate": profile.get("birthdate", ""),
        "age": leeftijd,
        "minor": leeftijd is not None and leeftijd < 18,
        "guardian_ok": bool(profile.get("guardian_ok")),
        "gender": profile.get("gender", "onbekend"),
        "language": profile.get("language", "nl"),
    }


def set_name(name):
    return set_profile({"name": name})


def save_episode(number, episode):
    """Bewaar de hele aflevering, zodat hij terug te kijken is.

    Zonder dit is een aflevering weg zodra je de pagina ververst, en zou iemand
    opnieuw moeten betalen voor beelden die al gemaakt zijn. De panelen en de
    video staan al als bestand in data/panels; hier komt de tekst bij die erbij
    hoort.
    """
    EPISODES.mkdir(parents=True, exist_ok=True)
    pad = EPISODES / "{}.json".format(number)
    tmp = pad.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(episode, f, ensure_ascii=False, indent=2)
    tmp.replace(pad)


def load_episode(number):
    """Een eerder gemaakte aflevering terughalen. None als hij er niet is."""
    try:
        with (EPISODES / "{}.json".format(number)).open(encoding="utf-8") as f:
            episode = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        # Dromen van voor het bewaren bestaan alleen nog als panelen op schijf.
        # Daar valt genoeg uit af te leiden om er beeld bij te kunnen kopen.
        panelen = sorted(kling.PANELS.glob("{}-[0-9].*".format(number)))
        beelden = [p for p in panelen if p.suffix.lower() in (".png", ".jpg", ".webp")]
        if not beelden:
            return None
        titel = next((x.get("title") for x in load_archive() if x.get("n") == number), None)
        return {
            "number": number,
            "title": titel or "Droom {}".format(number),
            "panels": [{"narration": "", "image": "", "palette": "crown", "motif": "expanse"}
                       for _ in beelden],
            "key_panel": min(2, len(beelden) - 1),
            "threads": [], "why": "", "meaning": "", "future": "", "question": "",
            "onvolledig": True,
        }
    for d in load_archive():
        if d.get("n") == number and d.get("answer"):
            episode["answer"] = d["answer"]
    return episode


def answer_question(number, answer):
    """Bewaar wat de dromer op de slotvraag antwoordde.

    Dat antwoord is het waardevolste wat er is: het is het enige stuk tekst dat
    de dromer schrijft nadat hij zijn droom heeft teruggezien. Het gaat mee in
    het geheugen en dus in de volgende duiding.
    """
    answer = (answer or "").strip()[:1000]
    if not answer:
        raise DreamverseError("Er stond niets in je antwoord.")
    with _lock:
        archive = load_archive()
        for d in archive:
            if d.get("n") == number:
                d["answer"] = answer
                save_archive(archive)
                return d
    raise DreamverseError("Die droom staat niet in je archief.")


def delete_dream(number):
    """Een droom weghalen: uit het archief, de bewaarde aflevering en de beelden.

    Alles weg betekent hier ook echt alles. Iemand die zijn droom wist verwacht
    niet dat de panelen ervan nog op de schijf staan.
    """
    with _lock:
        archive = load_archive()
        over = [d for d in archive if d.get("n") != number]
        if len(over) == len(archive):
            raise DreamverseError("Die droom staat niet in je archief.")
        save_archive(over)

    (EPISODES / "{}.json".format(number)).unlink(missing_ok=True)
    for pad in kling.PANELS.glob("{}-*".format(number)):
        pad.unlink(missing_ok=True)
    (kling.PANELS / "{}.json".format(number)).unlink(missing_ok=True)
    return {"deleted": number, "over": len(over)}


def clear_archive():
    with _lock:
        save_archive([])


# --------------------------------------------------------------------------- #
# De prompt
# --------------------------------------------------------------------------- #

RULES = f"""Je schrijft een aflevering voor Dreamverse: de droom van de gebruiker als korte,
literaire film in vijf panelen.

Toon en taal:
- Alles in het Nederlands, in de je-vorm, tegenwoordige tijd. Beeldend, maar zonder
  bloemrijke overdaad. Kort is beter dan mooi.
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

Antwoord met uitsluitend geldige JSON, zonder tekst eromheen, in deze vorm:

{{"title": string,
 "panels": [{{"narration": string, "image": string, "palette": string, "motif": string}}],
 "threads": [{{"ref": string, "was": string, "now": string}}],
 "why": string, "meaning": string, "future": string, "love": string,
 "today": string, "season": string,
 "question": string, "motifs": [string], "key_panel": number}}

Regels voor de velden:
- Precies 5 panelen. "narration" is 1 tot 2 zinnen Nederlands.
- "image" is een korte Engelse beschrijving van wat er te zien is, voor een
  illustratiemodel: alleen het beeld, geen namen, geen tekst in beeld, geen
  emoties benoemen. Bijvoorbeeld: "a figure gliding high above dark mountain
  ridges, a lit rectangular pool far below in the valley".
- palette is het kleurveld dat bij het gevoel van dat paneel past, een van:
  {", ".join(PALETTES)}. Betekenis: {CHAKRA_HINT}.
  Laat het door de aflevering heen verschuiven; vijf keer hetzelfde veld is bijna nooit waar.
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


def build_prompt(dream, archive, number, name=None):
    wie = ""
    if name:
        # Spaarzaam gebruiken: een duiding die elke zin je naam noemt klinkt als
        # een verkooptelefoontje, niet als iemand die naar je luistert.
        wie = ("\n\nDe dromer heet {}. Gebruik die naam hooguit een of twee keer "
               "in de hele aflevering, op een moment dat het iets doet.").format(name)
    return (
        RULES
        + wie
        + "\n\n--- eerdere dromen ---\n"
        + _history(archive)
        + "\n\n--- de droom van vannacht (dit wordt Droom {}) ---\n".format(number)
        + dream
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

    return {
        "key_panel": sleutel,
        "title": str(data.get("title") or "Naamloze droom"),
        "panels": panels,
        "threads": threads,
        "why": str(data.get("why") or ""),
        "love": str(data.get("love") or ""),
        "today": str(data.get("today") or ""),
        "season": str(data.get("season") or ""),
        "meaning": str(data.get("meaning") or ""),
        "future": str(data.get("future") or ""),
        "question": str(data.get("question") or ""),
        "motifs": [str(m) for m in (data.get("motifs") or [])][:8],
    }


# --------------------------------------------------------------------------- #
# Schrijven
# --------------------------------------------------------------------------- #

def voorbeeldaflevering(reden):
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


def write_episode(dream, archive, number, name=None):
    """Vraag Claude om de aflevering. Zonder sleutel: de voorbeeldaflevering."""
    if not credentials_available():
        return voorbeeldaflevering("Er zijn geen inloggegevens; dit is een voorbeeldaflevering.")

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
            # scheelt direct in de kostprijs per aflevering.
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": build_prompt(dream, archive, number, name)}],
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
            # Wel ingelogd, geen tegoed. De aflevering kan dan niet geschreven
            # worden; we tonen de voorbeeldaflevering en zeggen erbij waarom.
            return voorbeeldaflevering(
                "Geen tegoed op je Anthropic-account, dus dit is een voorbeeldaflevering. "
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


def create(dream):
    """De hele stap: schrijven, opslaan, teruggeven."""
    dream = (dream or "").strip()
    if not dream:
        raise DreamverseError("Schrijf eerst je droom op.")
    if len(dream) > 4000:
        raise DreamverseError("Dat is een lange droom. Vat hem samen in maximaal 4000 tekens.")

    # Poortje vóór het geld uitgeven, niet erna.
    kosten_tokens = plans.check_dream()

    with _lock:
        archive = load_archive()
        number = next_number(archive)

    episode = write_episode(dream, archive, number, load_profile().get("name"))
    episode["number"] = number

    with _lock:
        archive = load_archive()  # opnieuw laden: er kan intussen iets bij zijn gekomen
        number = next_number(archive)
        episode["number"] = number
        archive.append({
            "n": number,
            "text": dream,
            "title": episode["title"],
            "motifs": episode.get("motifs", []),
            "when": date.today().isoformat(),
        })
        save_archive(archive)

    plans.charge_dream(kosten_tokens)
    episode["tokens_charged"] = kosten_tokens

    u = episode.get("usage") or {}
    usage.episode(number, u.get("input_tokens", 0), u.get("output_tokens", 0),
                  demo=episode.get("demo"))

    save_episode(number, episode)

    # Het tekenwerk loopt op de achtergrond verder; de aflevering is al leesbaar.
    # In het gratis pakket blijft het bij de getekende composities.
    if plans.panels_allowed():
        # Het kernmoment volgt op de panelen: dat heeft het getekende beeld nodig
        # als startframe, anders verspringt de stijl.
        instelling = plans.video_for_plan()
        episode["images_pending"] = kling.render_async(
            number, episode["panels"], episode.get("key_panel"), instelling)
        episode["video_pending"] = bool(instelling)
        # Inspreken heeft de beelden niet nodig en loopt er dus naast.
        episode["voice_pending"] = stem.render_async(number, episode["panels"])
    else:
        episode["images_pending"] = False
        episode["video_pending"] = False
        episode["panels_locked"] = True

    return episode


# --------------------------------------------------------------------------- #
# Voorbeeldaflevering — draait zonder API-sleutel
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
