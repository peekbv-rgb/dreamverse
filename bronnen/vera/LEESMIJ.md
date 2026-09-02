# De bronbestanden van Vera's welkomstboodschap

Dit is het eerste wat iemand van Dreamverse ziet. Hier staan de originelen, zodat
het opnieuw te maken is zonder alles opnieuw te genereren.

| Bestand | Wat het is |
|---|---|
| `begroeting-met-stilte-nl.mp3` | De gesproken begroeting plus zes seconden stilte |
| `begroeting-met-stilte-en.mp3` | Dezelfde in het Engels |
| `intro-nl-ongeknipt.mp4` | De eerste versie, alleen de gesproken tekst (5,67 s) |
| `intro-en-ongeknipt-lang.mp4` | De Engelse generatie met twaalf seconden stilte (16,6 s), waar de gebruikte clip uit geknipt is |

Wat in `static/` staat is het resultaat: `vera-intro-nl.mp4` (11,5 s) en
`vera-intro-en.mp4` (8,5 s).

## Waarom er stilte achter de spraak zit

Vera moet praten als de app opengaat, en daarna niet bevriezen en ook niet haar
tekst opnieuw mimen. De eerste opzet was een tweede clip die op het laatste frame
van de eerste begon. Dat was niet goed genoeg: hoe precies het aansluitframe ook
gekozen was, twee generaties leveren net andere kleur en scherpte, en die overgang
zie je.

De oplossing zit in de audio. Runway's avatar accepteert geluid in plaats van
tekst, dus door zes seconden stilte achter de begroeting te plakken komt alles uit
één generatie: ze praat, en blijft daarna zes seconden rustig staan, ademen en
kijken. Er valt niets meer te knippen.

Na afloop spoelt de speler terug naar een punt in die stille staart, gekozen op het
frame dat het meest op het slotbeeld lijkt: 8,46 s voor Nederlands en 5,4 s voor
Engels. Die waarden staan in `INTRO` in `static/app.js`. Verandert de clip, dan
moeten ze opnieuw gezocht worden — meet de afwijking tussen het slotframe en elk
frame in de staart, en houd minstens drie seconden staart over, anders schokt de
rondgang.

## Waarom de Engelse clip uit twee stukken bestaat

Tijdens de stilte verzint het model soms een mondbeweging. In het Engels gebeurde
dat tussen 6,8 en 8,4 seconde, en dat leest als een woord dat je niet hoort —
Ruud zag haar "help" zeggen. Het is deterministisch: dezelfde audio geeft dezelfde
beweging, dus opnieuw genereren met dezelfde stilte helpt niet.

Wat wel helpt is een langere stilte, zodat er verderop een rustig stuk ontstaat.
De gebruikte clip is daarom `0 → 6,70` plus `14,80 → 16,55` uit dezelfde generatie
aan elkaar. Dat is een knip, maar geen tweede generatie: kleur, scherpte en
belichting zijn identiek. Het aansluitpunt is gekozen op het frame dat het beste
bij het eind van deel één past.

Meet de mondbeweging door per frame het verschil te nemen in het gebied
`x 0,35–0,65`, `y 0,55–0,75` van het beeld. Waarden van 1 tot 3 zijn ademen;
alles boven de 5 is de mond.

## Opnieuw maken

De audio, met ffmpeg uit `imageio_ffmpeg`. Eerst alleen de spraak, dan stilte erachter:

```bash
ffmpeg -y -i bronnen/vera/intro-nl-ongeknipt.mp4 -t 5.51 -vn -ac 1 -ar 44100 spraak.wav
ffmpeg -y -i spraak.wav -af "apad=pad_dur=6" -b:a 128k bronnen/vera/begroeting-met-stilte-nl.mp3
```

Dan de video, met avatar-id `43e6b2b0-29ea-4125-8e2f-3ebed04f65d1`:

```python
c.avatar_videos.create(
    model="gwm1_avatars",
    avatar={"type": "custom", "avatar_id": VERA},
    speech={"type": "audio", "audio": "data:audio/mpeg;base64," + base64.b64encode(mp3).decode()},
)
```

Let op: de server moet Range-verzoeken aankunnen, anders meldt de browser
`seekable = [0, 0]` en kan hij niet terugspoelen naar de staart. Dat zit in
`send_file` in `server.py`.
