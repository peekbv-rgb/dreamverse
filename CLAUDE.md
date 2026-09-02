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
POST   /api/episode   {"dream": "...", "quality": "duiding|eenvoudig|standaard|supreme"}
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
- **Nooit `.env` committen.** `.gitignore` blokkeert ook `.env.*` en `data/`.
- Basic auth gaat aan zodra `AUTH_USER` én `AUTH_PASSWORD` gevuld zijn.

## De chakrapilaar

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
  de veilige stand. In de app zie je de knoppen alleen na *beheer* en het invoeren
  van die sleutel; hij blijft daarna in `localStorage` van die ene browser.
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
- Het gesprek levert nog geen droomtekst op. De logische volgende stap: wat Vera
  hoort wordt de invoer voor de verbeelding, zodat vertellen en krijgen één geheel
  worden in plaats van twee losse dingen.
- Voordat er meer gebouwd wordt: tien testpersonen, drie dagen, en kijken wie op
  dag vier uit zichzelf terugkomt. Dat cijfer beslist of dit een bedrijf is.
