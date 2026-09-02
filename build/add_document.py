"""Een kennisdocument bij Vera zetten.

    python build/add_document.py knowledge/chakras.txt

`avatars.update(document_ids=...)` VERVANGT de hele set, dus dit script stuurt
altijd alles mee wat er al hing. Welke dat zijn staat in build/document-ids.json;
dat bestand is daarmee geen administratie maar een voorwaarde. Weggooien betekent
dat de volgende koppeling de rest eraf haalt.

Het inhoudsfilter van Runway is grillig: dezelfde tekst wordt soms een paar keer
geweigerd en daarna geaccepteerd. Dus blijven proberen.
"""

import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
VERA = "43e6b2b0-29ea-4125-8e2f-3ebed04f65d1"
REGISTER = HERE / "document-ids.json"


def client():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    if not os.environ.get("RUNWAYML_API_SECRET"):
        sys.exit("Geen RUNWAYML_API_SECRET in .env.")
    from runwayml import RunwayML
    return RunwayML()


def volhardend(werk, wat):
    for poging in range(1, 16):
        try:
            return werk()
        except Exception as e:
            if "cannot be used for an avatar" not in str(e):
                sys.exit("%s mislukte: %s" % (wat, e))
            time.sleep(3)
    sys.exit("%s: vijftien keer geweigerd door het filter." % wat)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    pad = pathlib.Path(sys.argv[1])
    if not pad.is_file():
        sys.exit("Niet gevonden: %s" % pad)

    tekst = pad.read_text(encoding="utf-8")
    c = client()

    register = json.loads(REGISTER.read_text(encoding="utf-8")) if REGISTER.exists() else {}
    oud = register.get(pad.name)

    print("Uploaden: %s (%d tekens)" % (pad.name, len(tekst)))
    doc = volhardend(lambda: c.documents.create(name=pad.name, content=tekst), "Uploaden")
    register[pad.name] = doc.id
    print("  id: %s" % doc.id)

    # Alles wat er hing plus deze. Zonder de rest zou de update ze eraf halen.
    ids = sorted(set(register.values()))
    print("Koppelen aan Vera: %d document(en)" % len(ids))
    volhardend(lambda: c.avatars.update(VERA, document_ids=ids), "Koppelen")

    REGISTER.write_text(json.dumps(register, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    if oud and oud != doc.id:
        # De vorige versie hangt er niet meer aan en kan weg.
        try:
            c.documents.delete(oud)
            print("  oude versie %s opgeruimd" % oud)
        except Exception as e:
            print("  oude versie %s bleef staan: %s" % (oud, e))

    time.sleep(2)
    avatar = c.avatars.retrieve(VERA)
    print("\nVera staat nu zo:")
    print("  documenten : %d" % len(avatar.document_ids or []))
    print("  persona    : %d tekens" % len(avatar.personality or ""))
    print("  status     : %s" % avatar.status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
