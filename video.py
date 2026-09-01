"""Het bewegende kernmoment.

Eén paneel per aflevering wordt echte video. Niet vijf: vier seconden op het
beste model kost EUR 1,47, dus een hele aflevering van twintig seconden is
EUR 7,36 en dat past in geen enkel maandbedrag. Eén moment wel, en het tilt de
rest op — de stilstaande panelen eromheen voelen dan als opbouw in plaats van
als vulling.

Welk paneel het draaipunt is, kiest het model dat de aflevering schrijft; het
geeft dat mee als `key_panel`. Wij animeren precies dat paneel, met het beeld
dat Kling er al van maakte als startframe. Zo blijft de stijl van de reeks
overeind: het is letterlijk hetzelfde plaatje, dat gaat bewegen.

Welk videomodel gebruikt wordt hangt van het pakket af (zie plans.VIDEO):

    snel   veo3.1_fast met geluid   15 credits/seconde   EUR 0,55 voor vier seconden
    top    veo3.1 met geluid        40 credits/seconde   EUR 1,47 voor vier seconden

Mislukt het, dan blijft het stilstaande paneel staan. Dat is de hele
foutafhandeling: beeld is een verrijking, nooit een voorwaarde.
"""

import base64
import json
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
PANELS = ROOT / "data" / "panels"

POLL_EVERY = 5
POLL_MAX = 60  # vijf minuten; veo doet er meestal veertig seconden over
RATIO = "1280:720"


class VideoError(Exception):
    pass


def _client():
    from runwayml import RunwayML
    return RunwayML()


def beweging_voor(panel):
    """Wat er moet bewegen. Kort houden: het startframe zegt al hoe het eruitziet."""
    beeld = (panel.get("image") or panel.get("narration") or "").strip()
    return (beeld + ". Subtle cinematic motion, slow camera move, the light breathing. "
            "Keep the painted watercolour look; do not change the composition.")


def render(number, panels, key_index, instelling):
    """Maak de video voor één paneel. Geeft het pad terug, of laat een fout los."""
    if not instelling:
        raise VideoError("Dit pakket bevat geen video.")
    startframe = None
    for suffix in (".png", ".jpg", ".webp"):
        kandidaat = PANELS / "{}-{}{}".format(number, key_index, suffix)
        if kandidaat.is_file():
            startframe = kandidaat
            break
    if startframe is None:
        raise VideoError("Het paneel dat moet bewegen bestaat nog niet.")

    uri = "data:image/{};base64,{}".format(
        "png" if startframe.suffix == ".png" else "jpeg",
        base64.b64encode(startframe.read_bytes()).decode())

    c = _client()
    taak = c.image_to_video.create(
        model=instelling["model"],
        prompt_image=uri,
        prompt_text=beweging_voor(panels[key_index]),
        duration=instelling["seconden"],
        ratio=RATIO,
        audio=instelling.get("audio", True),
    )

    for _ in range(POLL_MAX):
        time.sleep(POLL_EVERY)
        t = c.tasks.retrieve(taak.id)
        if t.status == "SUCCEEDED":
            blob = urllib.request.urlopen(t.output[0], timeout=180).read()
            doel = PANELS / "{}-hero.mp4".format(number)
            tmp = doel.with_suffix(".part")
            tmp.write_bytes(blob)
            tmp.replace(doel)
            return doel
        if t.status == "FAILED":
            raise VideoError((getattr(t, "failure", "") or "de taak mislukte")[:160])
    raise VideoError("De video werd niet op tijd klaar.")


def _in_state(number, **velden):
    """Schrijf het resultaat bij in het bestand dat de browser al ophaalt."""
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


def _werk(number, panels, key_index, instelling):
    _in_state(number, video_status="busy", video_panel=key_index)
    try:
        doel = render(number, panels, key_index, instelling)
    except Exception as e:
        print("video: kernmoment van droom {} mislukt: {}".format(number, e), flush=True)
        _in_state(number, video_status="failed", video_error=str(e)[:200])
        return
    import usage
    usage.hero_video(number, key_index, instelling)
    _in_state(number, video_status="done", video="/panels/" + doel.name)
    print("video: kernmoment van droom {} klaar ({})".format(number, instelling["model"]), flush=True)


def _werk_alles(number, panels, instelling):
    """Elk paneel apart animeren: de hele aflevering als film."""
    _in_state(number, film_status="busy")
    gemaakt = {}
    for i in range(len(panels)):
        try:
            doel = PANELS / "{}-film-{}.mp4".format(number, i)
            bron = render(number, panels, i, instelling)
            bron.replace(doel)
            gemaakt[str(i)] = "/panels/" + doel.name
            _in_state(number, film=gemaakt)
        except Exception as e:
            print("video: paneel {} van droom {} mislukt: {}".format(i, number, e), flush=True)
    import usage
    for i in gemaakt:
        usage.hero_video(number, int(i), instelling)
    _in_state(number, film_status="done", film=gemaakt)
    print("video: film van droom {} klaar ({} panelen)".format(number, len(gemaakt)), flush=True)


def film_async(number, panels, instelling):
    """De hele aflevering als film. Kost tokens, dus alleen op verzoek."""
    if not instelling:
        return False
    threading.Thread(target=_werk_alles, args=(number, panels, instelling), daemon=True).start()
    return True


def render_async(number, panels, key_index, instelling):
    """Start het animeren op de achtergrond. Geeft meteen terug."""
    if not instelling or key_index is None:
        return False
    if not (0 <= key_index < len(panels)):
        return False
    threading.Thread(target=_werk, args=(number, panels, key_index, instelling),
                     daemon=True).start()
    return True
