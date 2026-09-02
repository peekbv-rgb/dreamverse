# De chakrapilaar: waar het beeld vandaan komt

`voorbeeld-van-ruud.png` is de tekening die Ruud als voorbeeld aandroeg. Hij staat
hier en niet in `static/`, want hij wordt niet gebruikt en zou anders 1,9 MB
meedeployen voor niets.

## Waarom hij niet gebruikt wordt

Mooier dan wat er nu staat, maar er zitten **zes** mandala's op de as en geen
zeven: wit, violet, blauw, groen, amber, rood. Oranje (sacral) en indigo
(third_eye) ontbreken, en wat ertussen hangt zijn zwevende kristallen.

Zeven gegevens op zes plekken leggen betekent dat twee chakra's dezelfde lotus
krijgen of dat er een op een kristal landt. Dan wijst de tekening iets aan dat er
niet staat, en dat merkt niemand op — precies het soort fout dat het hele ding
waardeloos maakt.

## Wat er wel gebruikt wordt

`static/chakra-pilaar.jpg`, gegenereerd met Runway `muse_image` op `1152:2016` en
daarna teruggebracht naar 576 bij 1008 (173 kB; hij wordt op 230 px getoond).

De aanwijzing die hem opleverde staat hieronder. Belangrijk is dat de zeven
lotussen apart genoemd worden mét hun aantal bloembladen — vraag je om "seven
chakras" dan komen er zes, of acht.

> A vertical column of seven glowing chakra mandalas rising through deep space,
> seen straight on. From bottom to top: a red four-petal lotus, an orange
> six-petal lotus, a golden ten-petal lotus, a green twelve-petal lotus, a blue
> sixteen-petal lotus, an indigo two-petal lotus, and at the very top a brilliant
> white-violet thousand-petal lotus blazing with light. A single brilliant white
> beam of light runs straight up through all of them. Around each mandala, wide
> flat horizontal spiral discs of light swirl outward like galaxy rings in the
> matching colour. Faint white sacred-geometry wireframes float to the left and
> right: flower of life circles, hexagonal Metatron cubes. Small faceted crystals
> and gemstones drift in the field, catching the light. Starfield and dark nebula
> behind everything, black background, symmetrical composition, centred,
> luminous, highly detailed digital art.

## De middelpunten opnieuw meten

Vervang je de plaat, dan moeten de zeven hoogtes opnieuw. Ze staan als `y` in
`VELDEN` in `static/app.js`, als fractie van de hoogte. Meten gaat zo: zet de
plaat op 384 breed, teken horizontale lijnen op je schatting, en kijk of ze door
het hart van elke lotus lopen. Zit er een lijn naast, dan vallen straks het
percentage en de dover ernaast.

Nu geldt: root 0,848 · sacral 0,700 · solar 0,570 · heart 0,455 · throat 0,345 ·
third_eye 0,235 · crown 0,112.
