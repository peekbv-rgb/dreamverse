# De bronbestanden van Vera's welkomstboodschap

Dit is het eerste wat iemand van Dreamverse ziet. Hier staan de originelen, zodat
het opnieuw te maken is zonder alles opnieuw te genereren.

## Wat er staat

| Bestand | Wat het is |
|---|---|
| `intro-nl-ongeknipt.mp4` | Vera's begroeting in het Nederlands, 5,67 s, zoals Runway hem gaf |
| `intro-en-ongeknipt.mp4` | Dezelfde in het Engels, 4,80 s, zoals Runway hem gaf |
| `laatste-frame-nl.jpg` | Het laatste beeld van de geknipte NL-clip (op 5,66 s) |
| `laatste-frame-en.jpg` | Het laatste beeld van de geknipte EN-clip (op 4,68 s) |

Wat in `static/` staat is het geknipte resultaat: `vera-intro-nl.mp4`,
`vera-intro-en.mp4`, en de stille lussen `vera-idle-nl.mp4` en `vera-idle-en.mp4`.

## Waarom er geknipt is

De Engelse clip eindigt met een knipper: vanaf 4,72 s zijn haar ogen dicht, en het
laatste beeld bleef daarop staan. Een welkomstboodschap die eindigt met een
gesloten gezicht leest als een storing. Afkappen op 4,68 s geeft ogen open en een
glimlach. De Nederlandse clip eindigt uit zichzelf goed en is alleen op 5,66 s
afgerond; de knipper daarin zit op 5,38 s, dus midden in de zin waar hij hoort.

## Waarom er twee stille lussen zijn

Na de begroeting mag ze niet stilstaan en niet opnieuw praten. De hele clip
herhalen laat haar de tekst mimen; bevriezen maakt haar levenloos. Daarom een
aparte lus per taal: ademen, knipperen, haar in de wind, mond dicht.

Die lus is gegenereerd **vanaf het laatste frame van de clip erboven** — vandaar
dat die frames hier bewaard staan. Dat is de hele truc: het eerste beeld van de
lus is letterlijk het laatste beeld van de begroeting, dus je ziet geen montage
maar een doorloop. Een lus uit een ander frame geeft een zichtbare knik, hoe goed
de generatie verder ook is.

## Opnieuw maken

Knippen (ffmpeg komt uit `imageio_ffmpeg`, staat al in de requirements):

```bash
python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"
```

Daarna, met dat pad als `ffmpeg`:

```bash
ffmpeg -y -i bronnen/vera/intro-en-ongeknipt.mp4 -t 4.68 -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -c:a aac -b:a 128k static/vera-intro-en.mp4
```

Het laatste frame eruit halen:

```bash
ffmpeg -y -sseof -0.05 -i static/vera-intro-en.mp4 -frames:v 1 -q:v 2 bronnen/vera/laatste-frame-en.jpg
```

De stille lus komt van Runway `image_to_video`, model `gen4_turbo`, 5 seconden,
`1280:720`, met dat frame als `prompt_image` en deze aanwijzing:

> She has just finished speaking and now stands still, listening. She breathes
> softly and blinks naturally a few times, keeping the same calm expression. Her
> lips stay closed and completely still: she is not speaking, her mouth does not
> move. Loose strands of hair drift in the sea breeze, waves roll gently behind
> her, warm sunset light. Static camera, no zoom, no cut.

De regel over de lippen moet erin blijven staan. Zonder die zin begint ze te
glimlachen en te praten, en dan is het weer een pratende clip.
