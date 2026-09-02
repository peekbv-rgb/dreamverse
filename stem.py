"""De verteller: de verbeelding ingesproken door een echte stem.

Waarom niet de stem van de browser: die is een loterij. Op deze machine staat
precies één Nederlandse stem, Microsoft Frank, en dat is een man. Op het ene
apparaat klinkt je app dus als een vrouw en op het andere als een computer uit
2009 — en jij kunt daar niets aan doen.

Waarom niet Vera's eigen stem: avatarstemmen en voorleesstemmen zijn bij Runway
twee losse verzamelingen. Violet bestaat alleen als avatar en kan geen tekst
voorlezen.

Dus: één meertalige stem die Nederlands spreekt, gelijk voor elke bezoeker.
`eleven_multilingual_v2` rekent 1 credit per 50 tekens, dus vijf panelen van
samen ongeveer 450 tekens kosten 9 credits — rond de acht cent per verbeelding.

Mislukt het, dan valt de speler terug op de stem van de browser. Geluid is een
verrijking, geen voorwaarde.
"""

import json
import os
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
PANELS = ROOT / "data" / "panels"

MODEL = "eleven_multilingual_v2"
# Vrouwelijke presets in deze set: Maya, Serene, Mabel, Eleanor, Sandra, Kylie,
# Lara, Lisa, Marlene, Miriam, Paula, Maggie, Katie, Rina, Ella, Mariah,
# Claudia, Niki, Myrna, Wanda, Kiana, Rachel, Leslie. Serene past bij een gids
# die stiltes laat vallen; te wisselen met VERTELSTEM in .env.
STEM = os.environ.get("VERTELSTEM", "Serene")
CREDITS_PER_50_TEKENS = 1
POLL_EVERY = 3
POLL_MAX = 40


class StemError(Exception):
    pass


def enabled():
    return bool(os.environ.get("RUNWAYML_API_SECRET")) and os.environ.get("VERTELLER", "1") != "0"


def kosten_euro(tekst):
    credits = max(1, -(-len(tekst) // 50)) * CREDITS_PER_50_TEKENS
    return credits * 0.01 * 0.92


def spreek(tekst, doel):
    """Eén stuk tekst inspreken en opslaan. Geeft het pad terug."""
    from runwayml import RunwayML
    c = RunwayML()
    taak = c.text_to_speech.create(
        model=MODEL,
        prompt_text=tekst[:900],
        voice={"type": "runway-preset", "preset_id": STEM},
        output_format="mp3",
        language_code="nl",
    )
    for _ in range(POLL_MAX):
        time.sleep(POLL_EVERY)
        t = c.tasks.retrieve(taak.id)
        if t.status == "SUCCEEDED":
            blob = urllib.request.urlopen(t.output[0], timeout=120).read()
            tmp = doel.with_suffix(".part")
            tmp.write_bytes(blob)
            tmp.replace(doel)
            return doel
        if t.status == "FAILED":
            raise StemError((getattr(t, "failure", "") or "de taak mislukte")[:160])
    raise StemError("De stem werd niet op tijd klaar.")


def _in_state(number, **velden):
    pad = PANELS / "{}.json".format(number)
    try:
        with pad.open(encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        state = {"status": "done", "images": {}, "errors": {}}
    state.update(velden)
    tmp = pad.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(pad)


def _werk(number, panels):
    PANELS.mkdir(parents=True, exist_ok=True)
    stemmen = {}
    _in_state(number, stem_status="busy")
    for i, panel in enumerate(panels):
        tekst = (panel.get("narration") or "").strip()
        if not tekst:
            continue
        doel = PANELS / "{}-stem-{}.mp3".format(number, i)
        try:
            spreek(tekst, doel)
            stemmen[str(i)] = "/panels/" + doel.name
            _in_state(number, stem=stemmen)
        except Exception as e:
            print("stem: paneel {} van droom {} mislukt: {}".format(i, number, e), flush=True)
    if stemmen:
        import usage
        usage.narration(number, len(stemmen),
                        sum(kosten_euro(p.get("narration") or "") for p in panels))
    _in_state(number, stem_status="done", stem=stemmen)
    print("stem: droom {} ingesproken ({} panelen)".format(number, len(stemmen)), flush=True)


def render_async(number, panels):
    if not enabled():
        return False
    threading.Thread(target=_werk, args=(number, panels), daemon=True).start()
    return True
