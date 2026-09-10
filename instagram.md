# @Veradreamverse

Wat er op het account komt, wat er nooit op komt, en waar je aan ziet of het
werkt. De techniek van het kanaal staat in `CLAUDE.md` onder *Van Instagram
naar de app*; dit gaat over de inhoud.

## Eén doel, en het is geen volgersaantal

Het cijfer dat telt is dat van `python rapport.py`: **wie komt er op dag vier
uit zichzelf terug**. Alles daarvoor is een trechter — bezoek, account, eerste
droom — en Instagram is er alleen om de bovenkant van die trechter te vullen.

Dus: een post die duizend keer geliked wordt en niemand naar `?van=ig-bio`
stuurt, heeft niets gedaan. Een post die vijf mensen naar de app brengt en er
één een droom laat vertellen, wel. Dat is ook waarom er geen volgersdoel in dit
stuk staat: dat getal is niet het product.

## Wat er al klaarligt

| Wat | Waar | Let op |
|---|---|---|
| Vier bewegende kernmomenten | `static/voorbeelden/*.mp4` | 720 × 407, dus **liggend** |
| Panelen uit het archief | `data/panels/` (op deze machine) | 1360 × 768, ook liggend |
| 27 gidsartikelen | `knowledge/droomgids/` | elk drie brillen + vragen |
| De chakrapilaar | `static/chakra-pilaar.jpg` | staand, 576 × 1008 |
| Vera zelf | `static/vera.png`, `vera-intro-nl.mp4` | een gezicht dat niet van een derde is |
| Het beeld bij een link | `static/og-beeld.jpg` | 1200 × 630, uit `build/og_beeld.py` |
| 27 gidsbeelden | `static/gids/` | 1200 × 678, dus ook liggend |

**Alles wat de app maakt is liggend, en Instagram is staand.** Panelen komen als
16:9 uit Kling (`submit(prompt, aspect_ratio="16:9")`) en de animaties nemen die
verhouding over. Een Reel of een verhaal is 9:16. Zet je een liggend beeld
zomaar in een Reel, dan staat het als een postzegel in het midden met twee
zwarte balken, en dat leest als een geleend plaatje in plaats van als een
product.

De DreamCard lost dat al op: donkere grond, het beeld in een kader in het
midden, tekst erboven. **Voor de gidsbeelden doet `build/reels.py` nu hetzelfde**
— staand, met een langzame zoom eroverheen, en de onderste 420 pixels leeg voor
de bediening van Instagram.

Wat er nog niet in zit is de **bewegende** bron: een kernmoment uit het archief
is al video, en die in dezelfde vorm zetten is een andere ingreep. Tot dat er is:
één donkere staande achtergrond in Canva, clip in het midden, en boven en onder
ruimte laten — dezelfde maat en om dezelfde reden als bij de kaart.

## De harde grenzen

Dit zijn niet mijn regels maar die van de app zelf. Een caption is precies zo
veel een uitspraak als een duiding, en op Instagram staat hij voor iedereen.

- **Nooit iemand anders zijn droom.** Ook niet anoniem, ook niet als iemand hem
  in een DM stuurt en het "leuk" vindt. De DreamCard draagt met opzet geen
  droomtekst; het account houdt diezelfde lijn. Wat je post is je eigen droom
  of niets. Wil je er ooit een van een gebruiker bij, dan is dat schriftelijke
  toestemming per droom, en dan nog zonder de duiding.
- **Nooit een voorspelling.** Geen "deze droom betekent dat er iets op je
  afkomt". Dezelfde reden als in de app: het is vermaak, en de kop erboven zegt
  dat ook. *Waar deze droom je aandacht op kan vestigen* — niet iets om op te
  wachten.
- **Nooit een claim over gezondheid, ziekte, geld, zwangerschap of iemands
  dood.** Ook niet als vraag ("Droomde jij ooit dat je tanden uitvielen vlak
  voordat je ziek werd?"). Dat is precies de post die iemand echte angst
  bezorgt, en je kunt het niet terugnemen.
  **Het onderwerp mag wel, de claim niet** — en dat verschil is sinds
  10 september scherp, want de gids heeft nu pagina's over *pregnancy*, *dying*
  en *deceased-person*. Die bestaan omdat iemand 's ochtends precies dat
  intikt, en ze doen het door de ontkenning in de **eerste zin** te zetten:
  *"not a sign that you are, and not a sign that you will be"*. Post je een van
  die drie, dan staat die ontkenning in de **eerste regels** van de caption en
  niet ergens achteraan. `build/reels.py` doet dat vanzelf — het neemt minstens
  twee zinnen van de opening mee, juist omdat bij *dying* de ontkenning in de
  tweede zin staat. Nagemeten op beide. Wat je zelf typt valt daarbuiten: iemand
  die alleen de eerste twee regels leest mag nooit de indruk overhouden dat een
  droom iets voorspelt over een lichaam.
- **Geen droomwoordenboek.** "Water staat voor emotie" kan iedereen opzoeken en
  is bij deze dromer misschien niet eens waar. De gids doet het goed: dit is wat
  tradities en de psychologie erover zeggen, en dan de vraag die het persoonlijk
  maakt. Neem die vorm over.
- **Geen duidingen in de comments of DM's.** Dat is het betaalde product, het is
  werk zonder bodem, en het is een duiding zonder de geschiedenis die haar goed
  maakt. Antwoord: leuk dat je het vertelt — vertel het aan Vera, zij leest de
  droom.
- **Geen religieuze of politieke tekens in het beeld.** Staat al in
  `NEGATIVE` in `kling.py` en geldt hier net zo hard.

## Drie soorten posts, en niets anders

**1. Het kernmoment (Reel).** Tien seconden droom die beweegt, in de staande
kaartvorm, met één regel eronder. Dit is het enige wat het verschil tussen
"vijf tekeningen" en "vijf tekeningen plus een bewegend kernmoment" laat zien —
dat kun je niet uitleggen, dat moet je laten zien. Caption: wat er te zien is,
niet wat het betekent. Geen duiding onder een Reel.

**2. Het gidsonderwerp (Reel).** Dit is de motor van het account geworden, en
het is nu een script: `python build/reels.py --ja` maakt van alle zevenentwintig
onderwerpen een staande video van acht seconden met de titel erboven, het
gidsbeeld met een langzame zoom, de vraag eronder en de weg naar de gids
onderaan — plus een caption met een uittreksel uit het artikel en de hashtags.
Klaar om te plaatsen, op het muziekje na: dat kies je in Instagram zelf, want
die bibliotheek mag alleen daar gebruikt worden. Zie *Van de gids naar een Reel*
in `CLAUDE.md` voor wat er in dat script vastligt.

**Besloten op 10 september 2026: een carrousel was het plan, een Reel is het
geworden.** Dezelfde inhoud, maar een carrousel van vier platen is handwerk per
stuk en een Reel rolt uit een script. Bereik ligt bij Instagram bovendien bij
video, en de drie brillen passen prima in de caption in plaats van op losse
platen.

De link in de caption is niet aanklikbaar — dat kan bij Instagram alleen vanuit
je bio of met een sticker in een verhaal. Het adres staat er dus wel, met "link
in bio" erachter. **Zolang deze reeks loopt hoort de bio-link naar
`/dream-meaning/?van=ig-bio` te wijzen** en niet naar de landingspagina: dan
komt iemand precies waar de Reel over ging.

**3. Eén paneel, één regel.** Een still uit het archief, in de kaartvorm, met
één zin. Geen uitleg, geen vraag, geen link. Dit is het beeldmerk: iemand die
drie keer langs zo'n plaat scrollt weet daarna hoe een Dreamverse-beeld eruit
ziet.

Wat er **niet** bij hoort: tips over slapen, quotes over dromen, carrousels met
"7 dingen die je niet wist over…", en alles wat een ander account ook had kunnen
posten. Het enige wat dit account heeft en niemand anders, is de verbeelding.

## Cadans

**Besloten op 10 september 2026: elke dag één, en niet drie keer per week.**
Hier stond drie per week, met het argument dat dagelijks niet te volhouden is
zonder vulling te gaan posten. Dat argument is weg nu de Reels uit een script
komen: er staan zevenentwintig klaar, dus er valt vier weken niets te bedenken
en niets op te rekken.

Twee dingen om in de gaten te houden. **Na die zevenentwintig is de voorraad
op** — dan is het een nieuw onderwerp schrijven (twee teksten plus een prompt)
of stoppen met dagelijks; op de dag dat de laatste geplaatst is, is het te laat
om daar over na te denken. En **de vragen onder een Reel blijven werk**: wie
dagelijks post en niet antwoordt, post tegen een muur. Dat is de tijd die
dagelijks posten wél kost.

Verhalen wel vaker, maar alleen als er iets is: een nieuw kernmoment, een
gidsonderwerp erbij, iets dat misging. Met een **linksticker naar
`?van=ig-story`**, dan zie je het terug in het rapport.

## De eerste tien

Alles hieronder kan met wat er nu op schijf staat.

| # | Soort | Wat |
|---|---|---|
| 1 | Still | De vuurvogel, met: *This was a dream. Someone told it, and got it back like this.* |
| 2 | Reel | De vuurvogel die beweegt, in de kaartvorm |
| 3 | Carrousel | `being-chased` — de meest gedroomde droom die er is |
| 4 | Still | De zee die rechtop staat |
| 5 | Carrousel | `teeth-falling-out` — let op de grens: geen woord over ziekte |
| 6 | Reel | De zee, bewegend |
| 7 | Still | De chakrapilaar, met wat de kleurvelden zijn |
| 8 | Carrousel | `falling` |
| 9 | Reel | De beker op het gras |
| 10 | Vera | Vera die zich voorstelt (`vera-intro-nl.mp4`), Engels ondertiteld |

Na tien posts weet je twee dingen die je nu niet weet: welke van de drie soorten
iets naar de app stuurt, en of de gidsonderwerpen mensen trekken die geen droom
willen bewaren. Stel daar de verhouding op bij, niet op likes.

## Bio en links

Naar buiten heet het **Vera Dreamverse** — dezelfde naam als het domein en
dezelfde naam als in de `<title>` van de pagina's. In de app zelf blijft
Dreamverse staan; dat hoeft niet mee te veranderen.

Bio, Engels, want de landingspagina en de gids zijn dat ook:

> Tell your dream in the morning. Get it back as five panels, a reading, and a
> look ahead. Every earlier dream counts.
> vera-dreamverse.com

De link in de bio: `https://vera-dreamverse.com/?van=ig-bio`. In verhalen
`?van=ig-story`, bij een Reel-caption `?van=ig-reel`. Alleen die woorden worden
geteld (`HERKOMST` in `accounts.py`); iets anders erachter zetten levert geen
regel op. Wie de tag vergeet wordt trouwens nog steeds als `ig-app` geteld op de
browsernaam, dus je verliest het bezoek niet — alleen het onderscheid tussen bio
en verhaal.

**Captions in het Engels.** De gids is Engels-eerst omdat de zoekvraag daar
vele malen groter is, de landingspagina heeft Engels als standaard, en het og-
beeld is Engels. Eén taal op het account houdt dat consequent. Dat kost niets
aan de Nederlandse kant: de app kiest zijn taal op de browser, dus een
Nederlandse bezoeker krijgt nog steeds een Nederlandse duiding. Voor je eigen
kring zijn er verhalen, en die mogen Nederlands zijn.

## Wat het kost

Een still uit het archief kost niets — die is al getekend en betaald. Een nieuw
paneel is € 0,014. Een **nieuwe** animatie bij Runway is € 0,55 tot € 1,47, en
dat is de enige post-soort die echt geld kost: drie Reels per maand van nieuw
werk is € 2 tot € 4,50. Doe dat dus met wat er al ligt zolang dat er is — er
staan vier animaties op schijf en meer in het archief.

**Het Kling-tegoed verloopt 18 september 2026.** Het eerste van de twee dingen
die dat waard waren is op 10 september gedaan, en meteen helemaal: alle
**zevenentwintig** gidsonderwerpen hebben een beeld
(`python build/gids_beelden.py --ja`, vier eenheden per stuk, dus 108). Wat er
nog ligt is een reeks stills in de kaartvorm voor het account zelf. Wat er op
19 september over is, is weg.

## Waar je aan ziet of het werkt

    python rapport.py

Twee blokken. **WAAR ZE VANDAAN KWAMEN** zegt of er iemand van Instagram kwam;
**DE TRECHTER** zegt wat er daarna gebeurde. De regel eronder — van zoveel
bezoeken werden er zoveel een account — is het enige percentage dat over
Instagram iets zegt.

Wat er níet in staat is klikgedrag: waar mensen in de app klikken en waar ze
afhaken wordt met opzet niet gemeten, want dat vraagt een meetscript en dat
levert een cookiebanner op. Wil je weten waarom iemand wegbleef, dan is er één
kanaal: het kaartje *Wat kan er beter?* na de eerste verbeelding. Dat staat
onderaan het rapport.

Instagram's eigen cijfers (bereik, opgeslagen, doorgestuurd) zijn goed voor één
ding: zien welke van de drie soorten posts mensen bewaren. Ze zeggen niets over
of er iemand terugkomt op dag vier.

## De vijf prompts van @iknowig, toegepast

Vijf rollen: een groei-analist, een openingsregel-schrijver, een carrousel- en
Reel-bouwer, een retentie-editor en een positioneringsstrateeg. Ze zijn hieronder
op dit account uitgevoerd. Eén ervan legde een echte fout in de app bloot; die
staat onderaan.

Wat er níet uit overgenomen is, staat in *Waar deze prompts tegen de regels van
de app duwen* — helemaal onderaan. Lees dat eerst als je haast hebt.

### 1. De audit — drie patronen die dit account onzichtbaar houden

Dit is een audit van het plan hierboven, niet van een tijdlijn: wat er nu op het
account staat kan ik niet zien. Staan er al posts, dan hoort deze audit opnieuw
te gebeuren met die posts erbij.

**Patroon 1: alle drie de postsoorten geven een reden om te liken, geen reden om
te volgen.** Een still is mooi, een Reel is mooi, een carrousel is nuttig — en
alle drie zijn af op het moment dat je ze uit hebt. Er is niets dat pas in de
volgende post rondkomt. Dat is opvallend, want dít product is het enige in zijn
niche dat over continuïteit gaat: terugkerende plaatsen en personen die na een
paar maanden één wereld worden. De app verkoopt een reeks en het account post
losse plaatjes.

Wat eraan te doen is: **één doorlopende reeks, en dat is je eigen archief.**
*Night 6: the burning bird.* *Night 7: the sea stood upright.* *Night 12: the
cup on the grass.* Genummerd, in volgorde, uit één dromer — jij. Wie de derde
tegenkomt begrijpt dat er een eerste en een tweede zijn, en dat er een vierde
komt. Dat is de reden om te volgen, en het is precies wat het product belooft.
Bijkomend voordeel: het is jouw droom, dus het valt buiten elk bezwaar over
andermans dromen.

**Patroon 2: de gidscarrousel eindigt bij het antwoord.** Vijf platen die de drie
brillen netjes uitleggen zijn compleet, en compleet betekent: bewaren en weg.
Het artikel doet het beter dan de carrousel — dat eindigt op *The details change
everything*. Zet die kant op de laatste plaat, niet de samenvatting.

**Patroon 3: er is geen stem.** Het plan hierboven post beelden en teksten maar
niemand zegt ze. Er staan twee stemmen klaar: Vera (er is een persona, een
portret en een video) en jij. Een account zonder verteller is in deze niche een
beeldbank. **Vera is de verteller** — één stem, herkenbaar, en ze bestaat al op
schrift in `persona/vera.txt`. Jij bent de tweede stem, maar alleen in verhalen
en alleen als er iets echt gebeurt.

### 2. Twaalf openingsregels

Idee: *je dromen herhalen zich, en dat kun je van binnenuit één nacht niet zien.*
Publiek: mensen die hun dromen onthouden en er nooit iets mee doen. Toon: stil en
precies, geen goeroe.

*Onmiddellijke spanning*

1. You have had this dream before. You met it in a different house.
2. The thing chasing you has kept the same shape for years.
3. That room came back last night. It was the fourth time.

*Tegen de intuïtie in*

4. What was chasing you does not matter. Whether you turned around does.
5. A dream dictionary cannot read your dream. Your other dreams can.
6. Forgetting your dreams is not the problem. Having nowhere to put them is.

*Het precieze gevoel van één persoon*

7. You wake with your heart going and about thirty seconds to decide whether
   that was worth keeping.
8. You start telling someone your dream and hear yourself making it smaller as
   you go.
9. You know it meant something. You also know that saying so out loud sounds
   ridiculous.

*Een lus die je niet dicht kunt laten*

10. This is the third night that house has come back. I am going to show you all
    three.
11. I asked what runs through ninety nights of my own dreams. One answer I did
    not expect.
12. There is one detail in a chase dream that changes the whole reading, and
    almost nobody mentions it.

Regel 10 en 11 mogen alleen als ze **waar** zijn. Een lus openen over een reeks
die niet bestaat is dezelfde fout als een verzonnen patroon op de kaart *Vera zag
iets*: het werkt één keer en daarna is het onderdeel ongeloofwaardig.

### 3. Carrousel van zeven, en een Reel zonder gezicht

Onderwerp: `being-chased`. De tekst komt uit het artikel dat er al staat, dus
hier wordt niets nieuws beweerd.

**De platen, exact wat er op staat:**

1. Everyone asks what was chasing them.
2. The more useful question is whether you ever turned around.
3. **PSYCHOLOGICAL** — Avoidance. Something being outrun instead of dealt with.
   What people remember afterwards is rarely the pursuer. It is what they did.
4. **SYMBOLIC** — The pursuer often stands for something inside rather than
   outside. An urge. A fear. A part of you you would rather not meet.
5. **SPIRITUAL** — Some traditions read the chase as a summons, not a threat.
   Something that keeps following until it is acknowledged.
6. Dreamers who turn around usually report that the dream changed at that
   moment. Sometimes it shrank. Sometimes it was someone familiar.
7. Being chased through a house you know is not the same dream as being chased
   through nowhere. **So what was actually behind you — and did you look?**

Caption: de openingsregel, dan de zeven vragen uit `details` als losse regels,
dan de link. Geen samenvatting in de caption: die staat op de platen.

**Het Reel-script (tekst op beeld, geen gezicht):**

| Tijd | Beeld | Tekst | Regie |
|---|---|---|---|
| 0–2 s | paneel, stil | Everyone asks what was chasing them. | begin op een stilstaand beeld; beweging pas als de tekst gelezen is |
| 2–5 s | de animatie start | The more useful question: | het kernmoment gaat lopen op het woord *question* |
| 5–8 s | animatie loopt | did you ever turn around? | tekst blijft staan tot het eind van de beweging |
| 8–11 s | volgend paneel | Dreamers who turn around say the dream changed right there. | één harde overgang, geen crossfade |
| 11–14 s | laatste paneel, stil | Sometimes it shrank. Sometimes it was someone they knew. | |
| 14–16 s | zwart met merk | What was behind you? | VERA DREAMVERSE, en verder niets |

**Geen trending audio, en dat hoeft ook niet:** de Runway-animaties komen met een
eigen geluidsspoor (dat is nou juist waarom Runway boven Kling gekozen is — 1,1 MB
mét geluid tegen 12,9 MB zonder). Dat geluid is van deze droom en van niemand
anders. Het is ook het enige waar dit account audio van heeft, dus behandel het
als bezit en niet als bijzaak.

**Wat ik van deze prompt níet overneem:** "faceless". Vera is het enige gezicht
dat we mogen gebruiken en het is er een die niets kost en niemand toebehoort. Een
account dat een gezicht heeft en het wegstopt gooit zijn eigen voorsprong weg.
Tekst-op-beeld-Reels zonder gezicht: ja. Een account zonder gezicht: nee.

### 4. De retentie-editor, op het scherm dat er echt staat

De nuttigste plek voor deze prompt is niet een caption maar **het eerste scherm
na de bio-link**. Daar valt iemand af of niet, en de post ervoor was gratis.

De poort heeft twee stappen, en `poortStap()` wisselt de kop: op de eerste staat
de belofte en is `.poort-sub` verborgen, op de tweede precies omgekeerd. Dit is
de Engelse tekst zoals hij er nu staat.

**Stap 1, de droom:**

> **Dreamverse**
> Tonight is one dream. After three nights your Dreamverse begins.
> **What did you dream last night?**
> [invoerveld] Speak it in · or type it above · Continue
> Your dream stays in this browser for now and goes nowhere. Already have an
> account? Log in

**Stap 2, het account** — pas als de droom er staat:

> **Dreamverse**
> You tell your dream; you get an imagining with a reading and a look ahead.
> Every earlier dream counts.
> Your dream is ready for Vera.
> Create a free account to see it imagined. Three dreams a month, no payment
> details.

Waar iemand wegklikt, en waarom:

- **"Tonight is one dream."** Hier stopt het. Iemand komt om 7 uur 's ochtends
  met een droom van vannacht, en de eerste regel gaat over vanavond. Dit is geen
  toon maar een fout: *vannacht* is in het Nederlands terug én vooruit, en de
  vertaling koos vooruit. Twee regels lager staat *What did you dream last
  night?*, dus de pagina spreekt zichzelf tegen. **Zie de reparatie onderaan.**
- **"you get an imagining"** staat op stap 2, en dat is de zwaarste plek die er
  is: dit is de zin die een account moet waard zijn. Het woord bestaat zo in het
  Engels niet. `welkom.html` zegt precies hetzelfde veel beter: *get it back as
  five panels, a reading and a look ahead*. Vijf panelen is concreet en telbaar;
  *an imagining* moet je uitleggen, en uitleggen is waar iemand wegklikt.
  Voorstel: **"Tell it, and get it back as five panels, a reading and a look
  ahead. Every earlier dream counts."**
- **De puntkomma in diezelfde zin.** Op een telefoon is dat een rem in een zin
  van veertien woorden. Twee zinnen zijn hier sneller dan één.
- **Stap 1 zegt niet wat je terugkrijgt.** Nu de sub daar verborgen is, staat er
  op het scherm waar iemand van Instagram landt alléén *After three nights your
  Dreamverse begins* — een belofte over de derde nacht, terwijl hij zich afvraagt
  wat er ná deze ene gebeurt. Dat is met opzet zo (twee koppen boven elkaar is
  erger), maar de belofte mag dan wel het eerste noemen: **"One night is five
  panels and a reading. After three, your Dreamverse begins."** Dat is één regel
  en hij zegt allebei.
- **"and goes nowhere"** — bedoeld is: het wordt nergens naartoe gestuurd.
  Gelezen kan worden: het leidt tot niets. Precies op de plek waar iemand een
  droom gaat intypen die hij aan niemand vertelt, is die dubbelheid duur.
  Voorstel: **"Your dream stays on this device until you make an account. It is
  not sent anywhere."**

Herschreven, met de spanning die elke regel de volgende in trekt:

> **Dreamverse**
> One night is five panels and a reading. After three, your Dreamverse begins.
> **What did you dream last night?**
> [invoerveld] Speak it in · or type it above · Continue
> Your dream stays on this device until you make an account. It is not sent
> anywhere.

En stap 2:

> **Dreamverse**
> Tell it, and get it back as five panels, a reading and a look ahead. Every
> earlier dream counts.
> Your dream is ready for Vera.
> Create a free account to see it. Three dreams a month, no payment details.

**Dit is allemaal doorgevoerd**, op 10 september 2026, en nagemeten in beide
talen op beide stappen. Twee dingen om te weten bij wat er wél en niet
veranderd is:

- **De belofte is in het Nederlands óók veranderd**, want daar ging het niet om
  een vertaling maar om wat de regel zegt: *Eén nacht is vijf panelen en een
  duiding.* Vijf panelen is telbaar, "je Dreamverse" niet, en op een gratis
  eerste droom is het waar (`GRATIS_MET_BEELD = 1`).
- **De rest is alleen aan de Engelse kant veranderd.** *Verbeelding* is in het
  Nederlands het woord van het product en werkt; *an imagining* bestaat in het
  Engels zo niet. Hetzelfde bij *goes nowhere*, dat te lezen was als "het leidt
  tot niets" terwijl bedoeld is dat hij niet verstuurd wordt. Het Nederlands
  was daar in orde en is dus niet aangeraakt.

### 5. Positionering — drie versies van de bio

*Door precisie:*

> Five panels, a reading and a look ahead, from the dream you tell in the
> morning. Dream 1 stands alone. From dream 3 the recurring places start
> showing up. vera-dreamverse.com

*Door zelfverzekerde eenvoud:*

> Tell your dream. See it. Keep it.
> vera-dreamverse.com

*Door een standpunt waar je het mee oneens kunt zijn:*

> Dream dictionaries read symbols. We read yours — against every night you have
> told us. Water does not mean emotion. It means what it keeps doing in your
> dreams. vera-dreamverse.com

De derde is de sterkste en de enige die iets riskeert, en hij is waar: het is
letterlijk de regel die in de prompt van de app staat. De tweede is de veiligste
en zegt het minst. Kies de derde als je één ding wil zijn in plaats van nog een
droomapp.

### Waar deze prompts tegen de regels van de app duwen

Vier van de vijf vragen om spanning, en spanning is bij dromen één stap van
angst.

- **"Immediate tension" mag nooit het angstregister worden.** Geen post over
  gezondheid, ziekte, geld, zwangerschap of iemands dood — ook niet als vraag,
  ook niet als grap. De spanning moet uit nieuwsgierigheid naar je eigen nacht
  komen, nooit uit dreiging. Dat is dezelfde regel die de vooruitblik in de app
  begrenst, en `being-chased` doet het onder de FAQ zelf voor: *Does being chased
  in a dream mean I am in danger? No.*
- **"Counterintuitive claim" mag geen claim worden die we niet kunnen dragen.**
  "Dromen voorspellen" is geen prikkelende stelling maar een onwaarheid, en één
  post is genoeg om alles wat de app zorgvuldig níet belooft te ondergraven.
- **"A loop the reader cannot close" is inhoud, geen vooruitblik.** In een post
  mag je iets openhouden. In de app niet: daar is de vooruitblik vermaak en geen
  voorspelling, en de kop erboven zegt dat ook.
- **"Faceless" past hier niet.** Zie hierboven.

Wat er wél uit deze vijf te halen is, staat in de audit: **een reden om te
volgen in plaats van te liken.** Dat is de enige van de vijf die een echt gat in
het plan aanwijst, en het antwoord erop is de genummerde reeks uit je eigen
archief.

## Wat hier nog niet is

- ~~De staande kaartvorm bestaat alleen in de app.~~ **Gedaan op 10 september
  voor een stilstaand beeld:** `build/reels.py` zet een gidsbeeld in de staande
  vorm met een zoom eroverheen, en levert de caption erbij. **Wat er nog niet is,
  is de bewegende bron** — een kernmoment uit het archief is al video, en dat in
  dezelfde vorm zetten is een andere ingreep dan een still inzoomen. Tot die er
  is blijft dat handwerk in Canva. En de video's staan in `data/reels/`, dat is
  git-ignored: 27 stuks is 21 MB en die horen niet in de repo, dus ze staan
  alleen op de machine die ze maakte en moeten naar je telefoon om geplaatst te
  worden.
- ~~Geen enkel gidsonderwerp heeft een eigen beeld.~~ **Gedaan op 10 september.**
  Alle zevenentwintig hebben er een, dus een gedeelde gidspagina laat zijn eigen
  beeld zien in plaats van zevenentwintig keer dezelfde vuurvogel in een
  tijdlijn. Het vaste og-beeld dekt nu alleen de overzichtspagina en de app.
  Voor Instagram is dat beeld meteen plaat 1 van de carrousel bij dat onderwerp
  — mits het door de kaartvorm gaat, want ze zijn liggend (1200 × 678).
- **Merknaam niet nagekeken.** Er staat sinds juni 2026 een app *The DreamVerse*
  in de App Store. *Vera Dreamverse* is de veiliger naam en staat al op het
  domein en op het account, maar een echte check bij BOIP, EUIPO en USPTO is
  niet gedaan. Zolang dat zo is: geen geld in advertenties, en geen naam op
  gedrukt materiaal.
- ~~De gids staat op negen onderwerpen.~~ **Zevenentwintig, sinds 10 september,
  allemaal met beeld.** Daarmee is de vraag hoeveel er nog komen ook weg: de
  achttien die `CLAUDE.md` noemde zijn er. Er liggen dus **27 carrousels** klaar
  waarvan de tekst al geschreven is, en dat is negen weken inhoud op één
  carrousel per week. Als er iets níet meer ingehaald hoeft te worden, is het
  dit. Een volgend onderwerp is nog steeds twee teksten (Engels en Nederlands)
  plus een prompt in `PROMPTS` in `build/gids_beelden.py`.
