# Dreamverse

Je vertelt 's ochtends je droom; je krijgt een verbeelding van vijf panelen met een
duiding en een vooruitblik. Elke eerdere droom telt mee, en daar zit het hele idee
in: terugkerende plaatsen, personen en dieren maken er na een paar maanden één
wereld van. Na honderd dromen is er *Season One of Your Dreams*.

**De map heet nog `nieuwe-app`.** Hernoemen naar `dreamverse` kan zodra er geen
sessie en geen server meer in draait:

```bash
cd "/c/Users/ruud/Desktop/AI/Projects" && mv nieuwe-app dreamverse
```

Gedeelde bedrijfscontext komt uit `AI/CLAUDE.md`. Dit project heeft **niets** met
Peek, Catyra of Catabatics te maken en deelt er ook geen code mee — het is een
consumentenexperiment. Niet te verwarren met de avatars Cat en Pia.

## Waarom dit idee en niet Parallel You

Het voorstel ernaast — elke dag een verbeelding over je parallelle leven — sneuvelt
op de kosten: 45 seconden gegenereerde video maal dertig dagen is €40 tot €160 per
abonnee per maand, tegen €8,99 omzet. Dreamverse ontsnapt daaraan om vier redenen:
dromen zijn zelfbeperkend (vijf tot tien per maand), de gebreken van AI-beeld zijn
bij een droom een kenmerk in plaats van een bug, de invoer komt van de gebruiker,
en er is geen gezicht van een derde nodig.

Kostprijs per verbeelding als motion comic: ongeveer **€0,35**. Bij €8,99 en zes
dromen per maand is dat 66% marge. Het rekenmodel staat in de artefacten van de
sessie van 1 september 2026.

## Stack

Python 3.14, standaardbibliotheek `http.server`, statische frontend, Anthropic SDK.
Geen framework — dat houdt de deploy op één bestand, net als de andere projecten hier.

| Onderdeel | Waar |
|---|---|
| Verbeeldingen schrijven, archief, prompt | `dreamverse.py` |
| Panelen als illustraties (optioneel) | `kling.py` |
| Het bewegende kernmoment | `video.py` |
| Live gesprek met de avatar | `vera.py` |
| Accounts, sessies, dromen per gebruiker | `accounts.py`, `data/dreamverse.db` |
| Afrekenen | `betalen.py` |
| E-mail versturen | `mail.py` |
| Het oude archief overzetten | `migratie.py` |
| Verbruik meten | `usage.py`, `data/usage.jsonl` |
| Pakketten, tokens en grenzen | `plans.py` |
| Prijzen doorrekenen mét btw en betaalkosten | `prijzen.py` |
| Persona en kennisdocumenten | `persona/`, `knowledge/` |
| Id's van gekoppelde documenten (**niet weggooien**) | `build/document-ids.json` |
| HTTP en routes | `server.py` |
| Speler, invoer, spraak | `static/` |
| De chakrapilaar, vaste plaat | `static/chakra-pilaar.jpg` |
| Het beeld bij een gedeelde link | `static/og-beeld.jpg`, uit `build/og_beeld.py` |
| Wat er op Instagram komt | [instagram.md](instagram.md) |
| Tweede taal (Amerikaans Engels) | `static/taal.js` |
| Persona van de gids | `persona/vera.txt` |
| Vera's welkomstboodschap, bronnen | `bronnen/vera/` (met `LEESMIJ.md`) |
| Droomarchief (git-ignored) | `data/archive.json` |
| Deploy | `render.yaml` |

```
POST   /api/registreren                {"email", "wachtwoord", "naam"}
POST   /api/inloggen                    {"email", "wachtwoord"}
POST   /api/uitloggen
POST   /api/wachtwoord                  {"oud", "nieuw"}
POST   /api/episode   {"dream", "quality", "lens": "vanzelf|psychologisch|symbolisch|spiritueel"}
GET    /api/episode/<nr>                -> een eerdere verbeelding terugkijken
POST   /api/episode/<nr>/herstel        -> duiding opnieuw schrijven bij oude panelen
GET    /api/archive                     -> alle eerdere dromen + de nieuwste analyse
GET    /api/spectrum                    -> welk kleurveld elke droom koos
POST   /api/dream/<nr>/vooruitblik      -> de dromer zegt of de vooruitblik uitkwam
DELETE /api/archive                     -> archief wissen
GET    /api/panels/<nr>                 -> stand van het tekenwerk
GET    /panels/<bestand>.jpg            -> een gegenereerd paneel
POST   /api/vera/session                -> WebRTC-gegevens voor een gesprek
DELETE /api/vera/session/<id>           -> gesprek afsluiten
POST   /api/feedback                    {"tekst"} -> wat er beter kan
GET    /api/health                      -> {"ok", "key", "kling", "vera"}
```

## Draaien

```bash
pip install -r requirements.txt && python server.py
```

Dan `http://127.0.0.1:8000`. **Zonder `ANTHROPIC_API_KEY` draait alles behalve het
schrijven**: elke droom geeft dezelfde voorbeeldverbeelding terug, met `demo: true`.
Zo is de app te demonstreren zonder een cent aan tokens.

Model: `claude-opus-5` op effort `medium`. Schrijfwerk heeft geen hoge effort nodig
en het scheelt direct in de kostprijs per verbeelding.

## Regels die er al in zitten

- **De vooruitblik is vermaak, geen voorspelling.** Nooit over gezondheid, ziekte,
  geld, zwangerschap of iemands dood. Dat staat in `RULES` in `dreamverse.py` en
  hoort daar te blijven: een app die zegt "let op je hart" bezorgt mensen echte
  angst en je kunt het niet terugnemen. **En de kop erboven zegt dat ook.** Daar
  stond *Wat eraan zit te komen* — een voorspelling, drie regels boven de zin
  dat dit geen voorspelling is; de app sprak zichzelf tegen op de plek waar
  iemand haar het scherpst leest. Nu: *Waar deze droom je aandacht op kan
  vestigen* / *What this dream may be pointing toward*. De promptregel is
  meegegaan (geen "je zult", geen "er komt": iets om op te letten, niet iets om
  op te wachten), en de vraag achteraf is van *Klopte het?* naar *Heb je het
  teruggezien?* gegaan met Ja/Deels/Nee. Wat bewaard wordt blijft
  `raak/deels/mis`, dus oude oordelen blijven staan.
- **Drie grenzen, en de nummers staan in de code.** Bij een expliciet seksuele
  droom komt er geen verbeelding: `BuitenBereik` slaat toe **vóór** het
  afrekenen en vóór het opslaan, dus zo'n droom kost niets en komt niet in het
  archief. Bij geweld tussen mensen en bij zelfdoding komt de duiding er wél —
  wie dit droomt en niets terugkrijgt is er slechter aan toe — met een vast
  hulpkader erboven. **Het model classificeert alleen** (`zorg` in
  `ZORG_REGELS`); de teksten en de nummers staan in `LANDEN` in `static/app.js`,
  want een gehallucineerd crisisnummer is het ergste wat deze app kan doen.
- **Nummers per land, en geen nummer als we het land niet kennen.** `landcode()`
  raadt het land uit de regio in de taalinstelling van de browser, anders uit de
  tijdzone — zonder het te vragen en zonder een IP-adres ergens heen te sturen.
  In `LANDEN` staat alleen wat bij de bron geverifieerd is: nu nl, be, de, gb en
  us. Kennen we het land niet, dan komt er géén nummer, want een nummer uit een
  ander land is erger dan geen nummer. Er staat **altijd** een link naar Find A
  Helpline (ThroughLine, ruim 175 landen, pagina per land) — dat is beter
  onderhouden dan een lijst van ons. Een land toevoegen is één regel in `LANDEN`,
  en doe dat alleen met de bron erbij.
- **De drempel ligt hoog en dat is opzet.** Een monster dat je achtervolgt is
  geen geweld waarvoor je Veilig Thuis belt, en doodgaan in een droom is iets
  anders dan een suïcidale droom — dat zijn juist de twee meest voorkomende
  dromen die er zijn. Wie te vaak waarschuwt maakt de waarschuwing waardeloos en
  bezorgt mensen angst; dezelfde reden waarom de vooruitblik nooit over
  gezondheid gaat. Nagemeten op vier dromen, inclusief een controlegeval dat
  níet mag afgaan.
- **Altijd positief duiden, maar niet wegwuiven.** Bij geweld, verlies of een
  overledene eerst erkennen, dan pas het licht zoeken.
- **De vooruitblik beoordeelt alleen de dromer.** `POST /api/dream/<nr>/vooruitblik`
  bewaart of het uitkwam, en dat oordeel gaat **niet** terug de prompt in. Zodra
  wij zouden scoren wordt de vooruitblik een claim en houdt "vermaak, geen
  voorspelling" geen stand; en een model dat weet dat het op raak beoordeeld wordt
  gaat vaag schrijven of gokken.
- **Symbolen komen uit zijn eigen dromen, niet uit een droomwoordenboek.** "Water
  staat voor emotie" kan iedereen opzoeken en is bij deze dromer misschien niet
  eens waar. Het veld `symbols` mag alleen tekens noemen die in de meegegeven
  geschiedenis meer dan een keer voorkwamen.
- **Geen "sacred geometry" in de beeldprompt.** Die term stond in `STYLE` in
  `kling.py` en is het recept voor hexagrammen, pentagrammen en Metatrons kubus
  — dat zijn de vormen die een beeldmodel eruit haalt. Op een droom over een
  boerderij kwam een davidster in de lucht te staan. Niemand vroeg erom, en in
  een app over iemands binnenwereld is een religieus teken dat je niet bedoeld
  hebt geen sfeer maar een uitspraak. Nu staan er **concentrische ringen en
  bogen**: dezelfde zachte structuur, nooit een teken. Van de andere kant houdt
  `NEGATIVE` het tegen — alleen het woord weglaten is niet genoeg, want zodra de
  droom over iets plechtigs gaat komt zo'n figuur er alsnog uit. Nationale en
  politieke tekens staan er om dezelfde reden bij. Nagemeten met
  `python kling.py --check`: Kling accepteert `negative_prompt`, en het beeld
  kwam terug met ringen in plaats van een ster. **Panelen die er al zijn
  veranderen niet** — die zijn getekend met de oude prompt.
- **De kleurvelden zijn de chakra's** (`root` tot `crown`). Dat is geen sfeer maar
  betekenis: het model kiest per paneel het veld dat bij het gevoel past, en de
  kijker ziet die keuze terug in de kleur van het beeld.
- **Eén standbestand, drie schrijvers.** `data/panels/<nr>.json` wordt bijgehouden
  door `kling.py`, `stem.py` én `video.py`. Wie zijn hele woordenboek wegschrijft
  gooit het werk van de andere twee weg, dus schrijf altijd samenvoegend. En de
  standaardwaarde bij een ontbrekend bestand is `status: "off"`, nooit `"done"`:
  met `done` en nul panelen concludeert de pagina dat de verbeelding af is
  terwijl er nooit iets gemaakt is.
- **Panelen bijkopen liet ze niet zien.** Wie "alleen de duiding" koos en er
  later panelen bij kocht, hield `quality: "duiding"` in de bewaarde
  verbeelding. De speler leest dat veld en zet zichzelf in tekstmodus, dus de
  panelen waren getekend, betaald en op te halen — en toch onzichtbaar. Dat
  wordt nu bij het **laden** gecorrigeerd en niet bij de aankoop: zo klopt het
  ook voor dromen die al gekocht waren, zonder de bewaarde verbeeldingen aan te
  raken. Wat er op schijf staat is de waarheid.
- **Een heropende droom haalt zijn panelen altijd één keer op.** Dat gebeurde
  alleen bij `images_pending`, en die vlag is bij een afgeronde droom allang
  `false` — dus wie terugkeek zag niets. Loopt er wél tekenwerk, dan blijft de
  volledige poll draaien.
- **Afrekenen pas als het werk echt kan.** `/api/extra` controleerde alleen het
  saldo en of de achtergrondtaak *startte*; die taak faalde daarna en de tokens
  waren weg. Nu weigert hij met 409 als er geen panelen liggen om te animeren.
- **Wissen ruimt ook de bestanden op.** De nummering begint na het wissen weer bij
  1, dus als de panelen van de oude Droom 1 blijven staan, erft de nieuwe Droom 1
  ze — en dan zie je in je archief een droom met het beeld van een andere. Zowel
  `clear_archive()` als `delete_dream()` gaan langs `_ruim_nummer_op()`, en `create()`
  ruimt het nummer op dat hij gaat gebruiken. Wat niet met een cijfer begint,
  zoals `check.png`, blijft staan.
- **`python build/controle.py` controleert ook de CSS-variabelen.** `var(--foo)`
  met een tikfout maakt de hele regel ongeldig; de browser slaat hem stil over en
  je ziet alleen dat er iets niet kleurt. Zo stond `--third_eye` met een lage
  streep op twee plekken, en werd `--water` nergens gezet — waardoor Vera's
  portret nooit oplichtte als ze luisterde. Zelfde soort fout als een stuurteken,
  dus zelfde controle.
- **Stuurtekens in de broncode: `python build/controle.py`.** Er stond een
  letterlijk backspace-teken (0x08) middenin `/[?&]beheer/` in `static/app.js`,
  waar een woordgrens bedoeld was. Die test matchte daardoor nooit, het
  beheerpaneel ging nooit open, en er was geen spoor: geen fout in de console,
  geen melding, geen venster. In een editor is het onzichtbaar. Dit is drie keer
  gebeurd doordat een script broncode wegschreef en een reeks onderweg als
  escape werd uitgelegd. Bij een klacht van het type "die knop doet niets en ik
  zie niks" is die scan de eerste stap.
- **Een klik op de taalvlag is geen "begin maar te praten"-aanraking.**
  Blokkeert Chrome het geluid, dan zet de app een wachter op de eerste
  aanraking. Een klik op EN/NL was daarmee twee dingen tegelijk: de wachter
  startte Vera in de oude taal, de vlag in de nieuwe — twee begroetingen op één
  speler, en de afgebroken `play()` zette de ander halverwege op stil omdat die
  catch alsnog draaide. Daarom worden `.vlag` en `.geluid-aan` doorgelaten in
  `wachtOpAanraking`, en weet elke poging aan zijn `begroetingRonde` of hij nog
  de actuele is.
- **Beheer vraagt zijn sleutel op een eigen pagina.** Het was eerst een
  `window.prompt` (die onderdrukt Chrome zodra het tabblad de focus kwijt is),
  daarna een kaart bovenop de app, en nu `/beheer`. Zie de sectie *Beheer staat
  op /beheer, buiten de app*. Wat van de eerste twee stappen overblijft is de
  les eronder: zeg apart of de sleutel is afgekeurd of `ADMIN_TOKEN` helemaal
  niet in de omgeving staat, want dat verschil scheelt een half uur zoeken naar
  een sleutel die nergens geldig is.
- **Opwaarderen moet één klik zijn vanaf het getal dat je aankijkt.** De
  koopknoppen stonden bijna vierduizend pixels onder de invoer; wie ziet dat hij
  nul tokens heeft staat bovenaan en gaat niet zoeken. Dan bestaat opwaarderen
  niet, ook al is het gebouwd. Vandaar `opwaarderen` in de tegoedbalk, *Tokens
  kopen* in de accountkaart, en dezelfde weg vanuit de weigering bij Vera.
- **Van een gesprek wordt nooit automatisch een verbeelding gemaakt.** De tekst
  gaat in de invoer en daar stopt het: verbeelden kost geld en soms tokens, en
  een verbeelding van een tekst die de dromer nog niet gezien heeft is een
  verbeelding die hij niet gevraagd heeft. Hij leest na, hij kiest de kwaliteit,
  hij klikt. Daarna loopt de gewone molen: duiding, panelen, chakraveld, en mee
  in de duiding van alle dromen samen.
- **Een ingesproken droom overleeft een verse pagina.** De tekst uit een gesprek
  bestaat alleen in dat ene tekstvak; een verdwaalde verversing kost dan een
  droom die net verteld is, terwijl de minuten met Vera al zijn afgerekend.
  Daarom gaat hij ook in `localStorage` (`dreamverse_gesprek`), met een grens van
  een uur — daarna is het geen "net ingesproken" meer en zou hij een oude tekst
  in een nieuwe sessie duwen.
- **`service-not-allowed` op een iPhone is geen storing.** Safari geeft die code
  als de spraakdienst niet mag: in een privévenster, of met Dicteren uit onder
  Instellingen → Algemeen → Toetsenbord. De ruwe code stond op het scherm
  ("Meeschrijven stopte: service-not-allowed"), en dat is jargon waar een
  dromer niets mee kan terwijl er een oplossing van één tik achter zit. Eén
  functie `spraakfout()` vertaalt de vijf codes die echt voorkomen, en bedient
  zowel het meeschrijven bij Vera als de knop Inspreken. Onbekende codes vallen
  terug op de ruwe melding — liever een code dan niets.
- **De Web Speech API is op een telefoon niet te vertrouwen.** Vera hoort de
  dromer wel (dat is LiveKit met een eigen microfoonstroom), maar de tekst komt
  van de browser. Wordt dit een telefoonproduct — en dat is het, want je vertelt
  je droom 's ochtends in bed — dan hoort het transcriberen naar de server te
  verhuizen in plaats van aan Safari te hangen.
- **Spraakherkenning volgt de taal uit het profiel.** `recogniser.lang` stond
  hard op `nl-NL`, dus een Engelse gebruiker sprak in en kreeg Nederlandse
  brij terug. Eén functie `taalcode()` bedient nu het inspreken én het
  meeschrijven.
- **Drie brillen naast de chakra's: psychologisch, symbolisch, spiritueel.**
  Een chakraveld is een gevoel dat het model per paneel kiest en dat je achteraf
  ziet; een bril is een manier van kijken die de dromer vooraf kiest. Dezelfde
  droom over een dichte deur geeft bij psychologisch iets over wat je van jezelf
  afhoudt, bij symbolisch over wat een deur in jóuw dromen betekent, bij
  spiritueel over waar je voor staat. **`vanzelf` is de standaard**: dan kiest
  het model en zegt in het veld `lens` welke het werd — zo krijgt ook iemand die
  er niet over wil nadenken de classificatie. Alles zit in `LENZEN` en
  `LENS_UITLEG` in `dreamverse.py`; de verbeelding wordt als woordenboek bewaard,
  dus er was geen migratie nodig.
- **Een sleutel is de héle `innerHTML` van het element, niet de tekst erbinnen.**
  De voetnootregel met drie links kreeg drie losse vertalingen — *Over
  Dreamverse*, *Pakketten en prijzen*, *Privacyverklaring* — en die pasten
  nergens op, want `<a>` staat niet in `TE_VERTALEN`; vertaald wordt de `<p>`
  eromheen, met de opmaak erin. Eén sleutel met de hele regel HTML dus, in
  enkele aanhalingstekens.
- **`python build/controle.py` kijkt ook of elke `t("...")` uit `app.js` een
  regel in `taal.js` heeft.** Zo'n zin valt anders terug op het Nederlands en
  blijft staan zodra iemand op English drukt — zonder fout, zonder melding.
  Wat in `index.html` staat vangt die controle níet: daar bepalen CSS-selectors
  wie meedoet en dat vraagt een echte browser. Die kant meet je door in de app
  op English te drukken en te kijken welke elementen hun `data-nl` houden.
- **Sleutels in `taal.js` met HTML erin moeten enkele aanhalingstekens hebben.**
  De vertaalslag vervangt `innerHTML`, dus een zin met een link erin heeft die
  link in de sleutel staan. Zet je daar dubbele aanhalingstekens omheen, dan
  breekt het bestand — en omdat `t()` daaruit komt, staat daarna de héle app
  stil: geen kwaliteitsknoppen, geen brillen, geen pakket. Eén zin in een
  woordenlijst legt dan alles plat, en de pagina zelf laadt gewoon door.
- **Groen betekent "zit in je pakket", violet betekent "dit heb ik gekozen".**
  Ze waren allebei groen, en dan zegt een kleur twee dingen tegelijk: bij Ultra
  stond Supreme groen omdat het inbegrepen is en Standaard groen omdat hij
  aanstond. Violet is dezelfde kleur als de gekozen bril eronder, dus een keuze
  ziet er overal hetzelfde uit. Het vlaggetje blijft groen, ook als die knop
  tegelijk de gekozene is — die twee dingen zijn allebei waar.
- **Panelen zijn los bij te maken, voor 1 token.** Koos iemand "alleen de
  duiding" en wil hij er toch beeld bij, dan tekent `/api/extra` met
  `kind: "panelen"` de vijf panelen alsnog bij de duiding die er al staat. Het
  antwoord was eerst "maak de droom opnieuw" — en dat kost een droom uit het
  maandtegoed én levert een ándere verbeelding op, want het model schrijft dan
  opnieuw. De prijs is het verschil tussen *duiding* en *eenvoudig*.
- **Een draad noemt de datum, niet "toen".** `datumVan()` zoekt het nummer uit
  `ref` ("Droom 12") op in het archief en toont de dag waarop die droom er was.
  Zonder bekende datum valt hij terug op "Toen:", want een lege regel is erger
  dan een vaag woord.
- **Eén vraag per droom is inbegrepen, daarna een token.** `POST /api/vraag`
  laat de dromer iets vragen over zijn eigen droom; het model krijgt de droom, de
  duiding die er al staat, zijn eerdere dromen en de eerder gestelde vragen mee.
  Gratis maken nodigt uit tot een gesprek, en dan bouw je ongemerkt een chatbot
  na met de marge van een droom-app. Dezelfde grenzen als de duiding staan in
  `VRAAG_REGELS`, inclusief de zorgclassificatie — nagemeten: "betekent dit dat
  ik ziek word" krijgt "daar ga ik niet over". **Dit is een proef**: elk gebruik
  wordt apart geteld in `usage` zodat te zien is of er belangstelling voor is.
- **Nooit `.env` committen.** `.gitignore` blokkeert ook `.env.*` en `data/`.
- Basic auth gaat aan zodra `AUTH_USER` én `AUTH_PASSWORD` gevuld zijn. **Twee
  paden staan er altijd buiten**: `/api/stripe/webhook`, want Stripe stuurt geen
  wachtwoord mee en dan slaat er stil nooit een pakket om terwijl de klant wél
  betaald heeft; en `/privacy.html`, want een privacyverklaring achter een
  wachtwoord beschermt niemand. Sinds er accounts zijn heb je basic auth
  overigens niet meer nodig: zonder inloggen komt niemand bij `/api` of
  `/panels`.

- **Eén keer vragen wat er beter kan, en dan niet meer.** De app meet met opzet
  geen klikgedrag, dus `rapport.py` ziet wél dat iemand wegblijft en nooit
  waarom. `POST /api/feedback` is het enige kanaal dat dat gat vult. Het kaartje
  komt **na** de eerste verbeelding — wie net binnen is heeft geen mening — en
  verdwijnt zodra er iets is ingestuurd, want nog eens vragen leest als "we
  hebben het niet gelezen". Wegklikken onthoudt de browser
  (`dreamverse_feedback_weg`); of er al iets ingestuurd is weet de server
  (`feedback_gegeven` in het profiel). Er kan van alles in zo'n veld staan, tot
  stukken droom aan toe, dus het valt onder dezelfde regels als de rest: mee in
  de zip, weg bij het verwijderen van het account, en genoemd in
  `privacy.html`. Alles komt onderaan `python rapport.py` te staan.

- **"Je dromen samen" is een beschouwing, geen samenvatting.** Het veld
  `together` was twee tot vier zinnen; nu zijn het drie tot vijf alinea's die
  vier dingen langslopen: wat er door alle nachten heen loopt, wat er verschoven
  is en waar je dat aan ziet, wat de dromen bij elkaar over hem zeggen, en waar
  hij op kan letten. Dit is het stuk waarvoor iemand terugkomt, dus het mag
  langer zijn dan de duiding van een enkele droom. Onder de drie dromen blijft
  het bij een paar zinnen en bij een of twee dromen leeg — doen alsof er al een
  patroon is, is niet eerlijk. Het blijft **één tekstveld**, geen nieuwe velden:
  zo hoefden oude verbeeldingen niet gemigreerd te worden. De app splitst op
  lege regels en maakt er `<p>`'s van, en daarom is `#samen` een `div` geworden
  — een `<p>` mag geen `<p>` bevatten.

## De DreamCard

De knop **Deel deze droom** bij de speler maakt een verticale kaart van
1080 bij 1920 in de browser en geeft hem aan het deelmenu van het toestel. Daar
staat Instagram in, en dat is de enige weg die er echt uitkomt: **posten vanaf
een website kan bij Instagram niet.**

Op de kaart staat het beeld, "Vannacht droomde ik…" en onderaan het merk.
**Geen duiding, geen droomtekst, geen titel** — dat is het intieme deel, en wie
op delen drukt om een mooi plaatje te sturen hoort niet per ongeluk zijn nacht
op straat te leggen. Een link naar het paneel zou trouwens ook niet werken: die
route controleert of het jouw gebruikersnummer is, dus bij een ander is hij dood.
Publieke deellinks zijn een heel ander en veel groter besluit.

**Beweegt het paneel, dan komt er een beeldje uit de animatie op de kaart** en
niet het stilstaande paneel. De video staat al te spelen in de speler, dus die is
rechtstreeks op het doek te tekenen — geen extra download en geen opname. Het
paneel is het startbeeld waar de animatie mee begon; halverwege staat er meestal
meer te gebeuren. Een video van tien seconden delen is te lang voor een verhaal;
een still eruit is beter. `readyState >= 2` wordt gecontroleerd, anders krijg je
een zwart vlak.

De knop verschijnt alleen als er iets te delen valt en niet bij het voorbeeld,
en volgt het paneel dat je op dat moment bekijkt. Zonder deelmenu —
op een laptop is dat de regel — wordt de kaart opgeslagen als afbeelding, met de
mededeling dat delen vanaf een telefoon makkelijker gaat.

Twee dingen die goed moeten. `document.fonts.ready` wordt afgewacht, anders
tekent het doek in Times New Roman en ziet de kaart er niet uit als de app. En
`AbortError` is geen fout: dat is iemand die het deelmenu wegklikt.

**Boven en onder blijft 285 pixels leeg, en dat is een gemeten maat.** In een
verhaal legt Instagram zijn eigen bediening over het beeld: bovenaan het profiel
met het kruisje, onderaan het antwoordveld — Instagram vraagt zelf om 250 pixels
rust aan beide kanten. En zet iemand de kaart in zijn feed in plaats van in een
verhaal, dan snijdt Instagram hem naar 4:5, de hoogste verhouding die de feed
aanneemt, en dat is precies de middelste 1350 pixels: 285 eraf aan beide kanten.
De strengste van die twee is 285. Daar viel het merk **buiten**: dat stond op
1770 en het adres op 1828, dus in een verhaal lag de antwoordbalk eroverheen en
in de feed werd het weggesneden — precies de twee regels waarvoor de kaart
bestaat, want de kaart is de advertentie. Nu staat de kop op 400, het paneel van
470 tot 1450, het merk op 1548 en het adres op 1610. Nagemeten met
`measureText`: de kop begint op 327 (en dat is met Georgia, de terugvalletter,
die een hogere stok heeft dan Cormorant) en het adres eindigt op 1610.
**Verander je een van die vijf getallen, meet dan opnieuw** — een letter met
andere maten schuift de bovenkant van de kop mee.

Op de kaart staat **VERA DREAMVERSE** en niet DREAMVERSE. Dat is de regel uit
*Domeinen*: naar buiten heet het Vera Dreamverse, binnen de app blijft het
Dreamverse. Deze kaart is het meest naar buiten wat de app maakt, en het adres
eronder zegt hetzelfde.

- **Vera's introductie komt één keer, niet elke keer.** `el("intro").hidden`
  stond onvoorwaardelijk op `false`, dus Vera stelde zich opnieuw voor aan iemand
  die zijn negende droom kwam vertellen. Een begroeting die je elke ochtend
  wegklikt is een drempel. Wegklikken onthoudt de browser
  (`dreamverse_intro_gezien`). **En er is een weg terug**, want dat venster is de
  enige plek waar naam, geboortedatum en geslacht staan — en die geboortedatum
  bepaalt de leeftijdscontrole bij een aankoop. Bij *Je gegevens* staat
  *Introductie opnieuw*.
- **Een sleutel in `taal.js` mag geen HTML-entiteit bevatten.** De browser
  decodeert `&middot;` bij het inlezen, dus `innerHTML` geeft het teken terug en
  niet de entiteit — en dan matcht de sleutel nooit. Zo bleef de hele
  voetnootregel van de app onvertaald terwijl de sleutel er wél stond.
  `python build/controle.py` let er nu op. Zet in de HTML dus gewoon `·` en niet
  `&middot;`.

## Van Instagram naar de app

Het Instagram-account *Veradreamverse* is het enige kanaal dat er is, en de weg
loopt via één link in de bio. Vier dingen stonden die weg in de weg; ze zijn
allemaal gemeten, en het zijn allemaal fouten van de soort die zich niet melden.

**Een gedeelde link had geen beeld.** `welkom.html` had geen enkele `og:`-tag,
dus het adres in een bio-link, een DM, een WhatsApp-bericht of een
Slack-kanaal was een grijze regel tekst — terwijl beeld het sterkste is wat dit
product heeft. Nu staat er een blok in `welkom.html` en in `index.html`, en
`static/og-beeld.jpg` (1200 × 630, de maat die Facebook, Instagram, WhatsApp en
LinkedIn allemaal aanhouden) komt uit `python build/og_beeld.py`. Dat is de
vuurvogel met de tekst op een **eigen donkere grond**, want een voorvertoning
wordt ook als duimnagel van 200 pixels getoond en dan geldt dezelfde regel als
in de app. De tags zijn **vast Engels**: een crawler haalt de pagina één keer op
en voert geen JavaScript uit, dus ze kunnen niet meebewegen met de taalknop.
En `/og-beeld.jpg` staat in `ZONDER_BASIC`, want de crawler die dat beeld
ophaalt stuurt geen wachtwoord mee — dan is de pagina leesbaar en blijft alleen
de voorvertoning leeg, de kant die het minst opvalt en het meest kost.

Ook de gidspagina's hadden alleen een beeld als het onderwerp er zelf een had,
en dat heeft er nog geen enkele. `_ogbeeld()` in `droomgids.py` valt nu terug op
hetzelfde vaste beeld. Komt het beeld per onderwerp er, dan wint dat vanzelf.

**Er was niet te zien of er iemand van Instagram kwam.** Instagram stuurt geen
referrer mee, dus zonder maatregel blijft het bij "er kwam iemand". Twee wegen
nu, in `accounts.herkomst()`:

- `?van=ig` achter de link. Alleen woorden uit de vaste lijst `HERKOMST` worden
  geteld — `weergaven` heeft (datum, pagina) als sleutel, dus een vrij veld laat
  iemand die tabel met duizenden regels per dag vullen.
- **De browsernaam.** Instagram opent een link in zijn eigen browser en zet
  zichzelf in de `User-Agent`; dat wordt `ig-app` en werkt ook als de link niet
  getagd is. Dit is de betrouwbaarste van de twee.

Wat er bewaard wordt is één woord bij een dagteller, **naast** de gewone
telling en niet in plaats daarvan — anders is het aantal bezoeken aan de
landingspagina niet meer met zichzelf te vergelijken. Geen IP-adres, geen
cookie: de browsernaam wordt gelezen en weggegooid, net als bij de zeef op
robots. Dus nog steeds geen banner en niets in de privacyverklaring.

In `rapport.py` staat het onder *WAAR ZE VANDAAN KWAMEN*. Daar zat en passant
een fout: de trechter deed "landing, of anders app", en daarmee kwamen de
gidspagina's (die als `gids` en `gids:<slug>` geteld worden) in de kolom van de
app terecht. Op 9 september waren dat 36 app-weergaven waarvan er 2 van een
publieke pagina kwamen. De gids heeft nu zijn eigen kolom, want het is een
ingang en hoort in de trechter.

**In de browser van Instagram werkt inspreken niet, en de app zei het
verkeerde.** Instagram opent een link niet in Safari of Chrome maar in een
browser in de app zelf, en op een iPhone bestaat `webkitSpeechRecognition`
daarbuiten niet. De app zei "Inspreken kan alleen in Chrome en Edge" — tegen
iemand die Chrome misschien op zijn telefoon heeft staan, terwijl er een
oplossing van twee tikken achter zit. `instagramBrowser()` kijkt naar de
browsernaam, en dat verandert vier dingen: de hint bij *Inspreken* op het
eerste scherm (dat is het scherm waar iedereen van de bio-link op landt), die
in de app zelf, de titel op de knop, en drie foutcodes in `spraakfout()`
(`not-allowed`, `service-not-allowed`, `network`) — want op Android bestaat
`SpeechRecognition` in die browser wél en komt het probleem er als code uit in
plaats van als ontbrekende functie. Bij de knop van Vera staat er een regel
**vóór** de klik: een gesprek wordt ná afloop op werkelijk gesproken tijd
afgerekend, dus wie daar begint en niet gehoord wordt heeft betaald voor een
minuut waarin hij tegen niets praatte.

Alleen Instagram, met opzet. De browser van Facebook (`FBAN`, `FBAV`, `FB_IAB`)
doet precies hetzelfde en is één regexp erbij, maar zolang de bio-link het
enige kanaal is hoort er niet meer te staan dan we gemeten hebben.

Nagemeten op een tijdelijke kopie van de app die zich als de Instagram-browser
voordeed: de hint wordt vervangen, de knop gaat op grijs, de regel bij Vera
verschijnt, en een klik op EN/NL houdt alle drie overeind — die laatste is niet
vanzelfsprekend, want de vertaalslag legt de begintekst van elk element vast in
`data-nl` en herstelt daaruit. Daarom zet `hintVervangen()` `data-nl` mee, en
staat daar de **Nederlandse** zin en niet de vertaalde: dat veld is de bron.

**De poort is doorgelopen als het scherm dat het is: de landingspagina van
Instagram.** De retentie-prompt uit [instagram.md](instagram.md) is niet op een
caption gelegd maar op het echte scherm, en dat leverde vier dingen op.

- **"Tonight is one dream" ging over de verkeerde nacht.** *Vannacht* kijkt in
  het Nederlands terug én vooruit; het Engels moet kiezen, en koos vooruit.
  Iemand die om zeven uur 's ochtends met een droom van vannacht binnenkomt las
  dus een regel over vanavond — twee regels boven *What did you dream last
  night?*, en op de DreamCard staat *Last night I dreamed…* voor dezelfde bron.
- **En die regel zei niet wat je terugkrijgt.** Dat staat in `.poort-sub`, en
  `poortStap()` verbergt die op de eerste stap — met goede reden, twee koppen
  boven elkaar is erger. Maar dan is de belofte het enige wat iemand leest vóór
  hij gaat typen, en die ging alleen over de derde nacht. Nu: **Eén nacht is
  vijf panelen en een duiding. Na drie nachten begint jouw Dreamverse.** Vijf
  panelen is telbaar, "je Dreamverse" niet, en op een gratis eerste droom is het
  waar (`GRATIS_MET_BEELD = 1`). **Dit is de enige van de vier die ook in het
  Nederlands veranderd is**, want hier ging het niet om een vertaling maar om
  wat de regel zegt.
- **"You get an imagining" stond op de zin die een account waard moet zijn.**
  *Verbeelding* is in het Nederlands het woord van het product en werkt; *an
  imagining* bestaat in het Engels zo niet en moet uitgelegd worden. `welkom.html`
  zei het al beter, en die formulering staat er nu: *Tell it, and get it back as
  five panels, a reading and a look ahead.* Ook *to see it imagined* op de
  aanmeldknop is nu *to see the five panels*.
- **"And goes nowhere" was te lezen als "het leidt tot niets"** — precies op de
  plek waar iemand een droom gaat intypen die hij aan niemand vertelt. Nu: *Your
  dream stays in this browser until you make an account. It is not sent
  anywhere.* En het blijft **in this browser** en niet *on this device*: het is
  `localStorage`, dus in Safari opslaan en in Chrome terugkomen werkt niet.

Nagemeten in beide talen op beide stappen. **Let op bij het meten met de
console:** een `var t = …` in een losse consoleregel overschrijft `window.t`,
en dan valt élke `t()` in `app.js` stil — inclusief de knoptekst in
`zetPoortModus()`, die daarna op *Inloggen* blijft staan boven een
aanmeldformulier. Dat lijkt precies op een echte fout en is het niet. Zet zulke
regels dus in een `(function(){ … })()`.

**Wat de controle hier niet ziet.** `build/controle.py` zoekt naar een `t` met
de hele zin er letterlijk in. Een zin die eerst uit stukken wordt samengesteld
of via een variabele binnenkomt — zoals wat `geenSpraakUitleg()` en
`spraakfout()` teruggeven — valt daarbuiten. Die zinnen zijn met de hand
nageteld tegen `taal.js`. Schrijf een nieuwe melding dus liever als één
complete aanroep per taalvariant, zoals bij het meeschrijven, dan als één
aanroep om een keuze heen.

## De chakrapilaar

Hij staat op de pagina tussen *Je dromen samen* en *Je droomarchief*, en
verschijnt **vanaf de eerste droom**. Daar stond eerst een drempel van drie, met
het argument dat minder alleen ruis geeft. Dat klopte voor de tijdlijn maar niet
voor de pilaar: één droom is al vijf panelen met vijf gekozen velden, en dat is
een echte verdeling. Onder de drie nachten staat er een regel bij dat het nog
vroeg is.

**Maar hij staat dicht.** Zeven lotussen midden in de pagina zeggen tegen iemand
die hier voor een duiding komt dat dit een spiritueel product is, en dat is een
keuze die de dromer hoort te maken en niet wij. Tegelijk gold het oude bezwaar
nog steeds — wie hem niet ziet weet niet dat hij bestaat, en dit is een deel
waar mensen voor terugkomen. Dus: **de kop blijft staan met een knop ernaast, de
inhoud niet.** Wie hem eenmaal opent houdt hem open; dat onthoudt de browser in
`dreamverse_spectrum_open`. Niet in het profiel — het is geen eigenschap van de
dromer maar van hoe hij vanochtend kijkt, en een serververzoek voor het
open- en dichtklappen van een paneel is te veel.

Let op bij het opschrift van die knop: `taal.js` onthoudt de `data-nl` van elke
`<button>` bij de eerste vertaalslag, en dat is hier *Bekijken*. Zet JavaScript
er daarna *Verbergen* neer, dan draait een taalwissel dat terug en klopt het
opschrift niet meer met wat er open staat. Daarom roept `zetVlaggen()`
`spectrumUitklap()` opnieuw aan.

**Wat hier nog niet af is:** de namen. Het veld heet nu `root` tot `crown`, en
in de legenda staan de chakranamen. Ruud wil neutrale kleurveldnamen als
standaard, met de Sanskrietnamen als iets waar je zelf voor kiest. Dat is een
tekstwijziging in `VELDEN` in `static/app.js` plus een schakelaar, en het raakt
`PALETTES` in `dreamverse.py` niet — die sleutels blijven zoals ze zijn, anders
moet elke bewaarde verbeelding mee.


`static/chakra-pilaar.jpg` is een gegenereerde plaat: zeven lotussen in een
sterrenveld met de lichtbundel erdoorheen. Zelf zeven lotussen tekenen in SVG
kwam niet in de buurt, dus is de plaat vast en gaan de gegevens er als laagje
overheen: velden die weinig voorkwamen doven weg, velden die overheersten
blijven fel en krijgen hun percentage.

De zeven middelpunten zijn een keer uitgemeten en staan als `y` in `VELDEN` in
`static/app.js`, als fractie van de hoogte. **Vervang je de plaat, meet ze dan
opnieuw** — anders vallen de cijfers en de dovers naast de lotussen.

## Voorbeelden van een kernmoment

`static/voorbeelden/` bevat drie echte animaties uit het archief, met de
vuurvogel voorop, plus een posterplaatje per stuk. Ze staan op de landingspagina
en in de app bij *Los te koop* — want het verschil tussen "vijf tekeningen" en
"vijf tekeningen plus een bewegend kernmoment" kun je niet uitleggen, dat moet je
laten zien.

**De clips laden pas bij een klik.** Samen zijn ze 8,3 MB, en vooraf laden kost
een halve minuut op een telefoon voor iets wat de meeste bezoekers niet
aanklikken. De pagina toont dus posters van samen 154 kB, en
`static/voorbeelden.js` maakt het `<video>`-element pas aan zodra iemand erop
drukt.

Hier stond dat er geen ffmpeg is om ze te verkleinen, en **dat klopte niet**:
`imageio_ffmpeg` heeft een eigen ffmpeg 7.1 aan boord, ook al staat er niets in
PATH (zie *Van de gids naar een Reel*). Verkleinen kan dus alsnog — het laden bij
een klik blijft daarnaast gewoon goed, want ook een kleinere clip hoeft niemand
te downloaden die er niet op drukt.

Ze staan in `static/` en niet in `data/`: dat laatste is git-ignored en verdwijnt
bij elke deploy. Opnieuw klaarzetten na een nieuwe animatie:
`python build/voorbeelden.py`.

## Vera's Dream Guide

De publieke kennislaag op `/dream-meaning/`. Google levert de eerste droom,
Dreamverse zorgt dat iemand zijn volgende ook wil bewaren — dat is de hele
redenering. Wie zoekt op *dream about snakes* krijgt een algemene betekenis, en
onderaan de vraag die die betekenis persoonlijk maakt: wat deed die slang, en hoe
voelde jij je.

**De artikelen zijn gegevens, geen HTML.** Eén JSON per onderwerp in
`knowledge/droomgids/`, één sjabloon in `droomgids.py`. Onderwerp eenentwintig is
daarmee een bestandje van tien regels in plaats van een pagina overtikken, en een
wijziging in de vormgeving raakt ze allemaal tegelijk. De vaste vorm: Vera's
citaat, een inleiding, drie brillen (psychologisch, symbolisch, spiritueel) —
dezelfde drie als in de app — dan *The details change everything* met de vragen
die de betekenis kantelen, de knop naar de app, en pas daarná de FAQ.

**Tweetalig, met Engels als hoofdweg.** `/dream-meaning/snakes` is Engels,
`/nl/dream-meaning/snakes` Nederlands — twee adressen en geen schakelaar, want
Google moet ze los kunnen indexeren, en `hreflang` vertelt hem dat het
vertalingen zijn en geen dubbele tekst. Het Nederlands staat in een `nl`-blok in
dezelfde JSON; ontbreekt het, dan valt een veld terug op het Engels en verschijnt
het onderwerp niet in de Nederlandse lijst. **Elk nieuw onderwerp is daarmee twee
teksten**, en dat is de prijs van die knop: de Engelse zoekvraag is vele malen
groter, maar Ruud wilde de keuze.

Chrome vertaalt zo'n pagina anders zelf, en dan loopt een machinevertaling
buiten het zoekvak. Vandaar `translate="no"` en `class="notranslate"`, net als op
`welkom.html`.

**Dezelfde grenzen als de duiding.** Wat er staat zijn associaties uit tradities
en uit de psychologie, geen feiten en geen diagnose. Nooit over gezondheid,
ziekte, geld of iemands dood, en nooit als voorspelling. Onderaan elke pagina
staat dat ook met zoveel woorden. Een pagina die zegt dat dromen over tanden
betekent dat er iemand ziek wordt, bezorgt mensen echte angst.

Wat Google eruit leest: `<title>`, een beschrijving, een canoniek adres,
`og:`-velden, en JSON-LD met **Article** plus **FAQPage** — dat laatste is wat
Google uitklapt in de zoekresultaten, en de reden dat de FAQ ónder het artikel
hoort en niet andersom. `/sitemap.xml` en `/robots.txt` komen uit dezelfde
module, dus een nieuw onderwerp staat er vanzelf in.

**Categorieën** (`"category"` in de JSON: people, animals, events, places,
emotions) verschijnen pas als kop vanaf acht onderwerpen. Daaronder voegen
koppen niets toe en staat alles op één hoop.

**Ook in de app, onder *Je dromen samen*:** een zoekveld waarin je een woord uit
je droom intikt en doorklikt naar de gids. De onderwerpen komen van `/api/gids`
en niet uit een lijst in de frontend — anders staat dezelfde lijst op twee
plekken. Dat zoekveld staat bewust in een `<div>` en niet in een `<p>`: `taal.js`
vervangt de `innerHTML` van elke `<p>`, en dan wordt het invoerveld bij een
taalwissel opnieuw opgebouwd en is de listener weg.

De lijst met woorden eronder staat op een **eigen donkere grond**. Zie
*Leesbaar boven een bewegende achtergrond* hieronder.

**"Terug naar Dreamverse" wijst naar `welkom.html` en niet naar `/`.** De gids
hoort bij de publieke laag, en die begint bij de landingspagina. Voor iemand van
Google verandert er niets; wie ingelogd is werd door `/` de app in geduwd, met
Vera's introductie erbij, en dat is geen "terug".

Zoeken op de overzichtspagina filtert wat er al staat (`static/gids.js`), zonder
verzoek naar de server. Bij tientallen onderwerpen is dat sneller dan wat dan
ook; worden het er vijfhonderd, dan hoort het zoeken naar de server te
verhuizen.

**Elk onderwerp heeft een beeld**, uit `python build/gids_beelden.py --ja`.
Het veld `"image"` in de JSON wordt op drie plekken gebruikt: als kaartbeeld op
het overzicht, als hero boven het artikel, en als `og:image` bij een gedeelde
link (waar het het vaste beeld verslaat). Vier Kling-eenheden per stuk, dus
zevenentwintig onderwerpen is 108 eenheden.

Drie regels zitten er bewust in dat script:

- **Dezelfde stijl als de panelen.** `kling.STYLE` en `kling.NEGATIVE` worden
  niet overgeschreven. Wie op een gidspagina landt en daarna de app opent, hoort
  dezelfde hand te zien.
- **Geen gezichten.** Deze beelden staan op een openbare pagina en gaan mee als
  voorvertoning bij elke gedeelde link. Een herkenbaar gezicht bij *dromen over
  je ex* suggereert een persoon, en dat is precies wat een droom niet is. Dus
  silhouetten, van veraf, of geen figuur.
- **Niet letterlijk, en niet eng.** Bij tanden geen mond en geen bloed maar
  parels die door donker water zakken; bij spinnen geen spin maar een web vol
  dauw. Wie 's ochtends zoekt op *dromen over spinnen* is er meestal van
  geschrokken, en dan helpt een harige close-up niemand.

Bij een onderwerp dat over een mens gaat vallen die twee regels samen, en dat
is bij *stranger* het duidelijkst: in het artikel is de onbekende de bode — de
figuur die van buiten komt en iets brengt in plaats van weghaalt — en een
gestalte in een lichte deuropening is per constructie gezichtsloos, want het
tegenlicht doet het werk. De open hand is dat brengen; het ochtendlicht houdt
het van een indringer af. Zelfde truc bij *mother* (een stoel, een warme kop,
een jas over de rugleuning) en bij *being-naked* (een lege stoel in een zaal):
het onderwerp is een mens, het beeld is de plek die hij net verliet.

En ze worden **verkleind naar JPEG van 1200 breed** voordat ze in `static/gids/`
belanden. Kling levert PNG's van rond de 1,7 MB; zevenentwintig daarvan is 45 MB
op een pagina die iemand vanaf zijn telefoon opent. Nu is de hele set 3,0 MB bij
gemiddeld 110 kB per stuk, en de kaarten laden bovendien `lazy` — dus wie het
overzicht opent haalt alleen wat er in beeld staat.

**De achttien die nog te gaan waren zijn er, op 10 september 2026: de gids staat
op zevenentwintig onderwerpen en ze hebben allemaal een beeld.** Elk nieuw
onderwerp heeft nog steeds een prompt nodig in `PROMPTS` in
`build/gids_beelden.py`; zonder prompt weigert dat script te draaien in plaats
van het onderwerp stil over te slaan. Het Kling-tegoed verloopt
**18 september 2026** en rolt niet door.

**Drie onderwerpen raken de grens uit de regels, en die grens gaat over de
claim en niet over het onderwerp.** *pregnancy*, *dying* en *deceased-person*
staan er, terwijl er hierboven staat: nooit over gezondheid, ziekte, geld of
iemands dood. Dat blijft gelden voor wat een pagina *beweert* — en juist bij
deze drie is het onderwerp zelf wat mensen 's ochtends intikken, dus wegblijven
betekent dat ze het antwoord ergens anders halen. Ze doen het daarom omgekeerd:
de ontkenning staat in de **eerste zin**, niet in de kleine lettertjes. Dromen
over zwanger zijn is *"not a sign that you are, and not a sign that you will
be"*; dromen over doodgaan *"carries no information about anybody's health,
safety or lifespan"*. Wie een van deze drie herschrijft: die eerste zin is niet
de inleiding, die is de reden dat de pagina mag bestaan.

## Van de gids naar een Reel

`python build/reels.py --ja` maakt van elk gidsonderwerp een staande video met de
tekst erbij: `data/reels/<slug>.mp4` (1080 × 1920, acht seconden, ~1 MB) plus
`<slug>.txt` met de caption. Zevenentwintig onderwerpen is bijna vier weken
dagelijks posten zonder dat er nog iets bedacht hoeft te worden. `--tekst`
schrijft alleen de captions opnieuw — die zijn los van de video, en 27 keer acht
seconden coderen om één regel te wijzigen is zonde. `--taal nl` doet het
Nederlands.

**Er is hier wél ffmpeg.** `imageio_ffmpeg` heeft een eigen ffmpeg 7.1 aan boord
(`imageio_ffmpeg.get_ffmpeg_exe()`), ook al staat er niets in PATH. De regel bij
*Voorbeelden van een kernmoment* dat er geen ffmpeg is, klopte dus niet — en dat
was de reden dat die clips als 8,3 MB blijven staan met een posterplaatje ervoor.
Verkleinen kan alsnog.

Vijf dingen die in dat script bewust zo zijn:

- **Staand, met het beeld in een kader.** Alles wat de app maakt is 16:9 en
  Instagram is 9:16. Een liggend beeld dat je vult door in te zoomen verliest
  driekwart van zijn compositie, dus ligt het in een kader midden op een donkere
  grond — dezelfde vorm als de DreamCard. Het kader is 960 × 600 en niet
  960 × 680: dat laatste sneed 29% van de zijkanten af en bij *spiders* verdween
  dan de helft van het web. Nu is het 10%.
- **De onderste 420 pixels blijven leeg.** Bij een Reel legt Instagram daar de
  caption, de audioregel en de knoppen over je beeld, en rechts staan liken en
  delen. Alles staat dus tussen 285 en 1500, en niets tegen de rechterrand. Dat
  is strenger dan de 285/1635 van de DreamCard: een verhaal en een Reel bedekken
  niet hetzelfde.
- **Beweging zonder beeldmodel.** Een langzame zoom (1,00 → 1,12 over acht
  seconden) laat een stilstaand beeld leven en kost niets. Een echte animatie bij
  Runway is € 0,55 tot € 1,47 per stuk, dus € 15 tot € 40 voor deze reeks — voor
  een beeld dat acht seconden stilstaat koopt die zoom hetzelfde effect.
- **Geen geluid, en dat is geen gebrek.** Muziek uit de bibliotheek van Instagram
  mag je alleen in Instagram zelf toevoegen; daar geldt die licentie voor. Een
  eigen bestand eronder plakken kan technisch wel, maar dan draait de Reel niet
  mee in de zoekresultaten op dat nummer, en dat is juist waar bereik zit.
- **Onder het beeld staat de gids, niet het merk.** Op de DreamCard staat VERA
  DREAMVERSE met het domein, want die kaart ís de advertentie. Hier is het beeld
  de advertentie en is de vraag net gesteld, dus staat er waar het antwoord ligt:
  *VERA'S DREAM GUIDE* met `vera-dreamverse.com/dream-meaning`. Het
  overzichtsadres en niet de diepe link — dat laatste is 43 tekens die niemand
  overtypt. De diepe link staat wél in de caption.

**Kleiner in plaats van korter.** Past een titel niet in twee regels, dan gaat de
letter omlaag (84 → 54 punten) en wordt er niets weggelaten. Er stond eerst
`[:2]`, en dan verliest *Dreaming about being naked in public* zijn laatste
woorden zonder dat iets het meldt — een fout die je pas ziet als hij al op
Instagram staat. Zelfde regel voor de vraag eronder, met drie regels als grens.

**De caption is een uittreksel, geen artikel.** Vera's regel als haak, de opening
van het artikel, de drie brillen met elk hun eerste zin, dan de vragen die de
betekenis kantelen, dan de link. Alle 27 komen tussen 1100 en 1500 tekens uit;
Instagram kapt af op 2200 en `main()` waarschuwt als een onderwerp daarboven
komt — afgekapt betekent hier dat juist de link en de hashtags wegvallen.

**Van de opening worden minstens twee zinnen genomen, en dat is geen smaak.** Bij
*dying* staat de ontkenning in de **tweede** zin (*"a dream about dying carries
no information about anybody's health, safety or lifespan"*), bij *pregnancy* in
de eerste. Eén zin pakken zou dus per onderwerp verschillen, en juist bij deze
twee mag dat niet.

**De hashtags zijn klein gehouden.** De slug plus hoogstens twee uit `also`, dan
zes vaste. `also` bestaat voor de zoekwoorden van de gids en die zijn voor Google
geschreven: als zoekvraag is *someone I love dying* normaal, als hashtag iets
anders — en Instagram beperkt de zichtbaarheid van een deel van dat soort tags,
waarna een post in stilte verdwijnt. Welke dat zijn is hier niet na te kijken.
**Kijk bij `dying` en `deceased-person` zelf naar de tags voordat je plaatst.**

De bestanden staan in `data/reels/` en dat is git-ignored: 27 video's is ~27 MB
en die horen niet in de repo. Ze staan dus alleen op de machine die ze maakte, en
moeten naar je telefoon om geplaatst te worden.

## Eerst de droom, dan pas het account

Het eerste scherm van `/app` was naam, e-mail en wachtwoord — gevraagd aan
iemand die nog niet weet wat hij ervoor terugkrijgt. Nu staat er *Wat droomde je
vannacht?* met een tekstvak en *Inspreken*, en verder niets. Pas als die tekst
er staat komt de account, met een reden erbij: *Je droom staat klaar voor Vera.*

**De tekst blijft tot dat moment alleen in de browser** (`dreamverse_eerste_droom`
in `localStorage`, een dag geldig). Dat is geen gemak maar een grens: een droom
is een bijzonder persoonsgegeven en er is nog geen account om hem aan te hangen,
dus hij gaat pas naar de server als de gebruiker bestaat. Wie afhaakt kost
daardoor ook niets — er wordt niets gegenereerd voordat het account er is.

**Na het aanmelden komt de tekst in de invoer en licht de knop op, maar hij
wordt niet verstuurd.** Verbeelden kost geld en soms tokens, en de kwaliteit is
een keuze die hij nog niet gemaakt heeft. Zelfde regel als bij een gesprek met
Vera: daar wordt ook nooit vanzelf een verbeelding van gemaakt.

Drie dingen die hier stuk waren en meelopen:

- **De poort was altijd Nederlands.** Zolang het een inlogvenster was viel dat
  nauwelijks op; als eerste scherm van het product krijgt iemand die net op
  *Start for free* heeft gedrukt een Nederlandse vraag. `poortTaal()` leest
  dezelfde `dreamverse_taal` als `welkom.html` en `privacy.html`, met de
  browsertaal erachter en Engels als standaard.
- **Die taal gaat mee bij het registreren** (`taal` in de body van
  `/api/registreren`). Zonder dat begon iedereen op Nederlands, ook wie zijn
  droom in het Engels intypte — en een duiding wordt geschreven en niet
  vertaald, dus dat is achteraf niet te herstellen.
- **Vera's introductie wordt overgeslagen als er een droom klaarstaat.** Anders
  krijgt iemand die net zijn naam heeft ingevuld meteen een venster dat opnieuw
  om naam, geboortedatum en geslacht vraagt — precies het scherm waar dit pad
  omheen gebouwd is. `startteMetDroom` wordt gezet *voordat*
  `eersteDroomOverzetten()` de opslag leegmaakt, want `toonIntro()` haalt eerst
  het profiel op en is dus later klaar. De introductie staat nog gewoon bij *Je
  gegevens*, en de geboortedatum wordt pas bij een aankoop gevraagd.

## Twee letters, en waarvoor ze zijn

`--display` is Cormorant Garamond, `--body` is Karla. De verdeling is niet
willekeurig en er hoort niets buiten te vallen:

- **Cormorant** is wat je léést: koppen, de alinea's van de duiding, "Je dromen
  samen", het klein voorstel voor vandaag, het invoerveld waar je je droom in
  typt, en de woordenlijst van de gids.
- **Karla** is alles eromheen: labels, knoppen, tabellen, de kleine lettertjes,
  de bovenregel en de voetregel.

Er staat nergens een letternaam in `style.css` — alleen `var(--display)` en
`var(--body)`. Wat er wél misgaat is dat een element helemaal vergeten wordt en
op de erfelijke basismaat blijft staan (16,5px Karla). Zo gebeurde het twee keer:

- **`.lbl` was `.block .lbl`.** De zes labels búiten een `.block` — *Wat je
  vertelde*, *Als deze droom een opdracht was*, *Vraag iets over deze droom*,
  *Wat kan er beter?*, *Je naam en je geboortedatum*, *Alles
  meenemen/weghalen* — kregen daardoor géén opmaak en stonden als gewone tekst
  van 16,5px tussen kopjes van 10,4px in kapitalen. Twee regels verderop staat
  `.terugkoppeling .lbl { color: … }`, die dus een basis aannam die er niet was.
  De opmaak hangt nu aan **`.lbl` zelf** en de blokken zetten alleen nog de
  kleur. Nagemeten: alle zestien labels zijn Karla 10,4px in kapitalen.
- **De woordenlijst van de gids in de app** stond in Karla op de basismaat,
  terwijl diezelfde titels op `/dream-meaning/` als `.gids-kaart-titel` in
  Cormorant staan. Dezelfde woorden, twee lettertypes.
- **`.lead` bestond alleen in `welkom.html`, niet in `style.css`.** Drie
  alinea's op de landingspagina — het stuk van Ruud en de uitnodiging naar de
  Dream Guide — hadden dus geen letter, geen maat en geen grond, terwijl alles
  eromheen een kaart is. Daardoor stond juist de Dream Guide daar als los
  zwevend leesvoer. Nu Cormorant op een eigen grond, met de ondertekening
  eraan vast.

Zoek zulke gevallen zo, in de console van de app:

```js
document.querySelectorAll("p,li,span,a,div").forEach(e => {
  if (e.children.length || (e.textContent||"").trim().length < 4) return;
  if (Math.abs(parseFloat(getComputedStyle(e).fontSize) - 16.5) < .3)
    console.log(e.className || e.tagName, e.textContent.trim().slice(0, 40));
});
```

Alles wat daar uitkomt is óf bewust body-tekst óf vergeten. `.sub`, `.belofte`
en `.belofte-sub` staan er bewust in.

## Leesbaar boven een bewegende achtergrond

Het doek achter de app beweegt en is op sommige plekken fel oranje, cyaan of
paars. Alles wat daar rechtstreeks op ligt is daarom soms leesbaar en soms niet,
en "soms" bestaat hier niet als eis. Twee keer is dat misgegaan op precies
dezelfde manier: de woordenlijst van de gids, en de vier links onderaan de app.

**De regel: tekst krijgt een eigen grond van `rgba(13, 7, 26, .92)`, geen waas.**
Op halve dekking schijnt een felle plek er dwars doorheen. Nagerekend als
contrastverhouding (WCAG; 4,5:1 is de ondergrens voor gewone tekst, en de
rekensom staat hieronder zodat je hem kunt herhalen):

| grond | `--ink` | `--muted` |
|---|---|---|
| `rgba(13,7,26,.92)` | 15,4:1 | 6,8:1 |
| `rgba(8,6,17,.55)` | 5,5:1 | 2,5:1 |
| `rgba(8,6,17,.50)` | 4,8:1 | **2,1:1** |

Dus: `footer.end`, `.gids-woorden`, `.gids-geen`, `.meta`, en op de
landingspagina `.lead`, `.ondertekening`, `.waaraan-kop` en `.gegevens-voet`
staan op `.92`. `.sub` en `.head-rule p` mogen op `.55` blijven omdat ze in
diezelfde regel hun kleur naar `#F6F2FF` zetten en daarmee boven de 5:1
uitkomen. De `h2`'s van een sectie liggen bewust los op de achtergrond: 30px
Cormorant met een schaduw houdt zich daar wél.

**`welkom.html` heeft geen canvas maar wel felle verlopen.** Daar zit geen
bewegend doek achter, maar `body::before` legt er radiale verlopen tot
`rgba(214,150,255,.85)` overheen. Dezelfde eis geldt er dus.

Zo controleer je een pagina in één keer — dit zoekt tekst waar tússen hem en de
`body` niets met een vulling zit:

```js
function heeftGrond(e){let n=e;while(n&&n!==document.body){const c=getComputedStyle(n);
  if(c.backgroundColor!=="rgba(0, 0, 0, 0)")return true;n=n.parentElement;}return false;}
document.querySelectorAll("p,h2,h3,li,.lbl").forEach(e=>{
  if(!e.textContent.trim()||!e.getBoundingClientRect().height||heeftGrond(e))return;
  console.log(e.className||e.tagName, getComputedStyle(e).fontSize, e.textContent.trim().slice(0,34));
});
```

**En een link is strenger dan tekst.** `.gids-woorden a` en `.voet-links a`
stonden op `var(--crown)` en `var(--muted)`; die moeten niet alleen leesbaar zijn
maar ook nog van gewone tekst te onderscheiden. Ze zijn nu `var(--ink)` met een
paarse onderstreep. Een `text-shadow` — wat `.sub, .head-rule p, .meta,
.meter-noot, footer.end, .antwoord-uitleg` doen — helpt bij losse tekst, maar
niet bij een link en niet boven de felste plekken.

## De publieke pagina

`static/welkom.html` is wat iemand zonder account te zien krijgt: wat Dreamverse
doet, de vier pakketten met prijzen, wat een token kost, waar de grenzen liggen,
en de kleine lettertjes met opzegtermijn, restitutie, KvK en contactadres. Buiten
basic auth, net als de privacyverklaring.

Twee redenen dat hij er is. **Voor Stripe**: bij Managed Payments zijn zij de
verkoper en beoordelen ze de site, en tot vandaag zag een beoordelaar alleen een
inlogscherm. **Voor testers**: die kregen een wachtwoordveld zonder te weten waar
ze aan begonnen.

**En hij blijft bereikbaar na het inloggen.** `/` stuurt alleen naar
`welkom.html` zolang je uitgelogd bent, dus wie eenmaal binnen is zag hem nooit
meer — precies de mensen die betalen konden niet meer nalezen wat de app doet,
wat het kost en wie erachter zit. Onderaan de app staat daarom een regel met
*Over Dreamverse*, *Pakketten en prijzen* (`#kosten`) en *Privacyverklaring*.

Hij staat **los van de app**: geen `app.js`, geen `taal.js`. De vertaling zit in
de pagina zelf, met `data-en` en `data-nl` naast elkaar op elk element, en
Engels is er de standaard — Nederlands alleen als de browser dat zegt of de
bezoeker het kiest. Dat is bewust: deze pagina is het eerste wat iemand van
buiten Nederland ziet.

## Twee talen

De pagina is in het Nederlands geschreven; `static/taal.js` houdt per zin bij wat er
in het Engels moet komen, met de Nederlandse zin als sleutel. Er is dus geen
sleutelregister om bij te houden — je verandert de tekst in `index.html` en zet de
vertaling erbij. Witruimte telt niet mee bij het opzoeken.

**De duiding wordt niet vertaald maar in de gekozen taal geschreven.** De taal staat
in het profiel en gaat mee in de prompt; vertaalde duiding leest als vertaalde
duiding, en dit product staat of valt bij de toon. Het veld `image` blijft altijd
Engels, want dat gaat naar een beeldmodel.

`<html translate="no">` staat er niet voor niets: Chrome zag de pagina als Engels en
maakte van *Praat met Vera* "Praat ontmoette Vera".

## Wat Kling kost

Officiele tabel: <https://kling.ai/document-api/pricing/base/image>. Kling heeft
documentatie voor modellen op <https://kling.ai/document-api/llms.txt> — handig,
want de gewone prijspagina is een JavaScript-app waar geen enkele fetcher
doorheen komt.

Wij draaien op **Kling Image 2.1, text-to-image**: 4 eenheden à $0,0035 =
**$0,014 per paneel**, dus $0,07 (€ 0,06) aan beeld per droom. Nagemeten op
twintig panelen: precies 4,0 eenheden per stuk. Let op dat **image-to-image het
dubbele kost** (8 eenheden) — dat telt zodra we paneel 1 als stijlreferentie
voor de rest zouden gebruiken: dan wordt een droom 36 eenheden in plaats van 20.

Het probleem is niet de prijs maar de **instap**: het kleinste betaalde pakket is
$350 voor 100.000 eenheden, ofwel 5.000 dromen, met 180 dagen geldigheid en geen
rollover. Dat verdient zichzelf pas terug rond de 140 abonnees die een half jaar
blijven. Voor een testronde van dertig dromen ($2,10 aan verbruik) is het een
afschrijving, geen investering. De proefpakketten die er nu staan verlopen
**18 september 2026**.

## Het rapport

`rapport.py` en `GET /api/beheer/rapport`, te zien op `/beheer`. Het antwoord op de enige vraag die telt: **tien testpersonen, drie
dagen, wie komt er op dag vier uit zichzelf terug.** Bovenaan staat dat cijfer,
daaronder mensen, dromen, actieve dagen, gestelde vragen en omzet, en een tabel
per gebruiker.

"Terug" is bewust streng: een **droom** op dag vier of later, geen bezoek. Wie
alleen even kijkt is geen gebruiker.

**De trechter staat bovenaan: bezoek -> account -> droom.** Zonder dat zie je
pas iets zodra iemand een account maakt, en weet je nooit of er honderd mensen
keken en afhaakten of dat er simpelweg niemand kwam — twee heel verschillende
problemen. De tabel `weergaven` telt per dag per pagina hoe vaak `welkom.html`
en `index.html` geserveerd zijn. **Geen IP-adres, geen cookie, geen kenmerk
waarmee iemand te herkennen is**, dus geen banner en niets in de
privacyverklaring: dit is optellen, geen volgen. Daarom staat er ook geen
"unieke bezoekers" — om twee bezoeken aan dezelfde mens toe te schrijven moet je
die mens herkennen, en precies dat doen we niet.

Geteld wordt op de plek waar de **pagina** wordt geserveerd, niet bij de
statische bestanden: anders tel je stylesheets en plaatjes mee. De scanbots die
dagelijks op PHP-lekken zoeken vragen paden op die daar nooit langskomen, en wat
er alsnog doorheen glipt vangt `is_robot()` op de browsernaam. Nagemeten: drie
bezoeken als Chrome tellen, vijf als AhrefsBot niet, PHP-scans niet, de
stylesheet niet. `tel_weergave()` faalt nooit hardop — een teller mag geen
pagina kosten.

Het percentage verschijnt pas vanaf tien gemeten bezoeken, en alleen over dagen
waarop er ook echt geteld is. Het tellen begon later dan de eerste accounts, en
anders deel je twee getallen op elkaar die over verschillende weken gaan.

**Geen derde partij, geen cookies, geen banner.** Alles komt uit gegevens die er
al waren — `users.gemaakt`, `dromen.wanneer`, de vragen in de bewaarde
verbeelding, de tabel `betalingen` — plus `usage.checkout()` voor het begin van
de trechter. Daarom staat er ook **geen klikgedrag** in: waar mensen klikken en
waar ze afhaken zou clientmeting vragen, en dat is precies de stap die een
cookiebanner oplevert en het gedrag van dromers bij een advertentiebedrijf legt.

    python rapport.py

## Wat er nog niet is

- **Kling is aangesloten maar niet getest tegen de echte API** — er was hier geen
  sleutel. De client in `kling.py` is geschreven op de publieke documentatie.
  Zet `KLING_ACCESS_KEY` en `KLING_SECRET_KEY` in `.env` en draai eerst
  `python kling.py --check`: die maakt één afbeelding en drukt alles af wat
  terugkomt. Klopt een veldnaam niet, dan zie je precies welke. Zonder sleutels
  blijven de getekende composities staan; dat is geen storing maar het ontwerp.
- **Het gesprek met Vera werkt.** Ruud heeft er meermalen over zijn dromen mee
  gesproken, en op 2 september 2026 is de hele keten ook gemeten: de worker komt
  als `worker:<sessie-id>` de kamer binnen en publiceert **audio én video**.
  Let op: `consume` is eenmalig. Loopt de verbinding daarna stuk, dan is de sessie
  op en moet er een nieuwe komen.
  `realtime_sessions.create` heeft ook een veld `integration` (elevenlabs of
  livekit) om de avatar op een eigen stemagent te zetten. Dat is **niet** nodig:
  zonder dat veld doet Runway het gesprek zelf, met `personality` en
  `start_script`. Laat je erdoor niet op een dwaalspoor zetten.
- **`VERIFICATIE_NODIG=1` sluit iedereen buiten.** Er is een bevestigingscode
  per account en een eindpunt om hem in te wisselen, maar `mail.py` kent alleen
  `herstelbericht` - een verificatiemail bestaat niet, en in die tak gaat de
  code zelfs niet naar de log. Zet hem dus niet aan voordat het versturen er is.
  Vandaag krijgt een nieuwe gebruiker helemaal geen mail: hij is meteen
  ingelogd, en dat is met opzet zo.
- **Het archief is een bestand op schijf** en dus weg bij elke Render-deploy. Voor
  iets echts hoort daar een database.
- **Geen betaling.** Pakket en tokensaldo worden met de hand gezet, in het
  beheerpaneel. Zie hieronder.

## Beheer staat op /beheer, buiten de app

Het zat *in* de app: de opmaak in `static/index.html`, de code in
`static/app.js`, de sleutel in `localStorage`. Daarmee downloadde elke ingelogde
dromer de hele beheerlaag — de knoppen voor pakketten en tokensaldo, de
kostprijs per droom, de webhooklog en het rapport. Wijzigen kon hij niet
(`hmac.compare_digest` tegen `ADMIN_TOKEN`, en zonder die variabele weigert de
server helemaal), maar lezen wel. Verbergen gebeurde met een vlag in JavaScript,
en dat is geen slot maar een gordijn.

Nu:

- **Een eigen pagina.** `/beheer` → `static/beheer.html` plus
  `static/beheer.js`. De pagina zelf is een schil met een sleutelveld; de
  knoppen en de cijfers komen van `GET /api/beheer/paneel`
  (`beheer/paneel.html`, buiten `static/`) en alleen als de sleutel klopt. In
  `index.html` en `app.js` staat er geen letter meer van, en de dode
  beheerzinnen zijn ook uit `taal.js` gehaald — die stonden er nog met
  `?beheer` en "ADMIN_TOKEN staat bij Render onder Environment" in.
- **Een eigen sessie, geen sleutel in de browser.** `POST /api/beheer/inloggen`
  neemt de sleutel één keer aan en geeft een cookie terug dat **HttpOnly** is:
  JavaScript kan er niet bij, ook het onze niet. Dát is de winst. De sleutel
  stond in `localStorage` op dezelfde origin als de app, en dan is één XSS in de
  dromerkant genoeg om hem te stelen. Twee-factor helpt daar niet tegen — wat
  gestolen wordt is niet het wachtwoord maar het bewijs dat je het al gegeven
  hebt. `SameSite=Strict`, acht uur geldig, en de sessies leven in het geheugen
  van het proces: een deploy meldt je af. Dat is geen gebrek maar de bovengrens
  op hoe lang zo'n sessie kan blijven staan.
- **Geen dromersessie nodig.** Alles onder `/api/beheer/` valt buiten `guard()`
  en hangt alleen aan `beheer_ok()`. Beheren doe je als beheerder, niet als
  iemand met een droomarchief.
- **Een rem op raden.** Na drie missers een seconde per poging. Er is precies
  één sleutel en die verandert nooit, dus dit is het enige eindpunt waar brute
  kracht loont.
- **De header blijft werken.** `X-Admin-Token` doet het nog, voor een script of
  een curl vanaf de eigen machine.

De paden zijn verhuisd: `/api/rapport` → `/api/beheer/rapport`,
`/api/webhooklog` → `/api/beheer/webhooklog`, `/api/usage` →
`/api/beheer/usage`, `POST /api/account` → `POST /api/beheer/account`. Die
laatste eist nu **`wie`**: vroeger was leeg-laten "mijzelf", maar op een pagina
zonder ingelogde dromer is er geen mijzelf, en raden bij een handeling die
gratis Ultra uitdeelt is precies wat je niet wilt. `/api/usage` had trouwens
*helemaal geen* controle — elke ingelogde dromer kon opvragen wat de hele
installatie tot nu toe gekost heeft.

**Tokensaldo** *zet* een vast aantal (`{"saldo": 500}`), waar `{"tokens": 10}`
optelt. Zetten moest erbij omdat optellen eerst vraagt wat er stond, en tussen
die twee stappen kan een gesprek met Vera er een paar afhalen. Op Render is geen
shell, dus zonder dat veld is "zet mij op 500 tokens" niet te doen. Dat pad zet
alleen; er komt geen droom en geen duiding van een ander langs, en na afloop
gaat de gebruikerslaag in een `finally` terug naar wie er echt aan de lijn is.

**Het paneel tekende niet wat het rapport wist.** `laadRapport()` gebruikte negen
van de zestien velden die `GET /api/beheer/rapport` teruggeeft: het cijfer van
dag vier, de tegels en de tabel met wie er is. Wat er níet stond was
`trechter` — bezoek, account en droom **per dag** — en dat is precies wat je
opzoekt als je je afvraagt of er aanmeldingen zijn. Antwoord op die vraag was
alleen te krijgen met `python rapport.py` op de eigen machine, en op Render is
geen shell. Nu staan er drie blokken in: *Per dag: bezoek, account, droom* (met
een samen-regel en dezelfde drempel van tien gemeten bezoeken voordat er een
percentage komt), *Waar ze vandaan kwamen* uit `bronnen`, en *Wie er is*. Nog
steeds niet getekend: `feedback`, `pakketten`, `per_dag` en `betalingen` — die
staan wel in `python rapport.py`.

**En het rapport verborg zich stil.** Ging het verzoek mis, dan zette
`laadRapport()` het hele blok op `hidden` zonder een woord. Dan zoek je naar
cijfers die er niet zijn in plaats van naar een verzoek dat niet lukte. Nu komt
er een regel met de reden.

**Alles uit de database gaat door `esc()` voordat het in `innerHTML` belandt.**
Dat was niet zo, en dit is de gevaarlijkste plek van de app om dat te vergeten.
`accounts.EMAIL` laat alles toe wat geen apenstaartje of witruimte is — dus ook
punthaken — dus kon iemand zich aanmelden met een adres waar een `<img
onerror=…>` in staat en wachten tot de beheerder zijn eigen ledenlijst opent.
Het cookie is HttpOnly, maar script dat op deze pagina draait hoeft die sleutel
niet te lézen om hem te gebruiken: het kan `POST /api/beheer/account` aanroepen
en zichzelf Ultra en tokens geven. Nagemeten met een account met precies zo'n
adres: het komt er als tekst uit, er staat geen enkele `<img>` in het rapport en
`document.title` blijft staan.

**Wat er nog niet is:** een tweede beheerder, en daarmee ook geen reden voor een
beheerdersaccount met MFA. Zolang er één operator is, is een sleutel die je
inruilt voor een HttpOnly sessie het eerlijke antwoord.

## Wat de AVG hier betekent

Dromen zijn geen gewone gegevens: mensen vertellen erin over hun angsten, hun
relaties en hun overledenen. Daarom staan deze drie dingen er, en ze horen te
blijven.

- **`GET /api/mijn-gegevens`** geeft alles als zip: profiel, dromen, duidingen,
  betalingen, en al het beeld en geluid. Het wachtwoord zit er niet in — dat
  bewaren we niet, alleen een afdruk.
- **`POST /api/account-verwijderen`** haalt alles weg, en vraagt om het
  wachtwoord. Onomkeerbaar, dus een verdwaalde klik of een openstaand tabblad op
  een gedeelde computer mag het niet doen. **Loopt er een abonnement, dan wordt
  dat eerst bij Stripe opgezegd** — anders blijft iemand betalen voor een account
  dat niet meer bestaat. Lukt dat opzeggen niet, dan gaat de verwijdering niet
  door.
- **`static/privacy.html` is tweetalig**, op dezelfde manier als `welkom.html`:
  `data-en` en `data-nl` naast elkaar, Engels als standaard, en dezelfde
  opgeslagen keuze (`dreamverse_taal`) — wie op de landingspagina Engels koos
  krijgt hier ook Engels. Het script zet `textContent`, dus de keuze staat op
  elementen die **alleen tekst** bevatten; een alinea met een `<strong>` erin is
  daarom opgesplitst in `<strong>` plus `<span>`. Onderaan staat dat de
  Nederlandse tekst geldt waar de twee verschillen: Dreamverse wordt vanuit
  Nederland gevoerd.
- **`static/privacy.html`** noemt de verwerkers met naam: Anthropic (de tekst),
  Kling (de panelen), Runway (beeld, stem en Vera), Stripe (het afrekenen) en
  Render (waar het draait). Verandert er een leverancier, dan verandert die
  pagina mee.

De betaalregels blijven na verwijdering staan zonder gebruiker: een bedrag, een
datum en een gebeurtenis-id. Dat is boekhouding en er staat niets persoonlijks
in.

## Onder welke naam

**Peek BV.** Op 7 september 2026 is de SBI-code voor softwareontwikkeling aan de
KvK-inschrijving toegevoegd (KvK 18030812), juist omdat Managed Payments het
bedrijfsprofiel beoordeelt en daar tot dan alleen een installatiebedrijf stond.
De domeinen, het Stripe-account en de landingspagina staan allemaal op die naam.

Later verhuizen naar een andere entiteit kan, maar de prijs loopt op: domeinen
verhuizen eenvoudig, **Stripe-abonnementen niet**. Die hangen aan het account van
de entiteit, dus bij een verhuizing moeten klanten hun betaling opnieuw
goedkeuren. Bij nul klanten kost dat niets; bij vijftig kost het een deel van
die vijftig.

## Afrekenen

Stripe **Managed Payments**: Stripe is de verkoper en draagt de btw af in ruim
tachtig landen. 5% + $0,50 per transactie, tegen ongeveer 1,5% + € 0,25 bij
gewoon Stripe — dat verschil koop je bewust, want zelf OSS-aangifte doen over
27 tarieven kost meer.

```bash
python betalen.py --check     # staat alles klaar?
python betalen.py --setup     # producten en prijzen aanmaken
```

**Live sinds 8 september 2026.** De activatie liep via de instelwizard van
Managed Payments; die dwingt je met de hand een eerste product te maken, vandaar
dat `setup()` bestaande producten op naam hergebruikt. Belastingcategorie op het
account: *AI as a Service (AIaaS) - Cloud Based - Personal Use*, oftewel
`txcd_10105001` — er zijn vier AIaaS-varianten en de andere drie zijn zakelijk of
"cloud én gedownload", allebei fout hier.

De sleutel is een **beperkte** sleutel (`rk_live_`), geen volledige. Hij mag
schrijven op Checkout Sessions, Customers, Products, Prices, Subscriptions en
Billing Portal Sessions, en lezen op Balance en Webhook Endpoints — verder niets,
dus geen uitbetalingen en geen bankgegevens. Mist er ooit een recht, dan noemt
Stripe het letterlijk in de foutmelding; zo kwam `plan_write` (dat is *Prices*,
onder zijn oude naam) alsnog aan het licht.

Drie dingen die makkelijk fout gaan:

- **`tax_behavior` is `inclusive`.** Anders telt Stripe de btw *boven op* je
  prijs en rekent een klant bij € 2,99 straks € 3,62 af. Nagemeten op de
  betaalpagina: subtotaal € 2,99, btw € 0,52, totaal € 2,99.
- **Belastingcode `txcd_10105001`** (AI as a Service, particulier gebruik).
  Managed Payments accepteert alleen codes uit een vaste lijst.
- **Een geweigerde handtekening zegt niet welk van twee dingen fout is.**
  `SignatureVerificationError` komt zowel van een verkeerd geheim als van een
  klok die uit de pas loopt, en een verkeerd geheim ziet er precies zo uit als
  een nagemaakte melding. `python betalen.py --webhooks` laat zien welke
  endpoints dit account heeft, in welke modus (sandbox of live), of
  `checkout.session.completed` erbij staat, en of `STRIPE_WEBHOOK_SECRET`
  überhaupt gezet is. Elke endpoint heeft zijn eigen ondertekengeheim en aan het
  geheim is niet te zien bij welke het hoort — dus wie een endpoint eerst in het
  live-account maakte en daarna in de sandbox, heeft het oude geheim nog staan
  en krijgt elke betaling geweigerd terwijl Stripe meldt dat hij hem afleverde.
- **De webhook is het gevaarlijkste eindpunt van de app.** Hij komt binnen
  zonder sessie, en de handtekening is het enige bewijs. Zonder
  `STRIPE_WEBHOOK_SECRET` wordt alles geweigerd — dat is de veilige stand.
  Elke gebeurtenis wordt één keer verwerkt; het id gaat in de tabel
  `betalingen`, want Stripe stuurt opnieuw als hij geen 200 krijgt.

Tokens blijven staan als iemand opzegt: die zijn gekocht, niet gehuurd.

## Accounts

`accounts.py` met SQLite in `data/dreamverse.db`. Per gebruiker gescheiden: de
dromen, de duidingen, het pakket, het tokensaldo en de maandtellers. Wachtwoorden
door `hashlib.scrypt` — en `maxmem` moet expliciet ruimer, want 128·n·r komt op
precies de 32 MB die OpenSSL standaard toestaat.

**De panelen liggen in één map, met het gebruikersnummer in de naam**:
`1_12-2.png` is paneel 2 van droom 12 van gebruiker 1. Daardoor hoefde er in
`kling.py`, `stem.py` en `video.py` niets te veranderen — die krijgen
`dreamverse.sleutel(n)` waar ze eerst een nummer kregen, en zoeken nog steeds op
`"<sleutel>-*"`. De route `/panels/<bestand>` controleert dat de naam met jouw
nummer begint; anders kun je met een gokje in andermans dromen kijken.

Wie er aan de lijn is staat in een thread-lokale plek (`accounts.zet_huidige`),
gezet door `Handler.guard()`. Dat kan omdat de server één thread per verzoek
draait. Achtergrondthreads raken de gebruikerslaag niet aan: die krijgen hun
bestandssleutel mee. `accounts.huidige()` **gooit** als er niemand is — liever
hard stuk dan stil de gegevens van iemand anders aanraken.

**Wachtwoord vergeten werkt.** Verstuurd via het Gmail-account
`vera.dreamverse@gmail.com`, met een app-wachtwoord van zestien tekens — je
gewone Google-wachtwoord wordt geweigerd met `535 Username and Password not
accepted`, en app-wachtwoorden bestaan alleen als tweestapsverificatie aanstaat.
De spaties waarmee Google het toont worden in `mail.py` weggehaald.

Een gratis Gmail mag ongeveer 500 berichten per dag en levert slechter af dan
een eigen domein. Voor tien testpersonen prima; wordt dit een product, dan hoort
daar een verzenddomein met SPF en DKIM bij — dat is één regel in `.env`.

**Hoe het gebouwd is.** `mail.py` gebruikt `smtplib`
uit de standaardbibliotheek — geen nieuwe afhankelijkheid. Zonder `SMTP_HOST`
gaat de herstellink naar de serverlog en zegt de app eerlijk dat versturen
uitstaat. Twee dingen die daar goed moeten: de melding is **hetzelfde** voor een
bestaand en een onbekend adres (anders is dat eindpunt een manier om uit te
zoeken wie een account heeft), en de link staat **nooit** in het antwoord —
alleen in de mail.

**Wie zich aanmeldt krijgt een welkomstmail, met de bevestigingslink erin.**
Twee dingen in een bericht, met opzet: een aparte verificatiemail leest als een
hindernis, dit leest als een bericht dat je toch al kreeg. Inloggen gebeurt
meteen, dus de mail staat nooit tussen iemand en zijn eerste droom. Mislukt het
versturen, dan gaat de aanmelding gewoon door en komt er een regel in de log -
een haperende mailserver mag geen account kosten.

`GET /api/bevestigen?code=...` wisselt de code in en stuurt door naar
`/?bevestigd=1` of `=0`; de app zet daar een regel over in de statusregel. Dat
eindpunt **bestond eerder helemaal niet**: het stond wel in `VRIJ` maar er was
geen afhandeling voor, dus `VERIFICATIE_NODIG=1` zou iedere nieuwe gebruiker
buitengesloten hebben. Nu kan die vlag veilig aan.

**Een aanmeldtest op deze machine verstuurt een echte mail.** `.env` bevat de
Vera-Gmail met app-wachtwoord, dus `mail.enabled()` is hier `True` en elke
registratie stuurt de welkomstmail werkelijk vanaf `vera.dreamverse@gmail.com`.
Bij een verzonnen adres komt de bounce in diezelfde inbox, en dat is precies wat
er op 9 september acht keer gebeurde: het live-rapport laat op die dag nul
aanmeldingen zien, dus die mails kwamen van hier. **Haal `SMTP_HOST` uit `.env`
voordat je dat pad test** — dan schrijft `mail.py` de link naar de log en
verstuurt hij niets, en dat is precies waar die tak voor gemaakt is.

Twee dingen om te weten bij het lezen van zo'n bounce. Het adres waar het
naartoe ging staat in de `To`-regel van het teruggestuurde origineel. En de
**bevestigingslink verklapt de afzender**: `basis_url()` leest `PUBLIEKE_URL` en
valt anders terug op `http://127.0.0.1:8000`. Die variabele staat niet in de
lokale `.env` en wel op Render, dus een link naar 127.0.0.1 komt van een lokale
run en een link naar het echte domein van de live server.

## Vera bij Runway

Avatar-id `43e6b2b0-29ea-4125-8e2f-3ebed04f65d1`, stem **Violet** (Gentle),
status READY. **Dit is niet Cat (`761a6d44…`) en niet Pia (`75144525…`).**
`avatars.update(document_ids=...)` vervángt de hele set, dus stuur altijd alle
id's mee die moeten blijven — ze staan in `build/document-ids.json`.

Gekoppeld: `intuitief-dromen`, `soorten-dromen` en `chakras`. Met de persona erbij
zit je op ruim 18.000 tekens van de 100.000. Boven die grens gaat de avatar
zwijgen zonder dat iets een fout meldt.

Een document erbij zetten of vervangen:

```bash
python build/add_document.py knowledge/chakras.txt
```

Dat stuurt alle bestaande id's mee, ruimt de vorige versie op en werkt
`build/document-ids.json` bij.

## Wat er in de pakketten zit

| | prijs | dromen/maand | panelen | avatar |
|---|---|---|---|---|
| Gratis | € 0 | **3** | **de eerste** met vijf panelen, daarna de duiding | alleen met tokens |
| **Lite** | **€ 2,99** | **3** | ja, vijf getekende panelen | alleen met tokens |
| Plus | € 7,99 | 6 | ja, plus **drie** bewegende kernmomenten | alleen met tokens |
| Ultra | € 29,99 | 10 | ja, **vijf** kernmomenten op het beste model | 10 minuten inbegrepen |

**Niet elke droom krijgt een kernmoment, en dat is het besluit dat Plus en Ultra
gezond maakt.** Met alle zes kostte Plus € 4,14 per maand en bleef er 20% over;
met drie is het € 2,49 en **41%**. Ultra ging van 16% naar 41%. Die ene animatie
bij Runway kost € 0,55 tot € 1,47, tegen € 0,14 voor een hele droom zonder — dus
het is precies die knop die de marge opat. Het maandtegoed staat in
`PLANS[...]["kernmomenten"]`, de teller in `users.kern_op`, en die rolt om met
`dromen_op` en `avatar_sec`. Is hij op, dan kost een kernmoment tokens; koopt
iemand er zo een, dan gaat zijn maandtegoed **niet** ook nog omlaag — anders
betaalt hij twee keer.

**En dat tegoed geldt ook als je het kernmoment achteraf bijkoopt.** Dat was
niet zo: `/api/extra` keek alleen naar het tokensaldo, dus een Plus-gebruiker
met drie ongebruikte kernmomenten betaalde er tien tokens voor terwijl zijn
tegoed onaangeroerd bleef staan. Het pakket belooft "drie bewegende
kernmomenten per maand", niet "drie, maar alleen op het moment dat je de droom
vertelt". `EXTRA_ALS_KWALITEIT` legt de losse aankoop naast de kwaliteit waar
hij bij hoort, en `check_extra()` stelt dan dezelfde twee vragen als bij het
maken: hoort dit bij je pakket, en heb je er deze maand nog een. Geeft hij 0
terug, dan boekt `charge_extra()` de teller op in plaats van tokens af — zonder
dat onderscheid is het maandtegoed oneindig.

**Er was ook geen goedkope losse animatie.** Bij een bestaande droom kon je
alleen `kernmoment_top` kopen (10 tokens, € 1,47), terwijl het Plus-tegoed juist
over het snelle model gaat. Wie er achteraf beeld bij wilde, kocht dus
noodgedwongen de duurste knop die er is. `kernmoment_snel` staat er nu naast
voor 4 tokens — dezelfde prijs als *standaard*, want het is dezelfde animatie.
Het dure model blijft 10 tokens en zit alleen bij Ultra in het tegoed.

Op de knop staat wat het werkelijk kost: zit het in je tegoed, dan blijft de
tokenprijs staan maar doorgestreept, met *in je pakket* ernaast. Welke aankopen
inbegrepen zijn komt uit `extra_inbegrepen` in `/api/account`, zodat die regel
niet ook nog eens in JavaScript staat. **Let op hoe dat getekend wordt:** de
tekst komt uit een `data`-attribuut op de knop en een `::after` in de CSS, en
niet uit de knop zelf. `taal.js` gebruikt de `innerHTML` van een `<button>` als
vertaalsleutel — schrijf je daarin, al is het maar een `data`-attribuut binnen
de `<b>`, dan matcht de sleutel niet meer en blijft de hele knop Nederlands.

**Gratis geeft drie dromen, en alleen de eerste krijgt beeld.** Het was er één,
met het argument dat drie volledige dromen € 0,42 per maand kosten en vier
gratis gebruikers dan één betalende opeten. Dat klopte, maar het kocht die
besparing met het enige wat het abonnement verkoopt: bij één droom is er geen
tweede en geen derde, en dus nooit een verband om te laten zien — `together`
blijft onder de drie dromen met opzet leeg. Drie *volledige* dromen weggeven kan
óók niet, want dan heeft Lite (drie dromen voor € 2,99) geen reden meer om te
bestaan. Vandaar de trap: `GRATIS_MET_BEELD = 1` in `plans.py`, en `PLAN_RANG`
is daarvoor de functie `plan_rang(plan, droomnummer)` geworden. Wie op droom
twee tóch beeld wil koopt het met een token, via dezelfde knop die er al was.
Kostprijs van een gratis gebruiker: € 0,22 per maand in plaats van € 0,15 —
`python prijzen.py --scan` kent die trap, anders rekent hij drie keer het dure
tarief en lijkt de gratis laag bijna drie keer zo duur als hij is.

**En op de derde nacht staat "Vera zag iets" boven de gezamenlijke duiding.**
Dat is het betaalmoment, en met opzet niet "je gratis dromen zijn op": wat
iemand overtuigt is geen grens maar een vondst. Op de kaart staan de tekens die
in meer dan één droom voorkwamen en de draad naar een eerdere nacht, en pas
daaronder de knop naar de pakketten. Er staat **niets** in dat verzonnen is —
`symbols` mag per prompt alleen tekens noemen die vaker dan eens voorkwamen, en
een draad verwijst naar een droom die echt bestaat. Is er geen van beide, dan
blijft de kaart weg: beweren dat er een patroon is terwijl er niets te noemen
valt is de snelste manier om dit onderdeel ongeloofwaardig te maken. Wie al
betaalt ziet hem niet.

Lite kost € 2,99 en niet € 1,99, want bij een klein maandbedrag is de vaste $0,50
transactiekosten het probleem en niet het percentage — op € 1,99 is dat 23% van
de prijs. Drie dromen bij € 2,99 houdt 48% marge; bij € 1,99 was dat 33%.

Tokens gaan per pakket: 20 voor € 7,00, 40 voor € 12,00, 100 voor € 25,00 —
van € 0,35 naar € 0,25 per token, bijna dertig procent korting. Die staffel
loopt bewust naar beneden vanaf € 0,35 en niet vanaf € 0,25: een kernmoment
op het beste model kost 10 tokens en ons € 1,47, dus € 0,147 per token, en
netto houden we van € 0,25 per token ongeveer € 0,19 over. Daaronder wordt de
duurste knop die we verkopen verlieslatend. Een avatarminuut kost 2 tokens (kostprijs € 0,18), een extra
droom kost er 3. De avatar zit bewust in géén enkel pakket onbeperkt: bij € 4,99
is één gesprek van vijf minuten al een vijfde van de omzet.

**Deze marges zijn te optimistisch en dat is doorgerekend op 2 september 2026.**
Draai `python prijzen.py --scan`. Er gaan twee dingen af die niet in `plans.py`
zitten: 21% btw (een consumentenprijs is inclusief) en 5% + $0,50 betaalkosten
bij een merchant of record. Daarmee zakt Plus van 48% naar **20%** en Ultra van
46% naar **16%** — Ultra is slechter dan Plus, doordat tien dromen op *supreme*
€ 16,10 kosten.

Drie conclusies uit die doorrekening:

- **Het bewegende kernmoment eet de marge op.** € 0,14 per droom zonder, € 0,69
  met. Bij zes dromen voor € 7,99 is de netto opbrengst per droom € 0,96. Zelfde
  besluit als bij de avatar: het kernmoment hoort op tokens, niet onbeperkt in
  een pakket. Met *eenvoudig* in Plus gaat de marge naar **61%**, en Ultra met
  *standaard* naar **47%**.
- **Supreme kan in geen enkel pakket.** Tot € 14,99 per maand is de marge
  negatief. Alleen op tokens.
- **Tokens moeten in pakketten van twintig of meer.** De vaste $0,50 per
  transactie maakt een aankoop van twee tokens (€ 0,50) verlieslatend.

De server weigert met **402** en zegt erbij hoeveel tokens er tekortkomen.
Afrekenen van een gesprek gebeurt ná afloop op werkelijk gesproken tijd, naar
boven afgerond per begonnen minuut.

## Op het beginscherm (PWA)

Geen App Store, geen review, geen commissie: `static/manifest.json`, vier iconen
en `static/sw.js`. Iemand zet hem vanuit Safari of Chrome op zijn beginscherm en
het staat er als een app, met het chakra-icoon en zonder adresbalk.

De iconen komen uit `python build/pwa_iconen.py`, dat de chakrapilaar vierkant
snijdt. Vera's portret werkt niet op 48 pixels; zeven lotussen in een lichtbundel
wel.

**De service worker is bewust dom.** Alles is network-first, dus een deploy wint
altijd — een cache die een oude versie serveert terwijl jij net gepusht hebt,
kost een middag zoeken naar een fout die er niet is. En hij raakt `/api/` en
`/panels/` nooit aan: dat zijn antwoorden per gebruiker, en een gecachet
antwoord van iemand anders is het ergste wat een cache hier kan doen.

Aanmelden gebeurt alleen op een beveiligde verbinding en faalt stil: zonder
service worker werkt de app precies zoals hij nu werkt.

## De omgeving op Render

`build/render.py` leest en zet de omgevingsvariabelen van de draaiende dienst,
zodat een prijs-id of een webhookgeheim niet meer met de hand overgetikt hoeft te
worden. Dat handmatige stapje was steeds hetzelfde probleem: de code klopte al,
de omgeving nog niet, en daar zoek je een halve dag naar.

```bash
python build/render.py --check                            # sleutel goed, welke dienst
python build/render.py --env                              # wat staat er nu
python build/render.py --uit-env STRIPE_PRICE_TOKENS20 --ja   # uit .env overnemen
```

Drie remmen zitten er bewust in. Alleen `PUT /env-vars/<sleutel>` wordt gebruikt
en **nooit** de variant die de hele set vervangt - die wist alles wat je niet
meestuurt, en dan staat de app zonder API-sleutel stil. Zetten doet niets zonder
`--ja`; zonder die vlag zie je alleen wat er zou veranderen. En waarden worden
verhuld afgedrukt, want wat in de terminal staat, staat in de scrollback.

`RENDER_API_KEY` geeft toegang tot **het hele account**, niet tot deze ene
dienst. Hij hoort dus alleen in `.env`, en die is git-ignored. Render start de
service opnieuw op zodra een variabele verandert: een paar minuten 502.

## Domeinen

Geregistreerd op 6 september 2026, op naam van Peek BV: `dreamverse.nl`, plus
`veradreamverse` en `vera-dreamverse` op .com, .nl, .eu, .be, .store en .online.
**Naar buiten heet het Vera Dreamverse.** Er staat sinds juni 2026 een app *The
DreamVerse* in de App Store, óók een droomapp met dagboek, spraak en AI-duiding,
en er zijn meer Dreamverse-namen in omloop. Of dat een merkenprobleem is, is
niet vastgesteld — daar hoort een echte check bij voor Benelux (BOIP), EU
(EUIPO, klasse 9, 41 en 42) en de VS (USPTO), en die is nog niet gedaan.
Ondertussen is *Vera Dreamverse* hoe dan ook de veiligere en onderscheidender
naam, en hij staat al op het domein en op Instagram. Dus staat hij nu in alles
wat Google leest: de `<title>` van de drie pagina's, de titels en de JSON-LD van
de gidsartikelen, en auteur en uitgever in het schema. **In de app zelf blijft
er Dreamverse staan** — dat is hoe iemand het noemt zodra hij binnen is, en dat
hoeft niet mee te veranderen met de naam waarop hij ons gevonden heeft.

**`dreamverse.com` is niet van ons.** Gekozen hoofddomein: **vera-dreamverse.com**,
dezelfde naam als het Instagram-account *Veradreamverse*.

Er hoeft geen hostingpakket bij: Render host de app, de registrar levert alleen
DNS. Een website- of doorstuurdienst van de registrar zit het certificaat van
Render juist in de weg.

## Op je telefoon kijken

Start met `HOST=0.0.0.0` en open `http://<het ip van deze pc>:8000` op een
toestel in hetzelfde netwerk. Windows Firewall laat poort 8000 niet vanzelf door;
daar is eenmalig een regel voor nodig.

**Wat daar niet werkt: de microfoon.** Browsers geven `getUserMedia` en
spraakherkenning alleen op een beveiligde verbinding, en `localhost` is de enige
uitzondering. Op `http://192.168.x.x` blijven *Inspreken* en *Praat met Vera*
dus stil. Lezen, typen en de panelen werken wel. Wil je die twee op je telefoon,
dan moet de app achter https staan — Render doet dat vanzelf, en `render.yaml`
ligt klaar.

## Open punten

- **Beantwoord:** een avatarminuut kost €0,18 en een gesprek van vijf minuten
  €0,94. Runway rekent voor `gwm1_avatars` 2 credits vooraf plus 2 per aangebroken
  zes seconden, met een credit van $0,01. Wie opstart en meteen ophangt kost al
  €0,018. Daarom kan de avatar nooit in een vast abonnement van €4,99 — die hoort
  in tokens.
- **Beslist op 7 september 2026: de animatie blijft bij Runway.** Kling kan
  hetzelfde paneel ook laten bewegen — `build/kling_vergelijk.py` legt de twee
  naast elkaar op dezelfde bewegingsopdracht — en het is ongeveer zes keer
  goedkoper. Gemeten op droom 12: Kling v2.1 pro doet vijf seconden voor 3,5
  eenheden en levert 12,9 MB **zonder audiospoor**; Runway veo3.1 doet vier
  seconden voor € 1,47 en levert 1,1 MB **met** geluid. Ruud koos Runway op het
  beeld. Daarmee blijft die ene animatie 91% van de kostprijs van een
  *supreme*-droom, en blijft de vraag open of het kernmoment in Plus hoort of op
  tokens.
- **Beslist op 1 september 2026: panelen blijven bij Kling.** Runway's
  `muse_image` is met €0,009 per beeld de helft goedkoper en op één enkel beeld
  vaak indrukwekkender, maar houdt de stijl niet vast over vijf panelen: het ene
  paneel komt op wit papier, het volgende in een nachtblauwe wereld, en de
  opgelegde geometrie wordt een grote gouden bloem in plaats van een fluistering.
  Kling houdt dezelfde nacht vast, en die samenhang ís het product. Het scheelt
  €0,32 per abonnee per maand; dat weegt niet op tegen een verbeelding die
  halverwege van wereld verspringt. De vergelijkingsbeelden staan in
  `data/vergelijk/`.
  Terugkomen op dit besluit is zinnig zodra `muse_image` met een strakkere
  stijlregel — donkere ondergrond afdwingen, geometrie eruit — een hele set van
  vijf consistent krijgt.
- Twee valkuilen bij Runway-beeldmodellen: `gen4_image_turbo` is beeld-naar-beeld
  en eist een referentieafbeelding, en `muse_image` accepteert alleen zijn eigen
  verhoudingen (breedbeeld is `2016:1152`, niet `1280:720`).
- **Het gesprek levert nu wél droomtekst op**, maar hoe goed is niet gemeten.
  De browser schrijft mee met `SpeechRecognition` terwijl je met Vera praat, en
  bij het ophangen gaat die tekst in de invoer. Runway stuurt zelf geen tekst
  terug, dus dit is de enige plek waar de woorden bestaan. Twee dingen om in de
  gaten te houden: **Vera's eigen stem kan meekomen** via de speakers (de
  echo-onderdrukking van de browser vangt het meeste, een koptelefoon vangt de
  rest), en Firefox en Safari kunnen dit niet — daar zegt de app dat eerlijk.
  Hoe schoon een gesprek van vijf minuten eruit komt, moet uit gebruik blijken.
- **Beslist op 8 september 2026: geen testronde, gewoon open.** Het plan was
  tien testpersonen en kijken wie op dag vier terugkomt. Ruud heeft de app met
  vrienden doorgenomen en kiest ervoor om live te gaan en het aan echte
  bezoekers te vragen. `rapport.py` meet dat cijfer nog steeds - alleen nu op
  wie er uit zichzelf komt in plaats van op een genodigd groepje.
- **De app staat los van het afrekenen.** Gratis werkt zonder Stripe, dus de
  deur kan open terwijl Managed Payments nog beoordeeld wordt. Zolang de
  sandbox-sleutels erin staan geeft een betaalknop een fout uit de sandbox.
