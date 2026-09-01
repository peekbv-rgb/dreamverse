"""Vera's taal en stem omzetten, zodat je ze kunt horen in plaats van gokken.

    python build/set_vera.py                      # laat zien wat er nu staat
    python build/set_vera.py --taal en            # ze spreekt Engels
    python build/set_vera.py --stem clara         # andere stem
    python build/set_vera.py --taal de --stem georgia

Runway's dertig stemmen dragen geen taal in zich. Elke stem legt zijn eigen
accent over het Nederlands, Engels of Duits heen, en er is geen manier om dat
vooraf te horen: de voorbeeldfunctie gebruikt een heel andere set stemmen. Dus
omzetten, verbinden, luisteren, en weer omzetten.

Het raakt alleen wat je noemt. Kennisdocumenten en de rest van de persona blijven
staan — belangrijk, want `avatars.update(document_ids=...)` vervangt de hele set
zodra je dat veld wél meestuurt.
"""

import argparse
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
VERA = "43e6b2b0-29ea-4125-8e2f-3ebed04f65d1"

# De omschrijvingen komen van Runway zelf, uitgelezen via het avatar-object.
VOICES = {
    "luna": "Persuasive", "aurora": "Bright", "clara": "Soft", "mia": "Youthful",
    "maya": "Upbeat", "violet": "Gentle", "summer": "Breezy", "ruby": "Easy-going",
    "victoria": "Firm", "skye": "Bright", "emma": "Clear", "georgia": "Mature",
    "petra": "Forward", "nina": "Smooth", "morgan": "Informative",
    # De overige presets bestaan wel, maar hun omschrijving heb ik niet uitgelezen.
    "vincent": "?", "drew": "?", "max": "?", "felix": "?", "marcus": "?",
    "jasper": "?", "leo": "?", "adrian": "?", "blake": "?", "david": "?",
    "nathan": "?", "sam": "?", "adam": "?", "zach": "?", "roman": "?",
}

# De rest van de persona blijft Nederlands: het model leest dat prima en het
# scheelt drie versies onderhouden. Alleen de taalregel gaat er bovenop, in de
# taal zelf, want dat is het enige wat de uitspraak stuurt.
TAALREGEL = {
    "nl": "",
    "en": (
        "SPEAK ENGLISH. Every word you say is in English, whatever language the "
        "rest of these instructions are written in. Address the dreamer as you. "
        "Keep the same voice: calm, short sentences, one question at a time, and "
        "let silences fall.\n\n"
    ),
    "de": (
        "SPRICH DEUTSCH. Alles, was du sagst, ist auf Deutsch, egal in welcher "
        "Sprache der Rest dieser Anweisungen geschrieben ist. Duze die träumende "
        "Person. Bleib dieselbe: ruhig, kurze Sätze, eine Frage nach der anderen, "
        "und lass Stille zu.\n\n"
    ),
}

OPENING = {
    "nl": None,  # uit persona/vera-start-script.txt
    "en": ("Good morning. I'm Vera. Tell me what you saw last night, before it "
           "slips away — it doesn't have to be in order and it doesn't have to make sense."),
    "de": ("Guten Morgen. Ich bin Vera. Erzähl mir, was du heute Nacht gesehen hast, "
           "bevor es verschwindet — es muss nicht der Reihe nach sein und es muss "
           "keinen Sinn ergeben."),
}


def client():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    if not os.environ.get("RUNWAYML_API_SECRET"):
        sys.exit("Geen RUNWAYML_API_SECRET in .env.")
    from runwayml import RunwayML
    return RunwayML()


def huidige_taal(personality):
    for taal, regel in TAALREGEL.items():
        if regel and personality.startswith(regel.strip()[:20]):
            return taal
    return "nl"


def toon(avatar):
    print("stem     : %s (%s)" % (avatar.voice.name, avatar.voice.description))
    print("taal     : %s" % huidige_taal(avatar.personality or "").upper())
    print("persona  : %d tekens" % len(avatar.personality or ""))
    print("documenten: %d gekoppeld" % len(avatar.document_ids or []))
    print("openingszin: %s" % ((avatar.start_script or "")[:70] + "…"))
    print("status   : %s" % avatar.status)


def main():
    ap = argparse.ArgumentParser(description="Vera's taal en stem omzetten.")
    ap.add_argument("--taal", choices=sorted(TAALREGEL), help="nl, en of de")
    ap.add_argument("--stem", help="een van: " + ", ".join(sorted(VOICES)))
    args = ap.parse_args()

    c = client()

    if not args.taal and not args.stem:
        print("Vera staat nu zo:\n")
        toon(c.avatars.retrieve(VERA))
        print("\nStemmen met een bekende omschrijving:")
        for naam, omschrijving in sorted(VOICES.items()):
            if omschrijving != "?":
                print("  %-10s %s" % (naam, omschrijving))
        return 0

    update = {}

    if args.taal:
        basis = (ROOT / "persona" / "vera-personality.txt").read_text(encoding="utf-8")
        update["personality"] = TAALREGEL[args.taal] + basis
        opening = OPENING[args.taal]
        if opening is None:
            opening = (ROOT / "persona" / "vera-start-script.txt").read_text(encoding="utf-8").strip()
        update["start_script"] = opening

    if args.stem:
        stem = args.stem.lower()
        if stem not in VOICES:
            sys.exit("Onbekende stem. Kies uit: " + ", ".join(sorted(VOICES)))
        update["voice"] = {"type": "runway-live-preset", "preset_id": stem}

    # document_ids staat er bewust niet in: meesturen zou de hele set vervangen.
    #
    # Het inhoudsfilter van Runway is grillig: exact dezelfde tekst wordt soms
    # zes keer geweigerd en de zevende keer geaccepteerd, met een melding over
    # inhoud terwijl er niets aan de inhoud mankeert. Dus blijven proberen.
    import time
    for poging in range(1, 16):
        try:
            c.avatars.update(VERA, **update)
            if poging > 1:
                print("(het filter weigerde %d keer voordat het lukte)" % (poging - 1))
            break
        except Exception as e:
            if "cannot be used for an avatar" not in str(e):
                sys.exit("Omzetten mislukte: %s" % e)
            time.sleep(3)
    else:
        sys.exit("Vijftien keer geweigerd door het filter. Probeer het zo nog eens.")

    # Runway leest even achter op een schrijfactie, dus niet meteen aflezen.
    time.sleep(2)
    print("Omgezet. Vera staat nu zo:\n")
    toon(c.avatars.retrieve(VERA))
    print("\nHerlaad de pagina en druk op 'Praat met Vera'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
