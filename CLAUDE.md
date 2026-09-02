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
  angst en je kunt het niet terugnemen.
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
- **De kleurvelden zijn de chakra's** (`root` tot `crown`). Dat is geen sfeer maar
  betekenis: het model kiest per paneel het veld dat bij het gevoel past, en de
  kijker ziet die keuze terug in de kleur van het beeld.
- **Eén standbestand, drie schrijvers.** `data/panels/<nr>.json` wordt bijgehouden
  door `kling.py`, `stem.py` én `video.py`. Wie zijn hele woordenboek wegschrijft
  gooit het werk van de andere twee weg, dus schrijf altijd samenvoegend. En de
  standaardwaarde bij een ontbrekend bestand is `status: "off"`, nooit `"done"`:
  met `done` en nul panelen concludeert de pagina dat de verbeelding af is
  terwijl er nooit iets gemaakt is.
- **Afrekenen pas als het werk echt kan.** `/api/extra` controleerde alleen het
  saldo en of de achtergrondtaak *startte*; die taak faalde daarna en de tokens
  waren weg. Nu weigert hij met 409 als er geen panelen liggen om te animeren.
- **Wissen ruimt ook de bestanden op.** De nummering begint na het wissen weer bij
  1, dus als de panelen van de oude Droom 1 blijven staan, erft de nieuwe Droom 1
  ze — en dan zie je in je archief een droom met het beeld van een andere. Zowel
  `clear_archive()` als `delete_dream()` gaan langs `_ruim_nummer_op()`, en `create()`
  ruimt het nummer op dat hij gaat gebruiken. Wat niet met een cijfer begint,
  zoals `check.png`, blijft staan.
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
- **Beheer vraagt zijn sleutel in de pagina, niet met `window.prompt`.** Chrome
  onderdrukt zo'n dialoog zodra het tabblad de focus niet heeft, en hij lag
  onder Vera's introvenster. De kaart `#beheerpoort` ligt op z-index 140, boven
  alles, en zegt apart of de sleutel is afgekeurd of `ADMIN_TOKEN` helemaal niet
  in de omgeving staat.
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
- **Nooit `.env` committen.** `.gitignore` blokkeert ook `.env.*` en `data/`.
- Basic auth gaat aan zodra `AUTH_USER` én `AUTH_PASSWORD` gevuld zijn. **Twee
  paden staan er altijd buiten**: `/api/stripe/webhook`, want Stripe stuurt geen
  wachtwoord mee en dan slaat er stil nooit een pakket om terwijl de klant wél
  betaald heeft; en `/privacy.html`, want een privacyverklaring achter een
  wachtwoord beschermt niemand. Sinds er accounts zijn heb je basic auth
  overigens niet meer nodig: zonder inloggen komt niemand bij `/api` of
  `/panels`.

## De chakrapilaar

Hij staat op de pagina tussen *Je dromen samen* en *Je droomarchief*, en
verschijnt **vanaf de eerste droom**. Daar stond eerst een drempel van drie, met
het argument dat minder alleen ruis geeft. Dat klopte voor de tijdlijn maar niet
voor de pilaar: één droom is al vijf panelen met vijf gekozen velden, en dat is
een echte verdeling. De kosten van verbergen bleken hoger — wie hem niet ziet
weet niet dat hij bestaat, en dit is precies het deel waar mensen voor
terugkomen. Onder de drie nachten staat er een regel bij dat het nog vroeg is.


`static/chakra-pilaar.jpg` is een gegenereerde plaat: zeven lotussen in een
sterrenveld met de lichtbundel erdoorheen. Zelf zeven lotussen tekenen in SVG
kwam niet in de buurt, dus is de plaat vast en gaan de gegevens er als laagje
overheen: velden die weinig voorkwamen doven weg, velden die overheersten
blijven fel en krijgen hun percentage.

De zeven middelpunten zijn een keer uitgemeten en staan als `y` in `VELDEN` in
`static/app.js`, als fractie van de hoogte. **Vervang je de plaat, meet ze dan
opnieuw** — anders vallen de cijfers en de dovers naast de lotussen.

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
- **Het archief is een bestand op schijf** en dus weg bij elke Render-deploy. Voor
  iets echts hoort daar een database.
- **Geen betaling.** Pakket en tokensaldo staan in `data/profile.json` en worden
  met de hand gezet via `POST /api/account`. Dat eindpunt vraagt sinds
  2 september 2026 om de header `X-Admin-Token`, die moet kloppen met `ADMIN_TOKEN`
  uit de omgeving. Staat die niet gezet, dan kan aanpassen helemaal niet — dat is
  de veilige stand. In de app is er geen zichtbare beheerknop: zet
  `?beheer` achter het adres, vul de sleutel in de kaart in, en de knoppen én de
  kostenmeter verschijnen. De sleutel blijft daarna in `localStorage` van die ene
  browser staan, dus dat is eenmalig per browser, en met de knop **Beheer uit**
  gaat hij er weer af — anders blijven de kostenmeter, de webhooklog en de
  pakketknoppen voorgoed in beeld, ook als je de app gewoon als dromer gebruikt
  of hem aan iemand laat zien. Daar staat ook een veld
  **Tokensaldo**: dat *zet* een vast aantal (`{"saldo": 500}`), waar
  `{"tokens": 10}` optelt. Zetten moest erbij omdat optellen eerst vraagt wat er
  stond, en tussen die twee stappen kan een gesprek met Vera er een paar
  afhalen. Op Render is geen shell, dus zonder dat veld is "zet mij op 500
  tokens" niet te doen. Met **Voor wie** vul je het adres van een testpersoon in
  en zet je diens pakket of saldo zonder als hem in te loggen — anders had je
  zijn wachtwoord nodig. Dat pad zet alleen; er komt geen droom en geen duiding
  van een ander langs, en na afloop gaat de gebruikerslaag in een `finally`
  terug naar wie er echt aan de lijn is.
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
- **`static/privacy.html`** noemt de verwerkers met naam: Anthropic (de tekst),
  Kling (de panelen), Runway (beeld, stem en Vera), Stripe (het afrekenen) en
  Render (waar het draait). Verandert er een leverancier, dan verandert die
  pagina mee.

De betaalregels blijven na verwijdering staan zonder gebruiker: een bedrag, een
datum en een gebeurtenis-id. Dat is boekhouding en er staat niets persoonlijks
in.

## Afrekenen

Stripe **Managed Payments**: Stripe is de verkoper en draagt de btw af in ruim
tachtig landen. 5% + $0,50 per transactie, tegen ongeveer 1,5% + € 0,25 bij
gewoon Stripe — dat verschil koop je bewust, want zelf OSS-aangifte doen over
27 tarieven kost meer.

```bash
python betalen.py --check     # staat alles klaar?
python betalen.py --setup     # producten en prijzen aanmaken
```

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

**E-mailverificatie is gebouwd maar staat uit.** Er is een code per account en
een eindpunt om hem in te wisselen; versturen vraagt SMTP-gegevens die er niet
zijn. Zet `VERIFICATIE_NODIG=1` in de omgeving om het te eisen. Zolang het uit
staat wordt de code bij het aanmaken naar de log geschreven.

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
| Gratis | € 0 | **1** | ja, vijf getekende panelen | alleen met tokens |
| **Lite** | **€ 2,99** | **3** | ja, vijf getekende panelen | alleen met tokens |
| Plus | € 7,99 | 6 | ja, plus een bewegend kernmoment | alleen met tokens |
| Ultra | € 29,99 | 10 | ja, kernmoment op het beste model | 10 minuten inbegrepen |

Gratis geeft **één** droom en geen drie. Bij drie kostte een gratis gebruiker
€ 0,42 per maand, en vier van hen aten één betalende op; nu is dat € 0,14. Lite
kost € 2,99 en niet € 1,99, want bij een klein maandbedrag is de vaste $0,50
transactiekosten het probleem en niet het percentage — op € 1,99 is dat 23% van
de prijs. Drie dromen bij € 2,99 houdt 48% marge; bij € 1,99 was dat 33%.

Eén token is € 0,25. Een avatarminuut kost 2 tokens (kostprijs € 0,18), een extra
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
- Voordat er meer gebouwd wordt: tien testpersonen, drie dagen, en kijken wie op
  dag vier uit zichzelf terugkomt. Dat cijfer beslist of dit een bedrijf is.
