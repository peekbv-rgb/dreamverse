/* De tweede taal.
 *
 * De pagina is in het Nederlands geschreven en dat blijft de bron: hier staat
 * per zin wat er in het Engels moet komen. Zo is er geen sleutelregister dat je
 * bij elke tekstwijziging moet bijhouden, en blijft index.html gewoon leesbaar.
 *
 * De sleutels staan op één regel; de pagina levert diezelfde zin ingesprongen en
 * over meerdere regels aan. Daarom wordt er op genormaliseerde witruimte gezocht.
 *
 * Wat de server of het model teruggeeft staat hier niet in — een duiding wordt
 * in de gekozen taal geschreven, niet achteraf vertaald. Vertaalde duiding leest
 * als vertaalde duiding, en dit product staat of valt bij de toon.
 */
(function () {
  "use strict";

  var EN = {};

  // De pagina staat ingesprongen in de HTML, dus dezelfde zin komt met andere
  // witruimte binnen dan hij hierboven staat. Voor het opzoeken telt de tekst,
  // en de sleutels hieronder gaan door dezelfde molen.
  function plat(tekst) {
    return String(tekst).replace(/\s+/g, " ").trim();
  }

  // Per regel: Nederlands, dan Engels. Eén lange lijst leest hier prettiger dan
  // een object vol aanhalingstekens over meerdere regels.
  [
    // -- de introductie ----------------------------------------------------
    ["Hoor Vera", "Hear Vera"],
    ["Nog een keer", "Once more"],
    ["Geluid uit", "Sound off"],
    ["Hoe heet je?", "What is your name?"],
    ["Geboortedatum", "Date of birth"],
    ["Geslacht", "Gender"],
    ["man", "man"],
    ["vrouw", "woman"],
    ["beide", "both"],
    ["zeg ik liever niet", "rather not say"],
    ["Taal", "Language"],
    ["Deel hier je droom", "Share your dream here"],
    ["Later invullen", "Fill in later"],

    // -- de kop ------------------------------------------------------------
    ["Je droom als verbeelding", "Your dream, imagined"],
    ["Vertel of typ wat je vannacht droomde. Je krijgt een verbeelding in vijf panelen, een duiding en een vooruitblik — en alles wat je eerder droomde telt mee.",
     "Tell or type what you dreamt last night. You get an imagining in five panels, a reading and a look ahead — and everything you dreamt before counts."],

    // -- de gids -----------------------------------------------------------
    ["Goedemorgen. Hier is Vera, heb je lekker geslapen?", "Good morning. Vera here — did you sleep well?"],
    ["anders", "change"],
    ["je naam", "your name"],
    ["Praat met Vera", "Talk to Vera"],
    ["Vera wordt wakker…", "Vera is waking up…"],
    ["Gesprek beëindigen", "End the conversation"],

    // -- de invoer ---------------------------------------------------------
    ["Wat droomde je?", "What did you dream?"],
    ["Ik vloog over de bergen en zag een vriendin huilen aan het zwembad…", "I was flying over the mountains and saw a friend crying by the pool…"],
    ["Wat wil je van deze droom?", "What do you want from this dream?"],
    ["Verbeeld mijn droom", "Imagine my dream"],
    ["Inspreken", "Speak it"],
    ["Archief wissen", "Clear the archive"],
    ["in je pakket", "in your plan"],

    // -- de speler ---------------------------------------------------------
    ["Meer van deze droom", "More from this dream"],
    ["Kernmoment op het beste model <b>10 tokens</b>", "Key moment on the best model <b>10 tokens</b>"],
    ["Hele verbeelding als film <b>30 tokens</b>", "The whole imagining as a film <b>30 tokens</b>"],
    ["Als film, beste model <b>60 tokens</b>", "As a film, best model <b>60 tokens</b>"],
    ["Terug", "Back"],
    ["Verder", "Next"],
    ["Stem aan", "Voice on"],
    ["Stem uit", "Voice off"],

    // -- de duiding --------------------------------------------------------
    ["De duiding", "The reading"],
    ["Waarom nu, wat het zegt, wat eraan zit te komen — en wat je er vandaag mee kunt.", "Why now, what it says, what is coming — and what you can do with it today."],
    ["Wat je vertelde", "What you told me"],
    ["Waarom je dit droomde", "Why you dreamt this"],
    ["Wat de droom zegt", "What the dream says"],
    ["Wat eraan zit te komen", "What is coming"],
    ["In de liefde", "In love"],
    ["Klein voorstel voor vandaag", "A small suggestion for today"],
    ["Je antwoord", "Your answer"],
    ["Schrijf op wat er in je opkomt. Het hoeft niet af te zijn.", "Write down whatever comes to mind. It does not have to be finished."],
    ["Bewaren", "Save"],
    ["Dit gaat mee in de duiding van je volgende droom.", "This goes into the reading of your next dream."],
    ["Dit antwoord telt mee in je volgende duiding.", "This answer counts towards your next reading."],

    // -- alle dromen samen -------------------------------------------------
    ["Je dromen samen", "Your dreams together"],
    ["Nog geen patroon", "No pattern yet"],
    ["Toen:", "Then:"],
    ["Nu:", "Now:"],
    ["Eén droom is een anekdote. Alles bij elkaar wordt een portret.", "One dream is an anecdote. All of them together become a portrait."],
    ["Deze droom staat nog op zichzelf. Vanaf je tweede of derde droom vormt het web zich.", "This dream still stands alone. From your second or third dream the web starts to form."],

    // -- het archief -------------------------------------------------------
    ["Wie er in je droom was", "Who was in your dream"],
    ["Klopte", "It did"],
    ["Deels", "Partly"],
    ["Niet", "It did not"],
    ["Dit stond hier", "This was written here"],
    ["dagen geleden. Klopte het?", "days ago. Did it happen?"],
    ["Je zei dat dit klopte.", "You said this was right."],
    ["Je zei dat dit deels klopte.", "You said this was partly right."],
    ["Je zei dat dit niet uitkwam.", "You said this did not happen."],
    ["Je eigen tekens", "Your own signs"],
    ["Het lichaam en de nacht", "The body and the night"],
    ["Als deze droom een opdracht was", "If this dream were an instruction"],
    ["Het spectrum van je dromen", "The spectrum of your dreams"],
    ["Welk kleurveld je nachten kozen. Elke kolom is een droom, van links naar rechts in de tijd.",
     "Which colour field your nights chose. Each column is a dream, left to right in time."],
    ["aarde", "earth"],
    ["Je chakrapilaar", "Your chakra pillar"],
    ["Alle dromen", "All dreams"],
    ["Alle dromen samen", "All your dreams together"],
    ["nachten", "nights"],
    ["Droom", "Dream"],
    ["veiligheid, grond onder je voeten", "safety, ground under your feet"],
    ["levenslust, eigenwaarde, genieten", "appetite for life, self-worth, enjoyment"],
    ["kracht, spanning, wat je voortdrijft", "strength, tension, what drives you"],
    ["liefde, verlies, verbinding", "love, loss, connection"],
    ["spreken, zwijgen, gehoord worden", "speaking, staying silent, being heard"],
    ["zien, weten, een voorgevoel", "seeing, knowing, a hunch"],
    ["overgave, deel van iets groters", "surrender, part of something larger"],
    ["verlangen", "desire"],
    ["wil", "will"],
    ["hart", "heart"],
    ["stem", "voice"],
    ["inzicht", "insight"],
    ["licht", "light"],
    ["Je droomarchief", "Your dream archive"],
    ["Hier bouwt het geheugen zich op. Elke droom telt mee in de volgende duiding.", "This is where the memory builds up. Every dream counts towards the next reading."],
    ["Nog leeg. Je eerste droom wordt Droom 1.", "Still empty. Your first dream becomes Dream 1."],
    ["Deze droom verwijderen", "Delete this dream"],
    ["Ik kon je niet horen.", "I could not hear you."],
    ["Terugkijken", "Look back"],
    ["verbonden", "connected"],
    ["ingelogd als", "signed in as"],
    ["dromen over", "dreams left"],
    ["kernmoment wordt gemaakt…", "key moment is being made…"],
    ["Droom %s is weer compleet.", "Dream %s is whole again."],
    ["Droom %s terughalen…", "Fetching dream %s back…"],
    ["Droom %s — al eerder gemaakt, kost je niets.", "Dream %s — already made, this costs you nothing."],
    ["Bij deze droom is alleen het beeld bewaard gebleven.", "Only the images were kept for this dream."],
    ["Schrijf de duiding opnieuw", "Write the reading again"],
    ["gratis, de panelen blijven staan.", "free, the panels stay as they are."],
    ["nog geen dromen", "no dreams yet"],
    ["geen beeld", "no images"],
    ["Kies een droom waar panelen bij gemaakt zijn.", "Pick a dream that has panels."],
    ["Bezig…", "Working…"],
    ["Verbinden…", "Connecting…"],
    ["In gesprek", "In conversation"],
    ["Panelen tekenen —", "Drawing panels —"],
    ["Inspreken —", "Recording narration —"],
    ["Film maken —", "Making the film —"],
    ["van de", "of"],
    ["panelen klaar", "panels done"],
    ["tokens", "tokens"],
    ["minuten vera", "minutes of vera"],
    ["pakket", "plan"],
    ["gratis", "free"],
    ["plus", "plus"],
    ["ultra", "ultra"],
    ["+10 tokens", "+10 tokens"],
    ["beheer", "admin"],
    ["uitloggen", "log out"],
    ["abonnement", "subscription"],
    ["Je gegevens", "Your data"],
    ["Je dromen zijn van jou. Je kunt ze meenemen, en je kunt ze weghalen.",
     "Your dreams are yours. You can take them with you, and you can remove them."],
    ["Alles meenemen", "Take everything with you"],
    ["Download mijn gegevens", "Download my data"],
    ["Alles weghalen", "Remove everything"],
    ["Mijn account verwijderen", "Delete my account"],
    ["Typ je wachtwoord om het te bevestigen", "Type your password to confirm"],
    ["Ja, verwijder alles", "Yes, delete everything"],
    ["Laat maar", "Never mind"],
    ["Alles is weg.", "Everything is gone."],
    ["Je account, je dromen en al het beeld zijn verwijderd. Er is geen kopie.",
     "Your account, your dreams and all the imagery have been deleted. There is no copy."],
    ["Kies dit pakket", "Choose this plan"],
    ["Tokens bijkopen", "Buy tokens"],
    ["Je gaat naar de betaalpagina van Stripe…", "Taking you to Stripe's payment page…"],
    ["Afrekenen lukte niet.", "Checkout did not work."],
    ["Inloggen", "Log in"],
    ["Account maken", "Create account"],
    ["E-mailadres", "Email address"],
    ["Wachtwoord", "Password"],
    ["Minstens acht tekens.", "At least eight characters."],
    ["laat zien", "show"],
    ["verberg", "hide"],
    ["Wachtwoord laten zien", "Show password"],
    ["Wachtwoord verbergen", "Hide password"],
    ["Wachtwoord vergeten?", "Forgotten your password?"],
    ["Vul eerst je e-mailadres in, dan sturen we je een nieuwe link.",
     "Fill in your email address first, then we will send you a new link."],
    ["Verstuurd.", "Sent."],
    ["Dreamverse", "Dreamverse"],
    ["Vannacht is één droom.<br>Na honderd nachten ontstaat jouw Dreamverse.",
     "Tonight is one dream.<br>After a hundred nights your Dreamverse takes shape."],
    ["Je vertelt je droom; je krijgt een verbeelding met een duiding en een vooruitblik. Elke eerdere droom telt mee.",
     "You tell your dream; you get an imagining with a reading and a look ahead. Every earlier dream counts."],
    ["Beheerderssleutel (ADMIN_TOKEN uit .env)", "Admin key (ADMIN_TOKEN from .env)"],
    ["Die sleutel wordt niet geaccepteerd.", "That key is not accepted."],
    ["voorbeeldmodus", "example mode"],
    ["Vera is niet aangesloten", "Vera is not connected"],

    // -- de pakketten ------------------------------------------------------
    ["Wat je kunt kiezen", "What you can choose"],
    ["Gratis om te proeven, en drie pakketten die je maandelijks opzegt.",
     "Free to get a taste, and three plans you can cancel monthly."],

    ["Gratis · €0", "Free · €0"],
    ["Eén droom om te proeven, met de volledige duiding en vijf getekende panelen. Geen video, en Vera spreek je alleen met tokens.",
     "One dream to get a taste, with the full reading and five drawn panels. No video, and you speak to Vera only with tokens."],
    ["Lite · €2,99", "Lite · €2.99"],
    ["Drie dromen per maand, elk met vijf getekende panelen en de hele duiding. Het bewegende kernmoment koop je met tokens, en zo betaal je alleen voor de dromen waar je het bij wilt.",
     "Three dreams a month, each with five drawn panels and the whole reading. The moving key moment is bought with tokens, so you only pay for the dreams you want it on."],
    ["lite", "lite"],
    ["Plus · €7,99", "Plus · €7.99"],
    ["Zes dromen per maand, elk met een <strong>bewegend kernmoment</strong> van vier seconden met geluid. De andere panelen zijn illustraties. Vera spreken gaat op tokens: twee per minuut.",
     "Six dreams a month, each with a <strong>moving key moment</strong> of four seconds with sound. The other panels are illustrations. Speaking to Vera runs on tokens: two per minute."],
    ["Ultra · €29,99", "Ultra · €29.99"],
    ["Tien dromen per maand met het kernmoment op het <strong>beste videomodel</strong>, en tien minuten met Vera inbegrepen. Daarna praat je verder op tokens.",
     "Ten dreams a month with the key moment on the <strong>best video model</strong>, and ten minutes with Vera included. After that you continue on tokens."],
    ["Aangesloten — knop bovenaan.", "Connected — button at the top."],

    // -- verbruik ----------------------------------------------------------
    ["Wat dit kost", "What this costs"],
    ["Wat het maken van deze dromen jou gekost heeft. Alleen zichtbaar in beheer.",
     "What making these dreams cost you. Only visible in admin mode."],
    ["Nog niets gemeten.", "Nothing measured yet."],

    // -- los te koop -------------------------------------------------------
    ["Los te koop", "Sold separately"],
    ["Wat te duur is om in een pakket te stoppen. Eén token is €0,25.", "What is too expensive to put in a plan. One token is €0.25."],
    ["Voor welke droom?", "For which dream?"],
    ["Kernmoment, beste model <b>10</b>", "Key moment, best model <b>10</b>"],
    ["Als film <b>30</b>", "As a film <b>30</b>"],
    ["Als film, beste model <b>60</b>", "As a film, best model <b>60</b>"],
    ["30 tokens · €7,50", "30 tokens · €7.50"],
    ["Je hele verbeelding als film van twintig seconden, in plaats van één bewegend moment.", "Your whole imagining as a twenty-second film, instead of one moving moment."],
    ["60 tokens · €15,00", "60 tokens · €15.00"],
    ["Dezelfde film op het beste model — dat wat je bij Ultra per kernmoment krijgt, dan twintig seconden lang.", "The same film on the best model — what you get per key moment on Ultra, but twenty seconds long."],
    ["10 tokens · €2,50", "10 tokens · €2.50"],
    ["Nog een kernmoment uit dezelfde droom, op het beste model.", "Another key moment from the same dream, on the best model."],

    // -- de voetnoot -------------------------------------------------------
    ["<strong>Betalen bestaat nog niet.</strong> Pakket en tokens zet je hierboven zelf, en dat kan iedereen die de app kan bereiken. Dat moet dicht voordat dit ergens publiek draait.",
     "<strong>There is no payment yet.</strong> You set the plan and tokens yourself above, and so can anyone who can reach the app. That has to be closed before this runs anywhere public."],
    ["<strong>Wat werkt.</strong> Tekst, geheugen en duiding worden per droom geschreven. De vijf panelen komen echt uit een beeldmodel, in een vaste stijl, met het kleurveld per paneel. Vera is aangesloten en praat met haar eigen stem; de knop bovenaan opent een gesprek van maximaal vijf minuten.",
     "<strong>What works.</strong> Text, memory and reading are written per dream. The five panels really do come from an image model, in a fixed style, with a colour field per panel. Vera is connected and speaks in her own voice; the button at the top opens a conversation of at most five minutes."],
    ["<strong>Het kernmoment beweegt.</strong> Het model dat je verbeelding schrijft wijst zelf aan welk paneel het draaipunt is, en dat ene wordt echte video met geluid — vier seconden, op het snelle model bij Plus en op het beste bij Ultra. De andere vier blijven stil, want twintig seconden video per droom kost meer dan een maandabonnement opbrengt.",
     "<strong>The key moment moves.</strong> The model that writes your imagining picks which panel is the turning point, and that one becomes real video with sound — four seconds, on the fast model with Plus and on the best one with Ultra. The other four stay still, because twenty seconds of video per dream costs more than a monthly subscription brings in."],
    ["<strong>De vooruitblik is vermaak, geen voorspelling.</strong> Hij gaat nooit over gezondheid, geld of iemands overlijden. Dat staat als regel in de prompt, niet in de hoop.",
     "<strong>The look ahead is entertainment, not prediction.</strong> It never touches health, money or anyone's death. That is a rule in the prompt, not a hope."],

    // -- zinnen die in app.js ontstaan --------------------------------------
    ["Herstellen lukte niet.", "Restoring did not work."],
    ["Terughalen lukte niet.", "Could not fetch it back."],
    ["Inspreken werkt in Chrome en Edge", "Speaking it works in Chrome and Edge"],
    ["Stop met opnemen", "Stop recording"],
    ["Ik luister. Neem de tijd.", "I am listening. Take your time."],
    ["Geen toegang tot de microfoon. Sta dat toe in je browser.", "No access to the microphone. Allow it in your browser."],
    ["Het opnemen stopte onverwacht. Typ anders even.", "The recording stopped unexpectedly. Try typing instead."],
    ["Genoteerd. Zal ik je droom verbeelden?", "Noted. Shall I imagine your dream?"],
    ["Ik heb niets opgevangen. Probeer het nog eens.", "I caught nothing. Try again."],
    ["Bezig met aanvragen…", "Requesting…"],
    ["Dat lukte niet.", "That did not work."],
    ["Onderweg. De zandloper onderin loopt mee.", "On its way. The hourglass at the bottom keeps you posted."],
    ["Bewaard. Vera weet dit bij je volgende droom.", "Saved. Vera will know this at your next dream."],
    ["Bewaren lukte niet. Probeer het nog eens.", "Saving did not work. Try again."],
    ["Archief gewist.", "Archive cleared."],
    ["Vertel eerst je droom.", "Tell me your dream first."],
    ["Je droom wordt verbeeld. Dit duurt een halve tot anderhalve minuut.", "Your dream is being imagined. This takes half a minute to a minute and a half."],
    ["Je droom wordt geduid. Dit duurt ongeveer een halve minuut.", "Your dream is being read. This takes about half a minute."],
    ["Ik kijk ernaar. Blijf even bij me.", "I am looking at it. Stay with me a moment."],
    ["Het lukte niet.", "It did not work."],
    ["Dit is een voorbeeld.", "This is an example."],
    ["Kijk maar. Ik heb er iets van gemaakt.", "Have a look. I made something of it."],
    ["Er ging iets mis. Probeer het zo nog eens.", "Something went wrong. Try again in a moment."],
    ["De vijf minuten zaten erop.", "The five minutes are up."],
    ["Kernmoment animeren — dit duurt ongeveer een minuut", "Animating the key moment — this takes about a minute"],
    ["Aanvraag gestart…", "Request started…"],
    ["De duiding wordt geschreven", "Writing the reading"],
    ["De duiding wordt opnieuw geschreven", "Rewriting the reading"],
    ["De duiding wordt opnieuw geschreven bij je panelen…", "The reading is being written again for your panels…"],
    ["Het kernmoment lukte niet", "The key moment did not work"],
    ["De film lukte niet", "The film did not work"],
    ["De panelen lukten niet", "The panels did not work"],
    ["Het hele archief wissen? De panelen, de video's en de ingesproken tekst gaan mee. Je volgende droom wordt Droom 1.", "Clear the whole archive? The panels, the videos and the narration go with it. Your next dream becomes Dream 1."]
  ].forEach(function (paar) { EN[plat(paar[0])] = paar[1]; });

  // Wat het model of de server teruggeeft blijft staan: dat is al in de goede
  // taal geschreven en hoort niet door een woordenlijst heen.
  var MET_RUST = ["#narration", "#why", "#meaning", "#future", "#love",
                  "#today", "#question", "#samen", "#seizoen", "#status", "#counter",
                  "#intro-tekst", "#minderjarig", "#kwaliteit-knoppen", "#kwaliteit-melding",
                  "#archive", "#threads", "#account", "#meter", "#extras-melding",
                  "#kies", "#kies-melding", "#voortgang", "#call-time", "#who-naam",
                  "#antwoord-uitleg", "#who-voor"].join(",");

  var TE_VERTALEN = "h1,h2,p,label,span.lbl,span.label,span.tier-name,span.extras-kop," +
                    "span.kwaliteit-kop,span.antwoord-uitleg,button,option,#mode";

  function vertaal(taal) {
    document.querySelectorAll(TE_VERTALEN).forEach(function (e) {
      if (e.closest(MET_RUST)) { return; }
      if (e.dataset.nl === undefined) { e.dataset.nl = e.innerHTML.trim(); }
      var nl = e.dataset.nl;
      if (taal === "en") {
        var en = EN[plat(nl)];
        if (en !== undefined) { e.innerHTML = en; }
      } else {
        e.innerHTML = nl;
      }
    });
    document.querySelectorAll("input[placeholder],textarea[placeholder]").forEach(function (e) {
      if (e.dataset.nlPh === undefined) { e.dataset.nlPh = e.placeholder; }
      var nl = e.dataset.nlPh;
      var en = EN[plat(nl)];
      e.placeholder = (taal === "en" && en !== undefined) ? en : nl;
    });
  }

  // Voor zinnen die in app.js ontstaan.
  function t(nl) {
    var en = EN[plat(nl)];
    return (window.TAAL === "en" && en !== undefined) ? en : nl;
  }

  window.TAAL = "nl";
  window.vertaalPagina = function (taal) { window.TAAL = taal; vertaal(taal); };
  window.t = t;
})();
