# Live gaan bij Stripe

Alles wat Managed Payments vraagt, op één plek. Wat hier staat is uit het
project gehaald en klopt met wat er op `welkom.html` staat — en dat moet zo
blijven, want een beoordelaar legt die twee naast elkaar.

**Log zelf in en vul dit zelf in.** Claude kan geen bedrijfsgegevens,
bankrekening of identiteitsbewijs invoeren, en hoort dat ook niet te doen.

## 1. Bedrijfsprofiel

| Veld | Wat er in moet |
|---|---|
| Rechtsvorm | Besloten vennootschap (B.V.) |
| Statutaire naam | Technische Handelsonderneming Peek B.V. |
| Adres | De Ring 30, 5261 LM Vught, Nederland |
| KvK | 18030812 |
| Contact | ruud.peek@peekbv.nl |
| Website | https://vera-dreamverse.com |
| Branche | Software / SaaS (digitale dienst, geen fysieke goederen) |

De SBI-code voor softwareontwikkeling is op 7 september 2026 aan de inschrijving
toegevoegd. Dat was precies hiervoor: tot dan stond er alleen een
installatiebedrijf, en dan rijmt het bedrijfsprofiel niet met wat je verkoopt.

## 2. Wat je verkoopt

Zo'n omschrijving wordt echt gelezen. Deze kun je overnemen:

> Dreamverse turns a written or spoken dream into a five-panel illustrated
> reading. The user tells their dream in the morning; a language model writes an
> interpretation and a light-hearted look ahead, and five illustrations are
> generated. Earlier dreams are taken into account, so recurring people, places
> and symbols build into one connected dream world over time. Sold as a monthly
> subscription (EUR 2.99 to EUR 29.99) with optional one-off token purchases for
> extras such as an animated key moment or a conversation with the guide.
> Delivered instantly in the browser. Digital service, no physical goods.

Verwachte transactiegrootte: EUR 2,99 tot EUR 29,99 per maand, plus losse
aankopen van EUR 7 tot EUR 25. Levering: direct, digitaal.

## 3. Wat je NIET met de hand aanmaakt

**Maak geen producten of prijzen in het dashboard.** Doe dat met

    python betalen.py --setup

Twee dingen gaan met de hand bijna altijd mis, en allebei kosten ze geld:
`tax_behavior` moet `inclusive` zijn — anders telt Stripe de btw bóven op je
prijs en rekent een klant bij EUR 2,99 straks EUR 3,62 af — en de belastingcode
moet `txcd_10105001` zijn, want Managed Payments accepteert alleen codes uit een
vaste lijst.

## 4. De volgorde, en waarom die uitmaakt

Live is bij Stripe een aparte wereld: elk product, elke prijs en elke webhook
bestaat daar opnieuw. De zes `price_...`-id's die nu in Render staan zijn
sandbox-id's en bestaan live niet.

Er is dus een moment waarop de app een live sleutel heeft en nog
sandbox-prijzen. Dan is afrekenen stuk. Daarom gaan alle acht waarden in één
keer naar Render, aan het eind:

1. Activatie afronden en wachten tot Stripe akkoord is.
2. Live secret key maken, in `.env` zetten (vervang de `sk_test_`-regel).
3. `python betalen.py --setup` — maakt zes live producten en prijzen.
4. Webhook aanmaken in **live**: `https://vera-dreamverse.com/api/stripe/webhook`,
   gebeurtenis `checkout.session.completed`. Kopieer het ondertekengeheim.
   Elke endpoint heeft zijn eigen geheim en aan het geheim is niet te zien bij
   welke het hoort — wie het oude sandbox-geheim laat staan, krijgt elke
   betaling geweigerd terwijl Stripe meldt dat hij hem afleverde.
5. Alle acht in één keer naar Render:

       python build/render.py --uit-env STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET \
           STRIPE_PRICE_LITE STRIPE_PRICE_PLUS STRIPE_PRICE_ULTRA \
           STRIPE_PRICE_TOKENS20 STRIPE_PRICE_TOKENS40 STRIPE_PRICE_TOKENS100 --ja

6. Eén echte betaling van EUR 2,99 met een echte pas. Kijken of het pakket
   omslaat en of de webhook 200 gaf. Daarna jezelf terugbetalen.

## 5. Controleren

    python betalen.py --check       # welke modus, staan de prijzen erin
    python betalen.py --webhooks    # welke endpoints, in welke modus
    python build/render.py --env    # wat er daadwerkelijk op Render staat
