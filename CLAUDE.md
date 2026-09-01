# Dreamverse

Je vertelt 's ochtends je droom; je krijgt een aflevering van vijf panelen met een
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

Het voorstel ernaast — elke dag een aflevering over je parallelle leven — sneuvelt
op de kosten: 45 seconden gegenereerde video maal dertig dagen is €40 tot €160 per
abonnee per maand, tegen €8,99 omzet. Dreamverse ontsnapt daaraan om vier redenen:
dromen zijn zelfbeperkend (vijf tot tien per maand), de gebreken van AI-beeld zijn
bij een droom een kenmerk in plaats van een bug, de invoer komt van de gebruiker,
en er is geen gezicht van een derde nodig.

Kostprijs per aflevering als motion comic: ongeveer **€0,35**. Bij €8,99 en zes
dromen per maand is dat 66% marge. Het rekenmodel staat in de artefacten van de
sessie van 1 september 2026.

## Stack

Python 3.14, standaardbibliotheek `http.server`, statische frontend, Anthropic SDK.
Geen framework — dat houdt de deploy op één bestand, net als de andere projecten hier.

| Onderdeel | Waar |
|---|---|
| Afleveringen schrijven, archief, prompt | `dreamverse.py` |
| Panelen als illustraties (optioneel) | `kling.py` |
| HTTP en routes | `server.py` |
| Speler, invoer, spraak | `static/` |
| Persona van de gids | `persona/vera.txt` |
| Droomarchief (git-ignored) | `data/archive.json` |
| Deploy | `render.yaml` |

```
POST   /api/episode   {"dream": "..."}  -> de aflevering
GET    /api/archive                     -> alle eerdere dromen
DELETE /api/archive                     -> archief wissen
GET    /api/panels/<nr>                 -> stand van het tekenwerk
GET    /panels/<bestand>.jpg            -> een gegenereerd paneel
GET    /api/health                      -> {"ok": true, "key": bool, "kling": bool}
```

## Draaien

```bash
pip install -r requirements.txt && python server.py
```

Dan `http://127.0.0.1:8000`. **Zonder `ANTHROPIC_API_KEY` draait alles behalve het
schrijven**: elke droom geeft dezelfde voorbeeldaflevering terug, met `demo: true`.
Zo is de app te demonstreren zonder een cent aan tokens.

Model: `claude-opus-5` op effort `medium`. Schrijfwerk heeft geen hoge effort nodig
en het scheelt direct in de kostprijs per aflevering.

## Regels die er al in zitten

- **De vooruitblik is vermaak, geen voorspelling.** Nooit over gezondheid, ziekte,
  geld, zwangerschap of iemands dood. Dat staat in `RULES` in `dreamverse.py` en
  hoort daar te blijven: een app die zegt "let op je hart" bezorgt mensen echte
  angst en je kunt het niet terugnemen.
- **Altijd positief duiden, maar niet wegwuiven.** Bij geweld, verlies of een
  overledene eerst erkennen, dan pas het licht zoeken.
- **De kleurvelden zijn de chakra's** (`root` tot `crown`). Dat is geen sfeer maar
  betekenis: het model kiest per paneel het veld dat bij het gevoel past, en de
  kijker ziet die keuze terug in de kleur van het beeld.
- **Nooit `.env` committen.** `.gitignore` blokkeert ook `.env.*` en `data/`.
- Basic auth gaat aan zodra `AUTH_USER` én `AUTH_PASSWORD` gevuld zijn.

## Wat er nog niet is

- **Kling is aangesloten maar niet getest tegen de echte API** — er was hier geen
  sleutel. De client in `kling.py` is geschreven op de publieke documentatie.
  Zet `KLING_ACCESS_KEY` en `KLING_SECRET_KEY` in `.env` en draai eerst
  `python kling.py --check`: die maakt één afbeelding en drukt alles af wat
  terugkomt. Klopt een veldnaam niet, dan zie je precies welke. Zonder sleutels
  blijven de getekende composities staan; dat is geen storing maar het ontwerp.
- **Vera heeft nog geen gezicht.** Ze praat nu met de stem van de browser
  (`speechSynthesis`), en inspreken gaat via `SpeechRecognition` — dat werkt in
  Chrome en Edge, niet in Safari of Firefox. De pratende avatar is de Ultra-laag
  (€17,99) en vraagt een Runway-personage, een stem en een sessiebudget. De
  koppeling gaat zoals in `AI/Projects/peek-avatar/app`: de server maakt de
  realtime sessie en geeft alleen kortlevende WebRTC-gegevens aan de browser.
- **Het archief is een bestand op schijf** en dus weg bij elke Render-deploy. Voor
  iets echts hoort daar een database.
- **Geen accounts en geen betaling.** De prijslagen staan alleen als tekst in de UI.

## Open punten

- Wat kost een minuut pratende avatar werkelijk? Dat getal ontbreekt en bepaalt of
  de Ultra-laag op €17,99 uitkomt.
- Voordat er meer gebouwd wordt: tien testpersonen, drie dagen, en kijken wie op
  dag vier uit zichzelf terugkomt. Dat cijfer beslist of dit een bedrijf is.
