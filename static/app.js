/* Dreamverse — speler, invoer en stem.
   Praat met de server op /api. Alles wat hier gebeurt is presentatie; het
   schrijven en het geheugen zitten in Python. */

(function () {
  "use strict";

  var el = function (id) { return document.getElementById(id); };

  var stage = el("stage"), narration = el("narration"), counter = el("counter"),
      bar = el("bar"), statusEl = el("status"), archiveEl = el("archive"),
      threadsEl = el("threads"), input = el("dream"), guide = document.querySelector(".guide"),
      guideLine = el("guide-line"), player = el("player");

  var episode = null, index = 0, voiceOn = false;
  var panelImages = {};   // paneelnummer -> pad naar de illustratie van Kling
  var kernVideo = null;   // {panel: nummer, src: pad, status: "busy"|"done"|"failed"}
  var stemmen = {};       // paneelnummer -> opgenomen vertelstem
  var filmpjes = {};      // paneelnummer -> gekochte video voor dat paneel
  var speler = new Audio();
  var pollTimer = null;

  /* ---------------------------------------------------------------- velden */

  var FIELDS = {
    root:      { sky: "#2A0F14", deep: "#5E1C22", light: "#E2554F", ink: "#FFD9D2" },
    sacral:    { sky: "#2C1408", deep: "#6B3111", light: "#F0873C", ink: "#FFE2C6" },
    solar:     { sky: "#2A2208", deep: "#6A5411", light: "#F2C64C", ink: "#FFF3CC" },
    heart:     { sky: "#0B2418", deep: "#155038", light: "#4FBF86", ink: "#D3F5E4" },
    throat:    { sky: "#08202F", deep: "#12496E", light: "#4A9FE2", ink: "#D2ECFF" },
    third_eye: { sky: "#140E33", deep: "#2C2470", light: "#6E62DA", ink: "#DCD8FF" },
    crown:     { sky: "#1C0E2C", deep: "#4A2270", light: "#B369DE", ink: "#F0DBFF" }
  };

  function ridge(y, amp, fill) {
    var pts = [], x;
    for (x = 0; x <= 800; x += 100) {
      pts.push(x + "," + Math.round(y + Math.sin(x / 90 + y) * amp));
    }
    return '<polygon points="0,500 ' + pts.join(" ") + ' 800,500" fill="' + fill + '"/>';
  }

  function mandala(cx, cy, r, colour) {
    /* Zes cirkels rond een zevende: de kern van de bloem des levens. */
    var out = '<g class="turn" opacity=".5" fill="none" stroke="' + colour + '" stroke-width="1.2">';
    out += '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '"/>';
    for (var i = 0; i < 6; i++) {
      var a = (Math.PI / 3) * i;
      out += '<circle cx="' + (cx + Math.cos(a) * r) + '" cy="' + (cy + Math.sin(a) * r) + '" r="' + r + '"/>';
    }
    return out + "</g>";
  }

  function scene(panel) {
    var f = FIELDS[panel.palette] || FIELDS.crown;
    var m = panel.motif || "expanse";
    var s = '<svg viewBox="0 0 800 500" class="fade" role="img" aria-label="Sfeerbeeld bij dit paneel">';

    s += '<defs>' +
         '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">' +
         '<stop offset="0%" stop-color="' + f.sky + '"/><stop offset="100%" stop-color="' + f.deep + '"/></linearGradient>' +
         '<radialGradient id="halo" cx="50%" cy="50%" r="50%">' +
         '<stop offset="0%" stop-color="' + f.light + '" stop-opacity=".55"/>' +
         '<stop offset="100%" stop-color="' + f.light + '" stop-opacity="0"/></radialGradient>' +
         '</defs>';

    s += '<rect width="800" height="500" fill="url(#sky)"/>';
    s += mandala(400, 250, 96, f.light);
    s += '<circle cx="400" cy="250" r="230" fill="url(#halo)" opacity=".5"/>';

    s += '<g class="drift">';
    if (m === "close") {
      for (var r = 1; r <= 5; r++) {
        s += '<ellipse cx="400" cy="270" rx="' + (r * 68) + '" ry="' + (r * 21) +
             '" fill="none" stroke="' + f.ink + '" stroke-width="' + (2.4 - r * 0.35) +
             '" opacity="' + (0.7 - r * 0.11) + '"/>';
      }
    } else if (m === "water") {
      s += ridge(310, 20, f.deep);
      s += '<rect x="110" y="335" width="580" height="150" rx="14" fill="' + f.light + '" opacity=".6"/>';
      s += '<g class="shimmer"><rect x="165" y="372" width="250" height="3" rx="2" fill="' + f.ink + '"/>' +
           '<rect x="330" y="424" width="290" height="3" rx="2" fill="' + f.ink + '" opacity=".7"/></g>';
    } else if (m === "structure") {
      s += ridge(255, 30, f.deep);
      s += ridge(370, 16, f.sky);
      s += '<g class="shimmer"><rect x="330" y="360" width="170" height="74" rx="8" fill="' + f.light + '" opacity=".85"/></g>';
    } else if (m === "figure") {
      s += ridge(300, 18, f.deep);
      s += '<rect y="368" width="800" height="132" fill="' + f.sky + '"/>';
      s += '<ellipse cx="400" cy="370" rx="70" ry="14" fill="url(#halo)"/>';
      s += '<path d="M378 366 q6 -52 24 -58 q21 -6 25 17 q4 21 -8 41 z" fill="' + f.sky + '"/>' +
           '<circle cx="401" cy="296" r="17" fill="' + f.sky + '"/>' +
           '<path d="M382 374 q25 10 50 0 l4 13 q-29 12 -58 0 z" fill="' + f.sky + '"/>';
    } else if (m === "flight") {
      s += ridge(335, 44, f.deep);
      s += ridge(425, 24, f.sky);
      s += '<ellipse cx="300" cy="214" rx="28" ry="5" fill="' + f.light + '" opacity=".25"/>' +
           '<path d="M282 203 q18 -12 36 0 q-18 9 -36 0 z" fill="' + f.ink + '"/>' +
           '<circle cx="300" cy="199" r="4.5" fill="' + f.ink + '"/>';
    } else {
      s += ridge(345, 32, f.deep);
      s += ridge(435, 18, f.sky);
      for (var i = 0; i < 26; i++) {
        s += '<circle cx="' + ((i * 137) % 780 + 10) + '" cy="' + ((i * 61) % 210 + 15) +
             '" r="1.5" fill="' + f.ink + '" opacity=".55"/>';
      }
    }
    return s + "</g></svg>";
  }

  /* ----------------------------------------------------------------- stem */

  /* De verteller. Vera's eigen stem (Violet) kan hier niet gebruikt worden:
     avatarstemmen en voorleesstemmen zijn bij Runway twee losse verzamelingen.
     Wat wel kan is de browser een vrouwenstem laten pakken in plaats van de
     eerste de beste — dat is in het Nederlands vaak een man. */
  var verteller = null;

  var VROUWELIJK = ["fenna", "colette", "lotte", "saskia", "ellen", "google nederlands",
                    "eva", "claire", "laura", "female", "vrouw"];
  var MANNELIJK = ["frank", "maarten", "xander", "daan", "male", "man"];

  function kiesVerteller() {
    if (!("speechSynthesis" in window)) { return; }
    var alle = window.speechSynthesis.getVoices() || [];
    if (!alle.length) { return; }
    var nl = alle.filter(function (v) { return (v.lang || "").toLowerCase().indexOf("nl") === 0; });
    var kandidaten = nl.length ? nl : alle;

    function scoor(v) {
      var n = (v.name || "").toLowerCase();
      for (var i = 0; i < VROUWELIJK.length; i++) { if (n.indexOf(VROUWELIJK[i]) !== -1) { return 2; } }
      for (var k = 0; k < MANNELIJK.length; k++) { if (n.indexOf(MANNELIJK[k]) !== -1) { return 0; } }
      return 1;   // onbekend: liever dit dan een stem waarvan we weten dat het een man is
    }
    kandidaten.sort(function (a, b) { return scoor(b) - scoor(a); });
    verteller = kandidaten[0] || null;
  }

  if ("speechSynthesis" in window) {
    kiesVerteller();
    // De lijst is bij het laden vaak nog leeg en komt later binnen.
    window.speechSynthesis.onvoiceschanged = kiesVerteller;
  }

  function speak(text) {
    if (!voiceOn) { return; }
    // Is het paneel ingesproken door de echte verteller, dan die - altijd
    // dezelfde stem, op elk apparaat.
    if (stemmen[index]) {
      try {
        window.speechSynthesis && window.speechSynthesis.cancel();
        speler.pause();
        speler.src = stemmen[index];
        speler.play().catch(function () { /* browser wil geen geluid; jammer */ });
        return;
      } catch (e) { /* val terug op de browserstem */ }
    }
    if (!("speechSynthesis" in window)) { return; }
    try {
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text);
      u.lang = "nl-NL";
      if (verteller) { u.voice = verteller; }
      // Iets lager en langzamer dan standaard: dit is een droom, geen mededeling.
      u.rate = 0.84; u.pitch = 1.05;
      window.speechSynthesis.speak(u);
    } catch (e) { /* stil terugvallen op alleen tekst */ }
  }

  /* --------------------------------------------------------------- speler */

  function show(n) {
    var total = episode.panels.length;
    index = Math.max(0, Math.min(total - 1, n));
    deelKnopBijwerken();
    var panel = episode.panels[index];
    stage.innerHTML = scene(panel);
    // Een gekochte film: elk paneel beweegt.
    var eigenFilm = filmpjes[index];
    // Het kernmoment: op dit ene paneel staat geen plaatje maar echte video.
    if (eigenFilm || (kernVideo && kernVideo.panel === index && kernVideo.src)) {
      var v = document.createElement("video");
      v.className = "kernmoment";
      v.src = eigenFilm || kernVideo.src;
      v.playsInline = true;
      v.loop = true;
      v.controls = false;
      stage.appendChild(v);
      // Met geluid proberen; blokkeert de browser dat, dan gedempt verder.
      v.play().catch(function () { v.muted = true; v.play().catch(function () {}); });
      var merk = document.createElement("span");
      merk.className = "kern-merk";
      merk.textContent = eigenFilm ? t("animatie") : t("kernmoment");
      stage.appendChild(merk);
      narration.textContent = panel.narration;
      counter.textContent = (index + 1) + " / " + total;
      el("prev").disabled = index === 0;
      el("next").textContent = index === total - 1 ? "Opnieuw" : "Verder";
      var pips2 = bar.querySelectorAll("span");
      for (var q = 0; q < pips2.length; q++) { pips2[q].classList.toggle("done", q <= index); }
      speak(panel.narration);
      // De video staat er nu pas; de knop kijkt ernaar om te weten of er iets
      // te delen valt.
      deelKnopBijwerken();
      return;
    }
    if (kernVideo && kernVideo.panel === index && kernVideo.status === "busy") {
      var wacht = document.createElement("span");
      wacht.className = "kern-merk bezig";
      wacht.textContent = t("kernmoment wordt gemaakt…");
      stage.appendChild(wacht);
    }

    var drawn = panelImages[index];
    if (drawn) {
      // De tekening blijft eronder staan: valt het beeld weg, dan is er nog iets.
      var img = new Image();
      img.className = "painted";
      img.alt = "";
      img.src = drawn;
      stage.appendChild(img);
    }
    narration.textContent = panel.narration;
    counter.textContent = (index + 1) + " / " + total;
    el("prev").disabled = index === 0;
    el("next").textContent = index === total - 1 ? "Opnieuw" : "Verder";
    var pips = bar.querySelectorAll("span");
    for (var p = 0; p < pips.length; p++) {
      pips[p].classList.toggle("done", p <= index);
    }
    speak(panel.narration);
  }

  /* De zandloper: het enige bewijs dat er nog iets gebeurt.
   *
   * Er zit anderhalve minuut tussen op de knop drukken en de eerste letter, en
   * in die tijd bewoog er niets. Dan denk je dat het stuk is - en dat is erger
   * dan wachten, want je gaat opnieuw klikken.
   *
   * Daarom loopt er nu een teller mee. Een draaiende zandloper alleen is niet
   * genoeg: die draait ook door als de verbinding weg is. Een klok die elke
   * seconde verspringt zegt dat er echt nog iemand thuis is.
   */
  var bezigSinds = 0;
  var bezigTikker = null;
  var bezigRegel = "";
  var bezigStuk = "";

  function klok(ms) {
    var s = Math.floor(ms / 1000);
    return Math.floor(s / 60) + ":" + (s % 60 < 10 ? "0" : "") + (s % 60);
  }

  function verfBalk() {
    var balk = el("voortgang");
    if (!balk) { return; }
    if (bezigStuk) {
      balk.hidden = false;
      balk.className = "voortgang mis";
      balk.innerHTML = '<span aria-hidden="true">✕</span><span>' + bezigStuk + "</span>";
      return;
    }
    if (!bezigRegel) {
      balk.hidden = true;
      balk.innerHTML = "";
      return;
    }
    balk.hidden = false;
    balk.className = "voortgang";
    balk.innerHTML = '<span class="zandloper" aria-hidden="true">⧗</span><span>' +
                     bezigRegel + '</span><span class="klok">' +
                     klok(Date.now() - bezigSinds) + "</span>";
  }

  function startBezig(regel) {
    bezigRegel = regel;
    bezigStuk = "";
    if (!bezigSinds) { bezigSinds = Date.now(); }
    verfBalk();
    if (!bezigTikker) { bezigTikker = setInterval(verfBalk, 1000); }
  }

  function stopBezig() {
    bezigRegel = "";
    bezigStuk = "";
    bezigSinds = 0;
    if (bezigTikker) { clearInterval(bezigTikker); bezigTikker = null; }
    verfBalk();
  }

  function mislukt(regels) {
    bezigRegel = "";
    bezigStuk = regels;
    if (bezigTikker) { clearInterval(bezigTikker); bezigTikker = null; }
    verfBalk();
  }

  /* Wat er op dit moment gemaakt wordt.
   *
   * Twee dingen die eerder misgingen. Tussen "aanvraag verstuurd" en de eerste
   * keer dat de server "busy" meldt zit een gaatje, en in dat gaatje verdween de
   * balk weer. En als er iets mislukte werd de balk gewoon verborgen, zodat je
   * nooit te horen kreeg dat het niet doorging.
   */
  var werkGestart = 0;
  var werkGezien = false;

  function verwachtWerk() {
    werkGestart = Date.now();
    werkGezien = false;
  }

  function toonVoortgang(state) {
    var regels = [];
    var totaal = (episode && episode.panels) ? episode.panels.length : 5;

    var klaar = Object.keys(state.images || {}).length;
    if (state.status === "busy") {
      regels.push(t("Panelen tekenen —") + " " + klaar + " " + t("van de") + " " + totaal);
    }
    if (state.stem_status === "busy") {
      regels.push(t("Inspreken —") + " " + Object.keys(state.stem || {}).length + " " +
                  t("van de") + " " + totaal);
    }
    if (state.video_status === "busy") {
      regels.push(t("Kernmoment animeren — reken op een paar minuten"));
    }
    if (state.film_status === "busy") {
      var f = Object.keys(state.film || {}).length;
      regels.push(t("Animatie maken —") + " " + f + " " + t("van de") + " " + totaal + " " +
                  t("panelen klaar"));
    }

    var stuk = [];
    if (state.video_status === "failed") {
      stuk.push(t("Het kernmoment lukte niet") +
                (state.video_error ? " — " + state.video_error : ""));
    }
    if (state.film_status === "failed") { stuk.push(t("De animatie lukte niet")); }
    if (state.status === "failed") { stuk.push(t("De panelen lukten niet")); }

    if (regels.length) {
      werkGezien = true;
      startBezig(regels.join(" · "));
      return;
    }
    if (stuk.length) { mislukt(stuk.join(" · ")); return; }

    // Nog niets te melden, maar er is net wel iets in gang gezet: laten staan.
    if (!werkGezien && Date.now() - werkGestart < 40000) {
      startBezig(t("Aanvraag gestart…"));
      return;
    }
    stopBezig();
  }

  /* Kijken of het tekenwerk al klaar is.
   *
   * Hier stond 90 keer met vier seconden ertussen: precies zes minuten, en
   * daarna hield hij stil op met kijken terwijl de zandloper doortikte. Wie een
   * hele verbeelding als animatie koopt is zo een kwartier bezig, en zag dus een
   * teller die niets meer betekende.
   *
   * Nu duurt het langer en gaat het rustiger: de eerste twee minuten elke vier
   * seconden, daarna elke acht. En als de tijd echt op is, zegt hij dat - het
   * werk loopt op de server gewoon door, dus verversen helpt.
   */
  // Twee minuten snel, daarna acht seconden: samen ruim twintig minuten. Genoeg
  // voor een hele verbeelding als animatie, het langste werk dat er is.
  var POLL_TOTAAL = 180;

  function pollPanels(number, tries) {
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    if (tries <= 0) {
      stopBezig();
      statusEl.className = "status";
      statusEl.textContent = t("Dit duurt langer dan verwacht. Het werk loopt door; "
                               + "ververs de pagina om te kijken of het klaar is.");
      return;
    }
    fetch("/api/panels/" + number)
      .then(function (r) { return r.json(); })
      .then(function (state) {
        var fresh = false;
        Object.keys(state.images || {}).forEach(function (k) {
          if (!panelImages[k]) { panelImages[k] = state.images[k]; fresh = true; }
        });
        if (state.film) {
          // Een gekochte film vervangt alle panelen door bewegend beeld.
          Object.keys(state.film).forEach(function (k) {
            filmpjes[k] = state.film[k];
          });
        }
        if (state.stem) {
          Object.keys(state.stem).forEach(function (k) { stemmen[k] = state.stem[k]; });
        }
        if (state.video_panel !== undefined) {
          var was = kernVideo && kernVideo.src;
          kernVideo = { panel: state.video_panel, src: state.video || null,
                        status: state.video_status || "busy" };
          if (kernVideo.src && !was) { fresh = true; }
        }
        // Staat het net binnengekomen paneel in beeld, dan meteen tonen.
        if (fresh && panelImages[index] && !stage.querySelector(".painted")) { show(index); }
        deelKnopBijwerken();
        toonVoortgang(state);
        var bezig = state.status !== "done"
                 || (kernVideo && kernVideo.status === "busy")
                 || state.film_status === "busy"
                 || state.stem_status === "busy";
        if (bezig) {
          // De eerste twee minuten snel kijken, daarna rustiger: dan is het
          // groot werk en heeft elke vier seconden geen zin meer.
          var pauze = tries > POLL_TOTAAL - 30 ? 4000 : 8000;
          pollTimer = setTimeout(function () { pollPanels(number, tries - 1); }, pauze);
        }
      })
      .catch(function () { /* beeld is bijzaak; de verbeelding staat er al */ });
  }

  /* De lijn door alle dromen heen.
   *
   * Dit blok staat altijd op de pagina, ook zonder open verbeelding: het is de
   * reden dat iemand terugkomt. Eén droom is een anekdote, tien dromen zijn een
   * portret, en dat portret hoort niet te verdwijnen zodra je de pagina ververst.
   *
   * Bij elke nieuwe droom wordt hij herschreven. Een oude droom terugkijken mag
   * hem niet terugzetten naar een eerdere versie, dus alleen een nieuwer nummer
   * mag overschrijven.
   */
  var samenVan = 0;

  // Twee dingen die elkaar nodig hebben en op verschillende momenten binnenkomen:
  // het pakket komt van /api/account, de tekens van /api/archive. Wie het laatst
  // aankomt tekent de kaart, dus allebei worden ze hier onthouden.
  var rekeningPlan = "";
  var laatsteSamen = null;

  /* "Vera zag iets" - het moment waarop een gratis gebruiker gaat betalen.
   *
   * Eén gratis droom liet iemand droom -> duiding -> beeld zien en daar stopte
   * het. Wat hij nooit meemaakte is droom 1 + 2 + 3 -> hier loopt iets
   * doorheen, en dat is precies wat het abonnement verkoopt. Vandaar drie
   * gratis dromen, en vandaar deze kaart op de derde.
   *
   * Er staat niets in dat we verzinnen. `symbols` noemt alleen tekens die in
   * meer dan één droom voorkwamen - dat is de regel in de prompt - en een draad
   * verwijst naar een droom die er echt is. Is er geen van beide, dan blijft de
   * kaart weg: beweren dat er een patroon is terwijl er niets te noemen valt,
   * is de snelste manier om dit hele onderdeel ongeloofwaardig te maken.
   */
  function toonVeraZag(gegevens) {
    var kaart = el("verazag");
    if (!kaart) { return; }
    var tekens = (gegevens && gegevens.symbols) || [];
    var draden = (gegevens && gegevens.threads) || [];

    // Alleen bij wie er nog niet voor betaalt, en alleen vanaf drie nachten.
    var mag = rekeningPlan === "gratis" && aantalDromen >= 3;
    if (!mag || (!tekens.length && !draden.length)) { kaart.hidden = true; return; }

    // Hoogstens drie regels: tekens eerst, draden vullen aan. Meer leest als
    // de duiding zelf, en die staat er hieronder al.
    var regels = [];
    tekens.slice(0, 2).forEach(function (k) {
      regels.push([k.sign, k.meaning || ""]);
    });
    draden.forEach(function (d) {
      if (regels.length < 3) { regels.push([d.ref, d.now || d.was || ""]); }
    });

    var doos = el("verazag-regels");
    doos.innerHTML = "";
    if (tekens.length) {
      // Eén keer boven de lijst en niet achter elk teken: dezelfde zin twee keer
      // onder elkaar leest als een sjabloon in plaats van als een vondst. Geen
      // aantal erbij - het veld garandeert "meer dan één", niet hoeveel.
      var lead = document.createElement("p");
      lead.className = "verazag-lead";
      lead.textContent = t("Dit kwam in meer dan één van je dromen terug:");
      doos.appendChild(lead);
    }
    regels.forEach(function (paar) {
      var p = document.createElement("p");
      var tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = paar[0];
      p.appendChild(tag);
      p.appendChild(document.createTextNode(" " + paar[1]));
      doos.appendChild(p);
    });
    kaart.hidden = false;
  }

  // De knop wijst naar de pakketten. Niet naar Stripe: eerst zien wat er te
  // kiezen valt, dan pas betalen.
  if (el("verazag-knop")) {
    el("verazag-knop").addEventListener("click", function () {
      var doel = document.querySelector(".tiers");
      var sectie = doel ? doel.closest("section") : null;
      if (!sectie) { return; }
      sectie.scrollIntoView({ behavior: "smooth", block: "center" });
      if (doel) {
        doel.classList.add("wijs");
        setTimeout(function () { doel.classList.remove("wijs"); }, 2400);
      }
    });
  }

  function toonSamen(nummer, tekst, draden, tekens) {
    nummer = nummer || 0;
    if (nummer && nummer < samenVan) { return; }
    samenVan = nummer || samenVan;

    laatsteSamen = { symbols: tekens || [], threads: draden || [] };
    toonVeraZag(laatsteSamen);

    // De gezamenlijke duiding komt nu in alinea's terug in plaats van in twee
    // zinnen. Met textContent op een enkele <p> vallen die lege regels weg en
    // wordt het één muur tekst - precies het stuk dat je wél wilt lezen.
    var samen = el("samen");
    samen.innerHTML = "";
    (tekst || "").split(/\n\s*\n/).forEach(function (stuk) {
      var s = stuk.trim();
      if (!s) { return; }
      var a = document.createElement("p");
      a.textContent = s;
      samen.appendChild(a);
    });
    samen.hidden = !tekst;
    threadsEl.innerHTML = "";
    el("threads-section").hidden = false;

    if (draden && draden.length) {
      el("threads-title").textContent = t("Je dromen samen");
      draden.forEach(function (draad) {
        var d = document.createElement("div");
        d.className = "thread";
        var tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = draad.ref;
        var toen = document.createElement("p");
        // "Toen" zegt niets; een datum plaatst het meteen. Weten we hem niet -
        // een oude droom zonder datum - dan blijft het bij "Toen".
        toen.textContent = datumVan(draad.ref) + " " + draad.was;
        var nu = document.createElement("p");
        nu.className = "then";
        nu.textContent = t("Nu:") + " " + draad.now;
        d.appendChild(tag); d.appendChild(toen); d.appendChild(nu);
        threadsEl.appendChild(d);
      });
    } else if (!tekst) {
      /* Zeggen hoe ver je bent, niet dat er niets is.
       *
       * Hier stond "vanaf je tweede of derde droom vormt het web zich" - waar
       * dan niet uit blijkt wat je zelf moet doen om er te komen. Drie is de
       * grens: onder de drie is er geen patroon om over te schrijven, en dan
       * doen alsof er al een lijn is, is niet eerlijk. Dus staat het getal er,
       * en hoeveel er nog bij moeten.
       */
      var over = Math.max(0, 3 - aantalDromen);
      el("threads-title").textContent = over
        ? (t("Nog") + " " + over + " " + t(over === 1 ? "nacht tot je Dreamverse" : "nachten tot je Dreamverse"))
        : t("Nog geen patroon");
      var leeg = document.createElement("div");
      leeg.className = "thread wachtend";
      if (over) {
        var kop = document.createElement("p");
        kop.className = "wachtend-kop";
        kop.textContent = t("Vanaf drie nachten schrijft Vera de lijn door al je dromen heen:")
          + " " + t("welke plaatsen, personen en dieren terugkomen, en wat er sindsdien veranderd is.");
        var teller = document.createElement("span");
        teller.className = "tag";
        teller.textContent = aantalDromen + " / 3";
        leeg.appendChild(teller);
        leeg.appendChild(kop);
        // Alleen naar de pilaar wijzen als die er ook staat. Bij nul dromen is
        // hij verborgen, en wijzen naar iets wat er niet is is erger dan zwijgen.
        if (aantalDromen) {
          var nu = document.createElement("p");
          nu.className = "then";
          nu.textContent = t("Je chakrapilaar vult zich ondertussen al — die staat hieronder.");
          leeg.appendChild(nu);
        }
      } else {
        leeg.textContent = t("Deze droom staat nog op zichzelf. Bij de volgende gaan de lijnen zich aftekenen.");
      }
      threadsEl.appendChild(leeg);
    } else {
      el("threads-title").textContent = t("Je dromen samen");
    }
  }

  /* De datum van de droom waar een draad naar verwijst.
   *
   * `ref` is iets als "Droom 12" of "Dream 12"; het nummer is wat telt. Zonder
   * bekende datum valt hij terug op het oude woord, want een lege regel is
   * erger dan een vaag woord.
   */
  function datumVan(ref) {
    var m = String(ref || "").match(/(\d+)/);
    var wanneer = m ? wanneerPerDroom[parseInt(m[1], 10)] : null;
    if (!wanneer) { return t("Toen:"); }
    var d = new Date(wanneer);
    if (isNaN(d.getTime())) { return t("Toen:"); }
    var taal = (profiel && profiel.language) === "en" ? "en-US" : "nl-NL";
    try {
      return d.toLocaleDateString(taal, { day: "numeric", month: "long", year: "numeric" }) + ":";
    } catch (e) {
      return wanneer + ":";
    }
  }

  /* Klopte de vooruitblik?
   *
   * Alleen de dromer oordeelt. Zodra wij zouden scoren wordt de vooruitblik een
   * claim, en dan houdt "vermaak, geen voorspelling" geen stand. Het oordeel gaat
   * ook niet terug de prompt in: een model dat weet dat het op raak beoordeeld
   * wordt gaat vaag schrijven of gokken.
   *
   * De vraag komt pas als er tijd overheen is. Op de dag zelf is er niets te
   * beoordelen en voelt het als een enquête.
   */
  var DAGEN_VOOR_OORDEEL = 7;

  function toonOordeel(ep) {
    var doos = el("oordeel");
    if (!ep.future || !ep.number || !ep.when) { doos.hidden = true; return; }
    var dagen = Math.floor((Date.now() - new Date(ep.when).getTime()) / 86400000);
    if (isNaN(dagen) || dagen < DAGEN_VOOR_OORDEEL) { doos.hidden = true; return; }

    doos.hidden = false;
    doos.dataset.dream = ep.number;
    var gegeven = ep.future_check || "";
    var gezegd = {raak: "Je zei dat je dit hebt teruggezien.",
                  deels: "Je zei dat je hier iets van hebt teruggezien.",
                  mis: "Je zei dat je dit niet hebt teruggezien."};
    el("oordeel-vraag").textContent = gegeven
      ? t(gezegd[gegeven])
      : t("Dit stond hier") + " " + dagen + " " + t("dagen geleden. Heb je het teruggezien?");
    doos.querySelectorAll(".oordeel-knop").forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.oordeel === gegeven ? "true" : "false");
    });
  }

  document.querySelectorAll(".oordeel-knop").forEach(function (knop) {
    knop.addEventListener("click", function () {
      var nummer = parseInt(el("oordeel").dataset.dream, 10);
      if (!nummer) { return; }
      fetch("/api/dream/" + nummer + "/vooruitblik", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verdict: knop.dataset.oordeel })
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (episode) { episode.future_check = (d.dream || {}).future_check || ""; }
          toonOordeel(episode || {});
        })
        .catch(function () { /* een oordeel is geen voorwaarde */ });
    });
  });

  var MAANDEN = {
    nl: ["januari", "februari", "maart", "april", "mei", "juni", "juli",
         "augustus", "september", "oktober", "november", "december"],
    en: ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"]
  };

  function datumInWoorden(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) { return ""; }
    var m = (MAANDEN[window.TAAL] || MAANDEN.nl)[d.getMonth()];
    return window.TAAL === "en"
      ? m + " " + d.getDate() + ", " + d.getFullYear()
      : d.getDate() + " " + m + " " + d.getFullYear();
  }

  function render(ep) {
    episode = ep;
    panelImages = {};
    kernVideo = null;
    stemmen = {};
    filmpjes = {};
    try { speler.pause(); } catch (e) { /* niets aan de hand */ }
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    // Altijd één keer kijken wat er op schijf staat, ook als er geen tekenwerk
    // loopt. Stond dit alleen op images_pending, dan haalde een heropende droom
    // zijn panelen nooit op: die vlag is dan allang false. Loopt er wél werk,
    // dan blijven we doorpollen.
    if (ep.images_pending) { verwachtWerk(); }
    pollPanels(ep.number, ep.images_pending ? POLL_TOTAAL : 1);
    el("title").textContent = ep.title;
    // De kop draagt nu de titel van de droom, niet meer de slogan: dat is de
    // nieuwe brontekst, anders zet een taalwissel de slogan terug.
    el("title").dataset.nl = ep.title;
    toonBril(ep);
    toonZorg(ep);
    toonVragen(ep);
    toonTerugkoppeling();
    player.hidden = false;

    // "Alleen de duiding" betekent ook echt geen beeld: geen panelen, en dus ook
    // niet de getekende composities die anders als plaatsvervanger dienen. Wat
    // er wel is, is het verhaal in vijf stukken - dat blijft, als tekst.
    var tekstAlleen = ep.quality === "duiding";
    player.classList.toggle("alleen-tekst", tekstAlleen);
    el("verhaal").hidden = !tekstAlleen;
    if (tekstAlleen) {
      el("verhaal").innerHTML = "";
      ep.panels.forEach(function (paneel) {
        var alinea = document.createElement("p");
        alinea.textContent = paneel.narration;
        el("verhaal").appendChild(alinea);
      });
    }

    bar.innerHTML = "";
    ep.panels.forEach(function () { bar.appendChild(document.createElement("span")); });
    show(0);

    toonSamen(ep.number, ep.together, ep.threads, ep.symbols);

    el("extras").hidden = !ep.number;
    el("extras").dataset.dream = ep.number || "";
    el("extras-melding").textContent = "";
    el("extras-melding").className = "extras-melding";

    el("reading-section").hidden = false;
    // De slotvraag krijgt een antwoordveld: zonder dat is het een doodlopende weg.
    var blok = el("antwoord-blok");
    blok.hidden = !ep.question;
    blok.classList.remove("bewaard");
    el("antwoord").value = "";
    el("antwoord-uitleg").textContent = t("Dit gaat mee in de duiding van je volgende droom.");
    blok.dataset.dream = ep.number;
    // De droom zoals hij verteld is, boven de duiding. Alles eronder verwijst
    // ernaar, en na een maand weet je zelf niet meer wat je hebt ingetypt.
    el("verteld").textContent = ep.dream || "";
    el("verteld-blok").hidden = !ep.dream;
    el("verteld-wanneer").textContent = ep.when ? datumInWoorden(ep.when) : "";

    el("why").textContent = ep.why;
    el("meaning").textContent = ep.meaning;
    el("future").textContent = ep.future;
    el("love").textContent = ep.love || "";
    el("love").parentElement.hidden = !ep.love;

    // Wie erin voorkwam. Dit is op termijn het rijkste stuk geheugen: na honderd
    // dromen weet je wie de vaste bezetting van iemands nachten is.
    var mensen = el("mensen");
    mensen.innerHTML = "";
    (ep.people || []).forEach(function (m) {
      var rij = document.createElement("div");
      rij.className = "mens";
      var wie = document.createElement("span");
      wie.className = "wie";
      wie.textContent = m.who;
      var rol = document.createElement("p");
      rol.textContent = m.role;
      rij.appendChild(wie); rij.appendChild(rol);
      mensen.appendChild(rij);
    });
    el("mensen-blok").hidden = !(ep.people && ep.people.length);

    // Tekens uit zijn eigen dromen, niet uit een droomwoordenboek: water betekent
    // hier iets doordat hij er zes keer over droomde.
    var tekens = el("tekens");
    tekens.innerHTML = "";
    (ep.symbols || []).forEach(function (k) {
      var rij = document.createElement("div");
      rij.className = "teken";
      var naam = document.createElement("span");
      naam.className = "tag";
      naam.textContent = k.sign;
      var uitleg = document.createElement("p");
      uitleg.textContent = k.meaning;
      rij.appendChild(naam); rij.appendChild(uitleg);
      tekens.appendChild(rij);
    });
    el("tekens-blok").hidden = !(ep.symbols && ep.symbols.length);

    el("nacht").textContent = ep.night || "";
    el("nacht-blok").hidden = !ep.night;
    el("opdracht").textContent = ep.task || "";
    el("opdracht-blok").hidden = !ep.task;

    toonOordeel(ep);

    el("today").textContent = ep.today || "";
    el("vandaag-blok").hidden = !ep.today;
    el("seizoen").textContent = ep.season || "";
    el("seizoen").hidden = !ep.season;
    el("question").textContent = ep.question;
  }

  /* ------------------------------------------------------------- spectrum */

  /* De pilaar.
   *
   * De tekening is een vaste plaat: zeven lotussen in een sterrenveld, met de
   * lichtbundel erdoorheen. Zelf zeven lotussen tekenen in SVG kwam niet in de
   * buurt van wat het moest worden, dus is de plaat gegenereerd en meten we de
   * hoogtes van de zeven middelpunten er een keer uit.
   *
   * Wat er per droom overheen gaat: de velden die weinig voorkwamen doven weg
   * in het donker, de velden die overheersten blijven fel en krijgen hun
   * percentage. Zo is dezelfde tekening elke keer een ander beeld.
   */
  var VELDEN = [
    { key: "root",      kleur: "#E2554F", naam: "aarde",     sans: "Muladhara",    y: 0.848,
      thema: "veiligheid, grond onder je voeten" },
    { key: "sacral",    kleur: "#F0873C", naam: "verlangen", sans: "Swadhisthana", y: 0.700,
      thema: "levenslust, eigenwaarde, genieten" },
    { key: "solar",     kleur: "#F2C64C", naam: "wil",       sans: "Manipura",     y: 0.570,
      thema: "kracht, spanning, wat je voortdrijft" },
    { key: "heart",     kleur: "#4FBF86", naam: "hart",      sans: "Anahata",      y: 0.455,
      thema: "liefde, verlies, verbinding" },
    { key: "throat",    kleur: "#4A9FE2", naam: "stem",      sans: "Vishuddha",    y: 0.345,
      thema: "spreken, zwijgen, gehoord worden" },
    { key: "third_eye", kleur: "#6E62DA", naam: "inzicht",   sans: "Ajna",         y: 0.235,
      thema: "zien, weten, een voorgevoel" },
    { key: "crown",     kleur: "#B369DE", naam: "licht",     sans: "Sahasrara",    y: 0.112,
      thema: "overgave, deel van iets groters" }
  ];

  // De plaat is 576 bij 1008; in die maat wordt alles uitgerekend.
  var PLAAT_B = 576, PLAAT_H = 1008;

  var spectrumData = null;
  var spectrumKeuze = 0;

  function tekenPilaar(counts) {
    var totaal = 0, hoogste = 0;
    VELDEN.forEach(function (v) {
      var n = counts[v.key] || 0;
      totaal += n;
      if (n > hoogste) { hoogste = n; }
    });

    var svg = '<svg viewBox="0 0 ' + PLAAT_B + ' ' + PLAAT_H + '" role="img" aria-label="' +
              t("Je chakrapilaar") + '">';
    svg += '<defs><radialGradient id="doven">' +
           '<stop offset="0%" stop-color="#05030B" stop-opacity="1"/>' +
           '<stop offset="60%" stop-color="#05030B" stop-opacity=".92"/>' +
           '<stop offset="100%" stop-color="#05030B" stop-opacity="0"/>' +
           '</radialGradient></defs>';
    svg += '<image href="chakra-pilaar.jpg" x="0" y="0" width="' + PLAAT_B +
           '" height="' + PLAAT_H + '"/>';

    VELDEN.forEach(function (v) {
      var n = counts[v.key] || 0;
      var kracht = hoogste ? n / hoogste : 0;
      var cy = v.y * PLAAT_H;

      // Wat weinig voorkwam zakt terug in het donker. Nooit helemaal: de pilaar
      // hoort heel te blijven, ook als een veld dit keer niet meedeed.
      if (kracht < 0.98) {
        svg += '<ellipse cx="' + (PLAAT_B / 2) + '" cy="' + cy.toFixed(0) +
               '" rx="310" ry="84" fill="url(#doven)" opacity="' +
               ((1 - kracht) * 0.72).toFixed(2) + '"/>';
      }
      if (n) {
        svg += '<text x="' + (PLAAT_B - 20) + '" y="' + (cy + 11).toFixed(0) +
               '" class="pilaar-cijfer" fill="' + v.kleur + '">' +
               Math.round(n / totaal * 100) + '%</text>';
      }
    });
    return svg + "</svg>";
  }

  function tekenLegenda(counts) {
    var totaal = 0;
    VELDEN.forEach(function (v) { totaal += counts[v.key] || 0; });
    var doos = el("spectrum-legenda");
    doos.innerHTML = "";
    // Van boven naar beneden, zoals de pilaar staat: kruin eerst.
    VELDEN.slice().reverse().forEach(function (v) {
      var n = counts[v.key] || 0;
      var rij = document.createElement("div");
      rij.className = "legenda-rij" + (n ? "" : " stil");
      rij.innerHTML =
        '<i class="legenda-stip" style="background:' + v.kleur + ';color:' + v.kleur + '"></i>' +
        '<span class="legenda-naam">' + t(v.naam) + '</span>' +
        '<span class="legenda-sans">' + v.sans + '</span>' +
        '<span class="legenda-thema">' + t(v.thema) + '</span>' +
        '<span class="legenda-deel">' + (totaal ? Math.round(n / totaal * 100) + "%" : "0%") + '</span>';
      doos.appendChild(rij);
    });
  }

  function kiesSpectrum(nummer) {
    if (!spectrumData) { return; }
    spectrumKeuze = nummer || 0;
    var counts, wie;
    if (spectrumKeuze) {
      var gekozen = (spectrumData.dreams || []).filter(function (x) {
        return x.n === spectrumKeuze;
      })[0];
      if (!gekozen) { return; }
      counts = gekozen.counts || {};
      wie = t("Droom") + " " + gekozen.n + (gekozen.title ? " — " + gekozen.title : "");
    } else {
      counts = spectrumData.total || {};
      wie = t("Alle dromen samen") + " — " + (spectrumData.dreams || []).length + " " + t("nachten");
    }
    el("pilaar-wie").textContent = wie;
    el("pilaar").innerHTML = tekenPilaar(counts);
    tekenLegenda(counts);
    document.querySelectorAll(".kolom").forEach(function (k) {
      k.setAttribute("aria-pressed",
        parseInt(k.dataset.dream, 10) === spectrumKeuze ? "true" : "false");
    });
    el("tijd-alles").setAttribute("aria-pressed", spectrumKeuze ? "false" : "true");
  }

  /* Door welke bril je dromen tot nu toe gelezen zijn.
   *
   * Naast de chakrapilaar, want het is dezelfde soort vraag: niet wat één droom
   * betekende, maar waar je nachten zich ophouden. Chakra's gaan over gevoel,
   * dit gaat over de manier van kijken - en bij "vanzelf" koos het model, dus
   * dan zegt deze telling iets over de dromen zelf en niet over jouw voorkeur.
   */
  function toonBrilspectrum(sp) {
    var doos = el("brilspectrum");
    if (!doos) { return; }
    var tel = sp.lenses || {};
    var namen = sp.lens_names || [];
    var totaal = namen.reduce(function (som, naam) { return som + (tel[naam] || 0); }, 0);
    if (!totaal) { doos.hidden = true; return; }

    doos.hidden = false;
    var html = '<span class="brilspectrum-kop">' + t("Door welke bril") + "</span>";
    namen.forEach(function (naam) {
      var n = tel[naam] || 0;
      var deel = Math.round((n / totaal) * 100);
      html += '<div class="brilstaaf' + (n ? "" : " leeg") + '">' +
        '<span class="brilstaaf-naam">' + t(hoofdletter(naam)) + "</span>" +
        '<span class="brilstaaf-baan"><i class="bril-' + naam +
        '" style="width:' + deel + '%"></i></span>' +
        '<span class="brilstaaf-getal">' + n + "</span></div>";
    });
    doos.innerHTML = html;
  }

  function toonSpectrum(sp) {
    spectrumData = sp;
    var sectie = el("spectrum-section");
    var dromen = sp.dreams || [];
    toonBrilspectrum(sp);
    /* Vanaf de eerste droom.
     *
     * Hier stond een drempel van drie, met het argument dat minder alleen ruis
     * geeft. Dat klopte voor de tijdlijn maar niet voor de pilaar: één droom is
     * al vijf panelen met vijf gekozen velden, en dat is een echte verdeling.
     * En de kosten van verbergen zijn hoger dan gedacht - wie hem niet ziet weet
     * niet dat hij bestaat, en dit is precies het deel waar mensen voor
     * terugkomen. Een nieuwe tester zag hem de eerste drie ochtenden dus nooit.
     */
    if (!dromen.length) { sectie.hidden = true; return; }
    sectie.hidden = false;
    // Wel eerlijk zijn dat het pas een patroon wordt als er meer nachten zijn.
    var noot = el("spectrum-noot");
    if (noot) {
      noot.hidden = dromen.length >= 3;
      noot.textContent = t("Nog vroeg: met een paar nachten erbij gaat dit ergens op lijken.");
    }

    var doos = el("spectrum");
    doos.innerHTML = "";
    dromen.forEach(function (d) {
      var kolom = document.createElement("button");
      kolom.type = "button";
      kolom.className = "kolom";
      kolom.dataset.dream = d.n;
      kolom.title = t("Droom") + " " + d.n + (d.title ? " — " + d.title : "");
      kolom.setAttribute("aria-label", kolom.title);

      var stapel = document.createElement("div");
      stapel.className = "stapel";
      VELDEN.slice().reverse().forEach(function (v) {
        var n = (d.counts || {})[v.key] || 0;
        if (!n) { return; }
        var blok = document.createElement("span");
        blok.className = "veld";
        blok.style.background = v.kleur;
        blok.style.flexGrow = n;
        stapel.appendChild(blok);
      });
      var nummer = document.createElement("span");
      nummer.className = "kolom-nr";
      nummer.textContent = d.n;
      kolom.appendChild(stapel);
      kolom.appendChild(nummer);
      kolom.addEventListener("click", function () { kiesSpectrum(d.n); });
      doos.appendChild(kolom);
    });

    // Bij het herladen dezelfde keuze terug, zodat een taalwissel je niet
    // terugzet naar het totaal.
    kiesSpectrum(spectrumKeuze);
  }

  if (el("tijd-alles")) {
    el("tijd-alles").addEventListener("click", function () { kiesSpectrum(0); });
  }

  function laadSpectrum() {
    fetch("/api/spectrum")
      .then(function (r) { return r.json(); })
      .then(toonSpectrum)
      .catch(function () { /* het spectrum is een extraatje */ });
  }

  /* De chakralaag staat dicht tot je hem opent.
   *
   * Hij was mooi maar te aanwezig: een pilaar met zeven lotussen midden in de
   * pagina zegt tegen iemand die hier voor een duiding komt dat dit een
   * spiritueel product is, en dat is een keuze die de dromer hoort te maken.
   * Tegelijk gold het oude bezwaar nog: wie hem niet ziet weet niet dat hij
   * bestaat, en dit is een deel waar mensen voor terugkomen. Dus blijft de kop
   * staan en gaat alleen de inhoud dicht.
   *
   * De keuze blijft in deze browser staan. Niet in het profiel: het is geen
   * eigenschap van de dromer maar van hoe hij vanochtend kijkt, en een
   * serververzoek voor het open- en dichtklappen van een paneel is te veel.
   */
  var SPECTRUM_OPEN = "dreamverse_spectrum_open";

  function spectrumStaatOpen() {
    try { return localStorage.getItem(SPECTRUM_OPEN) === "1"; } catch (e) { return false; }
  }

  function spectrumUitklap(open) {
    var doos = el("spectrum-inhoud");
    var knop = el("spectrum-knop");
    if (!doos || !knop) { return; }
    doos.hidden = !open;
    knop.setAttribute("aria-expanded", open ? "true" : "false");
    knop.textContent = open ? t("Verbergen") : t("Bekijken");
    try { localStorage.setItem(SPECTRUM_OPEN, open ? "1" : "0"); } catch (e) { /* niets */ }
  }

  if (el("spectrum-knop")) {
    spectrumUitklap(spectrumStaatOpen());
    el("spectrum-knop").addEventListener("click", function () {
      var open = el("spectrum-inhoud").hidden;
      spectrumUitklap(open);
      // Bij het openen even laten zien waar je heen kijkt; anders klapt er
      // ergens onder je scherm iets uit.
      if (open) {
        el("spectrum-inhoud").scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }

  /* -------------------------------------------------------------- archief */

  function renderArchive(dreams) {
    archiveEl.innerHTML = "";
    if (!dreams.length) {
      var empty = document.createElement("div");
      empty.className = "entry";
      empty.textContent = t("Nog leeg. Je eerste droom wordt Droom 1.");
      archiveEl.appendChild(empty);
      return;
    }
    dreams.forEach(function (d) {
      var row = document.createElement("div");
      row.className = "entry";
      // Het kernmoment ernaast: dat is wat de droom terugbrengt. Bewoog het,
      // dan speelt de video zachtjes mee; anders staat de tekening er.
      var mini = document.createElement("div");
      mini.className = "mini";
      if (d.clip) {
        var mv = document.createElement("video");
        mv.src = d.clip; mv.muted = true; mv.loop = true;
        mv.playsInline = true; mv.autoplay = true; mv.preload = "metadata";
        mini.appendChild(mv);
        mini.classList.add("bewoog");
      } else if (d.thumb) {
        var mi = document.createElement("img");
        mi.src = d.thumb; mi.alt = ""; mi.loading = "lazy";
        mini.appendChild(mi);
      } else {
        mini.classList.add("leeg");
      }

      var no = document.createElement("span"); no.className = "no"; no.textContent = "Droom " + d.n;
      var txt = document.createElement("span"); txt.className = "txt"; txt.textContent = d.title || d.text;
      var weg = document.createElement("button");
      weg.type = "button";
      weg.className = "wis";
      weg.title = t("Deze droom verwijderen");
      weg.setAttribute("aria-label", "Droom " + d.n + " verwijderen");
      weg.textContent = "×";
      weg.addEventListener("click", function (e) {
        e.stopPropagation();
        if (!window.confirm(t("Droom") + " " + d.n + " " + t("verwijderen? De panelen en de animatie gaan mee."))) { return; }
        fetch("/api/dream/" + d.n, { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function () { loadArchive(); laadAccount(); })
          .catch(function () {});
      });

      row.appendChild(mini); row.appendChild(no); row.appendChild(txt); row.appendChild(weg);
      row.tabIndex = 0;
      row.title = t("Terugkijken");
      row.addEventListener("click", function () { herbekijk(d.n); });
      row.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); herbekijk(d.n); }
      });
      archiveEl.appendChild(row);
    });
  }

  // De duiding terugschrijven bij panelen die er al liggen. De droomtekst zelf
  // staat nog in het archief, dus er hoeft geen beeld opnieuw gemaakt te worden.
  function herstel(nummer) {
    statusEl.className = "status";
    statusEl.textContent = t("De duiding wordt opnieuw geschreven bij je panelen…");
    verwachtWerk();
    startBezig(t("De duiding wordt opnieuw geschreven"));
    fetch("/api/episode/" + nummer + "/herstel", { method: "POST" })
      .then(lees)
      .then(function (res) {
        if (!res.ok) { throw new Error(res.body.error || t("Herstellen lukte niet.")); }
        render(res.body.episode);
        pollPanels(nummer, 3);
        statusEl.className = "status";
        statusEl.textContent = t("Droom %s is weer compleet.").replace("%s", nummer);
        stopBezig();
      })
      .catch(function (e) {
        statusEl.className = "status err";
        statusEl.textContent = e.message;
      })
  }

  // Terugkijken kost niets: tekst, panelen en video staan al op de schijf.
  function herbekijk(nummer) {
    statusEl.className = "status";
    statusEl.textContent = t("Droom %s terughalen…").replace("%s", nummer);
    fetch("/api/episode/" + nummer)
      .then(lees)
      .then(function (res) {
        if (!res.ok) { throw new Error(res.body.error || t("Terughalen lukte niet.")); }
        var ep = res.body.episode;
        render(ep);
        if (ep.answer) {
          el("antwoord").value = ep.answer;
          el("antwoord-blok").classList.add("bewaard");
          el("antwoord-uitleg").textContent = t("Dit antwoord telt mee in je volgende duiding.");
        }
        // De beelden en de video die er al zijn ophalen, zonder iets te maken.
        pollPanels(nummer, 3);
        if (ep.onvolledig) {
          // Van voor het bewaren: wel beeld, geen tekst. Opnieuw schrijven mag,
          // en kost niets, want het beeld staat er al.
          statusEl.className = "status";
          statusEl.innerHTML = t("Bij deze droom is alleen het beeld bewaard gebleven.") + " " +
            "<button type=\"button\" class=\"herstel\" id=\"herstel-" + nummer + "\">" +
            t("Schrijf de duiding opnieuw") + "</button> — " + t("gratis, de panelen blijven staan.");
          el("herstel-" + nummer).addEventListener("click", function () { herstel(nummer); });
        } else {
          statusEl.textContent = t("Droom %s — al eerder gemaakt, kost je niets.").replace("%s", nummer);
        }
        player.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function (e) {
        statusEl.className = "status err";
        statusEl.textContent = e.message;
      });
  }

  // De keuzelijst bij "Los te koop" vullen met je dromen.
  var keuzeDromen = [];

  function vulKeuzelijst(dreams) {
    keuzeDromen = dreams || [];
    var kies = el("kies");
    if (!kies) { return; }
    kies.innerHTML = "";
    dreams.forEach(function (d) {
      var o = document.createElement("option");
      o.value = d.n;
      // Een droom zonder panelen stond hier uitgeschakeld, want bewegend beeld
      // heeft een getekend paneel nodig. Maar sinds je panelen los kunt kopen is
      // dat juist de droom die je wilt kiezen - hij was niet te selecteren voor
      // precies het ding dat hem zou helpen.
      o.textContent = t("Droom") + " " + d.n + " — " +
                      (d.title || d.text || "").slice(0, 40) +
                      (d.thumb ? "" : "  (" + t("nog geen beeld") + ")");
      kies.appendChild(o);
    });
    if (!dreams.length) {
      var leeg = document.createElement("option");
      leeg.textContent = t("nog geen dromen");
      leeg.value = "";
      kies.appendChild(leeg);
    }
    // Liefst een droom met beeld voorop, want daar is het meeste voor te koop.
    // Is die er niet, dan gewoon de eerste: panelen bijmaken kan wel.
    var metBeeld = dreams.filter(function (d) { return d.thumb; })[0];
    kies.value = String((metBeeld || dreams[0] || {}).n || "");
    zetKoopKnoppen(keuzeDromen);
  }

  /* Welke knoppen mogen bij de gekozen droom?
   *
   * Heeft hij panelen, dan alles behalve panelen bijmaken. Heeft hij ze niet,
   * dan alleen panelen bijmaken - de rest heeft een getekend paneel nodig als
   * startframe. Zo hoef je niet te klikken om te horen dat het niet kan.
   */
  function zetKoopKnoppen(dreams) {
    var kies = el("kies");
    if (!kies) { return; }
    var nummer = Number(kies.value);
    var droom = (dreams || []).filter(function (d) { return d.n === nummer; })[0];
    var heeftBeeld = !!(droom && droom.thumb);
    document.querySelectorAll(".kies-droom .koop").forEach(function (b) {
      var isPanelen = b.dataset.kind === "panelen";
      b.disabled = !droom || (isPanelen ? heeftBeeld : !heeftBeeld);
      b.title = b.disabled
        ? (isPanelen ? t("Bij deze droom staan de panelen er al.")
                     : t("Deze droom heeft nog geen panelen. Maak die eerst."))
        : "";
    });
  }

  function loadArchive() {
    fetch("/api/archive")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        aantalDromen = (d.dreams || []).length;
        // Wanneer was welke droom? De draden verwijzen met "Droom 12", en dan
        // is de datum meer waard dan het woord "toen".
        wanneerPerDroom = {};
        (d.dreams || []).forEach(function (x) {
          if (x && x.n) { wanneerPerDroom[x.n] = x.when || ""; }
        });
        renderArchive(d.dreams || []);
        vulKeuzelijst(d.dreams || []);
        laadSpectrum();
        var samen = d.samen || {};
        toonSamen(samen.number, samen.together, samen.threads, samen.symbols);
      })
      .catch(function () { /* archief is bijzaak; de app werkt zonder */ });
  }

  /* ------------------------------------------------------------- inspreken */

  var Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recogniser = null, listening = false;

  /* Kijkt iemand mee vanuit de app van Instagram?
   *
   * Instagram opent een link niet in Safari of Chrome maar in een browser die
   * hij zelf in de app heeft zitten, en dat is precies de weg waarlangs
   * iedereen van de bio-link binnenkomt. In die browser bestaat de Web Speech
   * API niet: op een iPhone zit `webkitSpeechRecognition` alleen in Safari
   * zelf. Dus zeggen we "Inspreken kan alleen in Chrome en Edge" tegen iemand
   * die Chrome misschien wel op zijn telefoon heeft staan - en er staat een
   * oplossing van twee tikken achter.
   *
   * Alleen Instagram, met opzet. De browser van Facebook (FBAN, FBAV, FB_IAB)
   * doet precies hetzelfde en is één regexp erbij, maar zolang de bio-link het
   * enige kanaal is hoort er niet meer te staan dan we gemeten hebben.
   */
  function instagramBrowser() {
    return /Instagram/i.test(navigator.userAgent || "");
  }

  /* Waarom inspreken hier niet kan, met wat je eraan doet. Nederlands, want dit
   * is de brontekst waar de vertaalslag op zoekt. */
  function geenSpraakUitleg() {
    return instagramBrowser()
      ? "Je bekijkt Dreamverse in de browser van Instagram, en inspreken kan"
        + " daar niet. Tik op de drie puntjes en kies Openen in Safari of"
        + " Openen in Chrome. Of typ je droom hierboven."
      : "Inspreken kan alleen in Chrome en Edge. Typ je droom hierboven.";
  }

  /* De hint onder het invoerveld. Ook `data-nl` zetten, want de vertaalslag
   * legt de begintekst van elk element vast en herstelt daaruit bij een
   * taalwissel - zonder deze regel stond er na een klik op EN/NL weer "of typ
   * het hierboven" en was de uitleg weg. In `data-nl` hoort de Nederlandse
   * zin, niet de vertaalde: dat veld is de bron en niet wat er staat. */
  function hintVervangen(hint, bron) {
    if (!hint) { return; }
    hint.classList.add("kan-niet");
    hint.dataset.nl = bron;
    hint.textContent = t(bron);
  }

  /* Het balkje: laat zien dat de microfoon je hoort.
   *
   * SpeechRecognition geeft geen geluidsniveau terug - alleen woorden, en pas
   * als het er woorden van kan maken. Tot dat moment is er geen enkel teken van
   * leven, en wie zijn droom inspreekt terwijl de verkeerde microfoon aanstaat
   * merkt het pas als hij klaar is. Daarom een tweede, eigen stream met een
   * analyser erop.
   *
   * Twee dingen die hier goed moeten. De stream moet echt gestopt worden, want
   * anders blijft het opnamelampje van het tabblad branden nadat je op stop hebt
   * gedrukt - dan lijkt het alsof de app blijft meeluisteren. En als dit hele
   * ding niet lukt, mag het inspreken er niet aan onderdoor gaan: het balkje is
   * een hulpmiddel, geen voorwaarde.
   */
  var METER_BALKJES = 14;
  var meterStaat = null;

  // De meter hangt aan een element-id, want er zijn er twee: de invoer in de
  // app en het eerste scherm waar iemand zonder account zijn droom vertelt.
  function meterBouwen(id) {
    var doos = el(id || "mic-meter");
    if (!doos || doos.childNodes.length) { return doos; }
    for (var i = 0; i < METER_BALKJES; i++) {
      var b = document.createElement("i");
      // Oplopend, zoals een niveaumeter eruitziet.
      b.style.height = Math.round(6 + (i / (METER_BALKJES - 1)) * 14) + "px";
      doos.appendChild(b);
    }
    return doos;
  }

  function meterStoppen() {
    var s = meterStaat;
    meterStaat = null;
    if (!s) { return; }
    if (s.frame) { cancelAnimationFrame(s.frame); }
    try { s.stream.getTracks().forEach(function (tr) { tr.stop(); }); } catch (e) { /* al weg */ }
    try { s.ctx.close(); } catch (e) { /* al dicht */ }
    var doos = el("mic-meter");
    if (doos) {
      doos.classList.remove("aan", "stil");
      doos.querySelectorAll("i").forEach(function (b) { b.classList.remove("op"); });
    }
  }

  function meterStarten(id) {
    var doos = meterBouwen(id);
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!doos || !Ctx || !navigator.mediaDevices) { return; }

    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      // Ondertussen op stop gedrukt: niet alsnog opengaan.
      if (!listening) {
        stream.getTracks().forEach(function (tr) { tr.stop(); });
        return;
      }
      var ctx = new Ctx();
      var analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.6;
      ctx.createMediaStreamSource(stream).connect(analyser);
      var data = new Uint8Array(analyser.frequencyBinCount);
      var balkjes = [].slice.call(doos.querySelectorAll("i"));
      doos.classList.add("aan");

      var stilSinds = Date.now(), gewaarschuwd = false;
      var s = { stream: stream, ctx: ctx, frame: 0 };
      meterStaat = s;

      (function teken() {
        if (meterStaat !== s) { return; }
        s.frame = requestAnimationFrame(teken);
        analyser.getByteFrequencyData(data);
        var som = 0;
        for (var i = 0; i < data.length; i++) { som += data[i] * data[i]; }
        var rms = Math.sqrt(som / data.length) / 255;
        // Wortel eroverheen: praten op normale sterkte moet het balkje vullen,
        // niet twee streepjes oplichten.
        var aan = Math.min(METER_BALKJES, Math.round(Math.sqrt(rms) * 1.9 * METER_BALKJES));
        for (var j = 0; j < balkjes.length; j++) {
          balkjes[j].classList.toggle("op", j < aan);
        }

        if (aan > 1) {
          stilSinds = Date.now();
          if (gewaarschuwd) {
            gewaarschuwd = false;
            doos.classList.remove("stil");
            guideLine.textContent = t("Ik luister. Neem de tijd.");
          }
        } else if (!gewaarschuwd && Date.now() - stilSinds > 4000) {
          gewaarschuwd = true;
          doos.classList.add("stil");
          guideLine.textContent = t("Ik hoor nog niets. Staat de juiste microfoon aan?");
        }
      })();
    }).catch(function () {
      /* Geen balkje dan. Het inspreken zelf loopt hier niet op stuk. */
    });
  }

  function setupMic() {
    var mic = el("mic");
    if (!Recognition) {
      // Firefox, Safari en iPhone kennen de Web Speech API niet. Dat stond
      // alleen in een title-tooltip: onzichtbaar op een telefoon en makkelijk
      // te missen op een laptop. Wat je overhoudt is een grijze knop die niets
      // doet zonder te zeggen waarom - en dan denk je dat de app stuk is.
      mic.disabled = true;
      mic.title = instagramBrowser()
        ? t("Inspreken kan niet in de browser van Instagram")
        : t("Inspreken werkt in Chrome en Edge");
      hintVervangen(document.querySelector(".invoer-hint"), geenSpraakUitleg());
      return;
    }
    mic.addEventListener("click", function () {
      if (listening) { recogniser.stop(); return; }
      recogniser = new Recognition();
      // Volgde de taal niet: een Engelse gebruiker sprak in en kreeg
      // Nederlands teruggeschreven, wat als onzin op je scherm belandt.
      recogniser.lang = taalcode();
      recogniser.continuous = true;
      recogniser.interimResults = true;

      var settled = input.value ? input.value + " " : "";

      recogniser.onstart = function () {
        listening = true;
        mic.classList.add("rec");
        mic.textContent = t("Stop met opnemen");
        guide.classList.add("listening");
        guideLine.textContent = t("Ik luister. Neem de tijd.");
        meterStarten();
      };
      recogniser.onresult = function (e) {
        var live = "";
        for (var i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) { settled += e.results[i][0].transcript + " "; }
          else { live += e.results[i][0].transcript; }
        }
        input.value = (settled + live).replace(/\s+/g, " ").trimStart();
      };
      recogniser.onerror = function (e) {
        statusEl.className = "status err";
        statusEl.textContent = t(spraakfout(e.error));
      };
      recogniser.onend = function () {
        listening = false;
        meterStoppen();
        mic.classList.remove("rec");
        mic.textContent = t("Inspreken");
        guide.classList.remove("listening");
        guideLine.textContent = input.value
          ? t("Genoteerd. Zal ik je droom verbeelden?")
          : t("Ik heb niets opgevangen. Probeer het nog eens.");
      };
      recogniser.start();
    });
  }

  /* ------------------------------------------- meeschrijven met het gesprek */

  /* Wat je Vera vertelt, wordt de invoer voor je verbeelding.
   *
   * Tot nu toe was een gesprek een doodlopende weg: je vertelde je droom, Vera
   * duidde hem, en daarna was er niets - geen tekst, geen panelen, geen chakra,
   * en hij telde ook niet mee in de duiding van alle dromen samen. Precies het
   * deel waar dit product om gaat.
   *
   * Dus schrijft de browser mee terwijl je praat. De herkenning loopt náást de
   * verbinding met Runway; die stuurt geen tekst terug, dus dit is de enige
   * plek waar de woorden bestaan.
   *
   * Wat er níet gebeurt: hier automatisch een verbeelding van maken. Dat kost
   * geld en soms tokens, en een verbeelding van een tekst die je nog niet hebt
   * gezien is een verbeelding die je niet gevraagd hebt. De tekst gaat in de
   * invoer, jij kijkt hem na, jij klikt.
   */
  var gesprekTekst = "";
  var gesprekLuisteraar = null;

  function taalcode() {
    return ((profiel && profiel.language) || "nl") === "en" ? "en-US" : "nl-NL";
  }

  /* Wat de spraakherkenning zegt als het misgaat, in mensentaal.
   *
   * De ruwe code kwam op het scherm: "Meeschrijven stopte: service-not-allowed".
   * Dat is jargon uit een API en zegt een dromer niets, terwijl er in dit geval
   * een oplossing van één tik achter zit. Op een iPhone komt die code van een
   * privévenster of van dictaat dat uitstaat, en dat kun je gewoon zeggen.
   */
  function spraakfout(code) {
    // In de browser van Instagram is dit geen storing maar de browser zelf: die
    // komt niet bij de microfoon en niet bij de spraakdienst. Op Android
    // bestaat SpeechRecognition daar wél, dus komt het daar niet naar buiten
    // als een ontbrekende functie maar als een van deze drie codes - en dan
    // stond er "zet de microfoon aan bij je site-instellingen", wat in die
    // browser niet bestaat.
    if (instagramBrowser() && (code === "not-allowed"
                               || code === "service-not-allowed"
                               || code === "network")) {
      return ("Inspreken kan niet in de browser van Instagram. Tik op de drie "
              + "puntjes en kies Openen in Safari of Openen in Chrome.");
    }
    return {
      "service-not-allowed":
        "De spraakdienst van je toestel doet niet mee. Op een iPhone komt dat "
        + "meestal door een privévenster, of doordat Dicteren uitstaat bij "
        + "Instellingen, Algemeen, Toetsenbord.",
      "not-allowed":
        "De microfoon is geweigerd. Zet hem aan bij de site-instellingen van je "
        + "browser.",
      "audio-capture":
        "Er is geen microfoon gevonden.",
      "network":
        "Spraak naar tekst kon het net niet op. Op een bedrijfsnetwerk zit daar "
        + "soms een firewall tussen.",
      "language-not-supported":
        "Deze taal kent de spraakherkenning niet."
    }[code] || ("Meeschrijven stopte: " + code);
  }

  function meeschrijvenStarten() {
    if (!Recognition) {
      // Firefox en Safari kunnen dit niet. Dat eerlijk zeggen is beter dan een
      // gesprek dat stil verdwijnt. In de browser van Instagram is het niet de
      // browser van de dromer maar die van de app, en dat is iets anders om te
      // zeggen: daar kan hij er zelf uit stappen.
      // Twee losse aanroepen met de zin er compleet in, en niet één aanroep om
      // een keuze heen: build/controle.py zoekt naar een t met de hele zin er
      // letterlijk in, dus een zin die eerst wordt samengesteld valt buiten
      // die controle.
      meeschrijfMelding(instagramBrowser()
        ? t("In de browser van Instagram schrijft Dreamverse niet mee.")
        : t("Meeschrijven kan alleen in Chrome en Edge."), true);
      return;
    }
    if (listening && recogniser) { try { recogniser.stop(); } catch (e) { /* al gestopt */ } }

    gesprekTekst = "";
    var r = new Recognition();
    r.lang = taalcode();
    r.continuous = true;
    r.interimResults = false;

    r.onresult = function (e) {
      for (var i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          gesprekTekst += e.results[i][0].transcript + " ";
        }
      }
      meeschrijfMelding(woordenMelding(gesprekTekst));
    };
    r.onerror = function (e) {
      if (e.error === "no-speech" || e.error === "aborted") { return; }
      meeschrijfMelding(t(spraakfout(e.error)), true);
    };
    r.onend = function () {
      // De herkenning stopt zichzelf na een stilte. Zolang het gesprek loopt
      // gaat hij weer aan, anders mis je de tweede helft van je droom.
      if (gesprekLuisteraar === r && room) {
        try { r.start(); } catch (e) { /* mag mislukken */ }
      }
    };

    gesprekLuisteraar = r;
    try {
      r.start();
      meeschrijfMelding(t("Ik schrijf mee"));
    } catch (e) {
      meeschrijfMelding(t("Meeschrijven kwam niet op gang."), true);
    }
  }

  function meeschrijvenStoppen() {
    var r = gesprekLuisteraar;
    gesprekLuisteraar = null;
    if (r) { try { r.stop(); } catch (e) { /* al gestopt */ } }
    var doos = el("call-meeschrijf");
    if (doos) { doos.hidden = true; }
  }

  function woordenMelding(tekst) {
    var n = tekst.trim() ? tekst.trim().split(/\s+/).length : 0;
    return t("Ik schrijf mee") + " · " + n + " " + t(n === 1 ? "woord" : "woorden");
  }

  function meeschrijfMelding(tekst, mis) {
    var doos = el("call-meeschrijf");
    if (!doos) { return; }
    doos.hidden = false;
    doos.className = "call-meeschrijf" + (mis ? " mis" : "");
    doos.textContent = tekst;
  }

  /* Na het gesprek: de woorden in de invoer, en zeggen wat er nu kan.
   *
   * Niet overschrijven wat er al stond - daar kan een droom in staan die je
   * net had getypt. Dan komt het eronder.
   */
  function gesprekOogsten() {
    var tekst = gesprekTekst.replace(/\s+/g, " ").trim();
    gesprekTekst = "";
    if (tekst.split(/\s+/).length < 4) {
      // Te weinig om een droom van te maken. Niets in de invoer duwen.
      return false;
    }
    input.value = input.value.trim() ? input.value.trim() + " " + tekst : tekst;
    gesprekBewaren(input.value);
    statusEl.className = "status";
    statusEl.textContent = t("Dit heb ik uit je gesprek opgeschreven. Lees het na — "
      + "haal eruit wat Vera zei en wat er niet bij hoort. Daarna verbeeldt hij "
      + "hem, en telt hij mee in je chakra's en in de duiding van alle dromen.");
    guideLine.textContent = t("Ik heb het opgeschreven. Kijk het na.");
    input.focus();
    input.scrollIntoView({ behavior: "smooth", block: "center" });
    return true;
  }

  /* Een ingesproken droom overleeft een verse pagina.
   *
   * De tekst bestaat alleen in dat ene tekstvak. Een verdwaalde verversing na
   * een gesprek van vijf minuten kost dan een droom die je net verteld hebt en
   * niet meer terug kunt halen - en de minuten met Vera waren al afgerekend.
   * Een uur is de grens: daarna is het geen "net ingesproken" meer.
   */
  var GESPREK_OPSLAG = "dreamverse_gesprek";

  function gesprekBewaren(tekst) {
    try {
      localStorage.setItem(GESPREK_OPSLAG,
        JSON.stringify({ tekst: tekst, wanneer: Date.now() }));
    } catch (e) { /* opslag kan geweigerd zijn; dan is het jammer */ }
  }

  function gesprekTerughalen() {
    var rauw = null;
    try { rauw = localStorage.getItem(GESPREK_OPSLAG); } catch (e) { return; }
    if (!rauw) { return; }
    var d = null;
    try { d = JSON.parse(rauw); } catch (e) { return; }
    // Eenmalig: hierna staat hij in de invoer en hoort hij daar thuis.
    try { localStorage.removeItem(GESPREK_OPSLAG); } catch (e) { /* niets */ }
    if (!d || !d.tekst) { return; }
    if (Date.now() - (d.wanneer || 0) > 3600000) { return; }
    if (input.value.trim()) { return; }
    input.value = d.tekst;
    statusEl.className = "status";
    statusEl.textContent = t("Dit stond nog van je gesprek met Vera. Ik heb het bewaard.");
  }

  gesprekTerughalen();

  /* ------------------------------------------------------------ veiligheid */

  /* Waar iemand naartoe kan, als een droom daarover ging.
   *
   * Drie regels, en ze zijn geen van drieën onderhandelbaar.
   *
   * 1. **Geen letter komt uit een model.** Het model classificeert alleen; deze
   *    nummers staan hier in de code. Een gehallucineerd crisisnummer is het
   *    ergste wat deze app kan doen.
   * 2. **Alleen wat nagekeken is.** In LANDEN staat uitsluitend wat bij de bron
   *    is geverifieerd. Een land dat er niet in staat krijgt geen nummer, en
   *    dat is beter dan een nummer dat daar niet werkt.
   * 3. **Er is altijd een vangnet.** Find A Helpline (ThroughLine) houdt
   *    hulplijnen bij in ruim 175 landen en heeft een pagina per land. Dat is
   *    beter onderhouden dan een lijst die wij bijhouden, dus die link staat er
   *    altijd bij - ook als we het land wel kennen.
   *
   * Een land toevoegen is één regel in LANDEN. Doe dat alleen met de bron erbij.
   */
  var HELPLINE = "https://findahelpline.com/";

  var LANDEN = {
    nl: {
      naam: "Nederland", nood: "112",
      suicide: [
        { naam: "113 Zelfmoordpreventie", waarde: "113", href: "tel:113",
          noot: "dag en nacht, gratis" },
        { naam: "Of gratis", waarde: "0800-0113", href: "tel:08000113", noot: "" },
        { naam: "Online", waarde: "113.nl", href: "https://www.113.nl", noot: "" }
      ],
      geweld: [
        { naam: "Veilig Thuis", waarde: "0800-2000", href: "tel:08002000",
          noot: "gratis, dag en nacht" },
        { naam: "Online", waarde: "veiligthuis.nl",
          href: "https://www.veiligthuis.nl/nl", noot: "" }
      ]
    },
    be: {
      naam: "België", nood: "112",
      suicide: [
        { naam: "Zelfmoordlijn", waarde: "1813", href: "tel:1813",
          noot: "dag en nacht, gratis" },
        { naam: "Online", waarde: "zelfmoord1813.be",
          href: "https://www.zelfmoord1813.be", noot: "" }
      ],
      geweld: [
        { naam: "Nulijn geweld en misbruik", waarde: "1712", href: "tel:1712",
          noot: "gratis en anoniem" },
        { naam: "Online", waarde: "1712.be", href: "https://www.1712.be", noot: "" }
      ]
    },
    de: {
      naam: "Deutschland", nood: "112",
      suicide: [
        { naam: "TelefonSeelsorge", waarde: "0800 111 0 111", href: "tel:08001110111",
          noot: "rund um die Uhr, kostenlos" },
        { naam: "Auch", waarde: "0800 111 0 222", href: "tel:08001110222", noot: "" }
      ],
      geweld: [
        { naam: "Hilfetelefon Gewalt gegen Frauen", waarde: "116 016",
          href: "tel:116016", noot: "kostenlos, rund um die Uhr" },
        { naam: "Online", waarde: "hilfetelefon.de",
          href: "https://www.hilfetelefon.de", noot: "" }
      ]
    },
    gb: {
      naam: "United Kingdom", nood: "999",
      suicide: [
        { naam: "Samaritans", waarde: "116 123", href: "tel:116123",
          noot: "day and night, free" }
      ],
      geweld: [
        { naam: "National Domestic Abuse Helpline", waarde: "0808 2000 247",
          href: "tel:08082000247", noot: "24 hours, free" }
      ]
    },
    us: {
      naam: "United States", nood: "911",
      suicide: [
        { naam: "Suicide & Crisis Lifeline", waarde: "988", href: "tel:988",
          noot: "day and night, free" }
      ],
      geweld: [
        { naam: "National Domestic Violence Hotline", waarde: "1-800-799-7233",
          href: "tel:18007997233", noot: "24 hours, free" }
      ]
    }
  };

  /* In welk land is deze dromer waarschijnlijk?
   *
   * Zonder het te vragen en zonder zijn IP-adres ergens heen te sturen. Eerst de
   * regio uit de taalinstelling van de browser ("de-DE" -> de), want die is het
   * nauwkeurigst als hij er staat. Anders de tijdzone, voor de landen die we
   * kennen. Weten we het niet, dan blijft het leeg - en dan doet Find A Helpline
   * het werk.
   */
  var ZONES = {
    "Europe/Amsterdam": "nl", "Europe/Brussels": "be", "Europe/Berlin": "de",
    "Europe/London": "gb", "Europe/Busingen": "de"
  };

  function landcode() {
    try {
      var talen = navigator.languages || [navigator.language || ""];
      for (var i = 0; i < talen.length; i++) {
        var deel = String(talen[i]).split("-");
        if (deel.length > 1) {
          var code = deel[deel.length - 1].toLowerCase();
          if (LANDEN[code]) { return code; }
        }
      }
      var zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (ZONES[zone]) { return ZONES[zone]; }
      if (/^America\//.test(zone) && /^en/i.test(navigator.language || "")) {
        // Grof, en daarom alleen voor het noodnummer en met de zoeker erbij.
        return null;
      }
    } catch (e) { /* dan weten we het niet */ }
    return null;
  }

  var TEKST = {
    nl: {
      kopSuicide: "Praat erover met iemand.",
      suicide: "In je droom kwam zelfdoding voor. Denk je hier ook wakker aan, "
             + "praat er dan vandaag met iemand over: iemand die je vertrouwt, of "
             + "je huisarts.",
      kopGeweld: "Praat erover met iemand.",
      geweld: "Er kwam geweld voor in je droom. Speelt er in je leven iets waar "
            + "geweld bij komt, dan hoef je dat niet alleen op te lossen. Praat met "
            + "iemand die je vertrouwt.",
      nood: "Direct gevaar",
      zoeker: "Hulplijnen in jouw land",
      elders: "Woon je ergens anders, dan vind je daar de hulplijnen van jouw land."
    },
    en: {
      kopSuicide: "Talk to someone about it.",
      suicide: "Your dream involved suicide. If this is on your mind when you are "
             + "awake too, talk to someone today: someone you trust, or your doctor.",
      kopGeweld: "Talk to someone about it.",
      geweld: "Your dream involved violence. If something in your life involves "
            + "violence, you do not have to solve it alone. Talk to someone you trust.",
      nood: "Immediate danger",
      zoeker: "Helplines in your country",
      elders: "Living somewhere else? That page lists the helplines for your country."
    }
  };

  /* Het hulpkader boven de duiding.
   *
   * Boven, niet onder: wie dit nodig heeft moet het zien voordat hij begint te
   * lezen. En de duiding zelf gaat er niet over - het model heeft opdracht om
   * geen hulp aan te raden, juist zodat het niet over deze nummers kan liegen.
   */
  function toonZorg(ep) {
    var doos = el("zorg-kader");
    if (!doos) { return; }
    var soorten = (ep && ep.zorg) || [];
    var taal = (profiel && profiel.language) === "en" ? "en" : "nl";
    var w = TEKST[taal];
    var land = LANDEN[landcode()] || null;
    var stukken = [];

    ["suicide", "geweld"].forEach(function (soort) {
      if (soorten.indexOf(soort) === -1) { return; }
      var html = '<div class="zorg-blok zorg-' + soort + '">' +
        '<p class="zorg-kop">' + (soort === "suicide" ? w.kopSuicide : w.kopGeweld) +
        "</p><p>" + (soort === "suicide" ? w.suicide : w.geweld) + "</p><ul>";

      // Wat we van dit land weten. Kennen we het land niet, dan slaan we dit
      // over - een nummer uit een ander land is erger dan geen nummer.
      (land ? land[soort] : []).forEach(function (r) {
        html += regel(r.naam, r.waarde, r.href, r.noot);
      });
      if (land && land.nood) {
        html += regel(w.nood, land.nood, "tel:" + land.nood.replace(/\s/g, ""), "");
      }
      // En altijd de zoeker: ruim 175 landen, door mensen die dit bijhouden.
      html += regel(w.zoeker, "findahelpline.com",
                    HELPLINE + (land ? "countries/" + landcode() : ""), "");
      html += "</ul>";
      if (!land) { html += '<p class="zorg-elders">' + w.elders + "</p>"; }
      html += "</div>";
      stukken.push(html);
    });

    doos.innerHTML = stukken.join("");
    doos.hidden = !stukken.length;
  }

  function regel(naam, waarde, href, noot) {
    var extern = href.indexOf("http") === 0;
    return "<li><span>" + naam + "</span> " +
      '<a href="' + href + '"' + (extern ? ' target="_blank" rel="noopener"' : "") +
      ">" + waarde + "</a>" +
      (noot ? " <em>" + noot + "</em>" : "") + "</li>";
  }

  /* Buiten bereik: geen verbeelding, wel een antwoord.
   *
   * Geen foutmelding en geen rode balk - er is niets stukgegaan en de dromer
   * heeft niets verkeerd gedaan. Er is ook niets afgerekend, en dat zeggen we,
   * anders gaat iemand zijn tokens natellen.
   */
  function buitenBereik() {
    statusEl.className = "status";
    statusEl.textContent = t("Deze droom is niet verbeeld en heeft je niets gekost.");
    guideLine.textContent = t("Hier ga ik niet over.");
    var doos = el("zorg-kader");
    if (doos) {
      doos.hidden = false;
      doos.innerHTML = '<div class="zorg-blok zorg-bereik">' +
        '<p class="zorg-kop">' + t("Dit valt buiten wat ik doe.") + "</p><p>" +
        t("Je droom was uitgesproken seksueel. Daar maak ik geen verbeelding van "
          + "en daar schrijf ik geen duiding over - niet omdat er iets mis is met "
          + "je droom, maar omdat het buiten mijn bereik valt. Vertel me een "
          + "andere droom, dan ga ik er wel voor zitten.") + "</p></div>";
      doos.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  /* De service worker aanmelden.
   *
   * Alleen op een beveiligde verbinding, want anders bestaat hij niet - en op
   * http://192.168.x.x zou dit een fout in de console geven waar niemand iets
   * aan heeft. Faalt het, dan werkt de app precies zoals hij nu werkt: dit is
   * een extraatje voor het beginscherm, geen voorwaarde.
   */
  if ("serviceWorker" in navigator && window.isSecureContext) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function (e) {
        console.warn("service worker niet aangemeld:", e && e.message);
      });
    });
  }

  /* Een antwoord uitpakken, ook als het geen JSON is.
   *
   * Render stuurt bij een herstart zijn eigen HTML-foutpagina terug, en dan
   * kreeg de dromer letterlijk `Unexpected token '<'` op zijn scherm te zien.
   * Dat is de fout van de browser, niet die van hem, en hij kan er niets mee.
   * Nu staat er wat er aan de hand is: even niet bereikbaar, probeer opnieuw.
   */
  function lees(r) {
    return r.text().then(function (tekst) {
      try {
        return { ok: r.ok, body: JSON.parse(tekst) };
      } catch (e) {
        return {
          ok: false,
          body: {
            error: r.status === 502 || r.status === 503 || r.status === 504
              ? t("De server is even niet bereikbaar — hij start opnieuw op. "
                  + "Probeer het over een minuut nog eens.")
              : t("De server gaf een onverwacht antwoord.") + " (" + r.status + ")"
          }
        };
      }
    });
  }

  /* ------------------------------------------------------------- de gids */

  /* Vera's Dream Guide in de app.
   *
   * De onderwerpen komen van de server en niet uit een lijst hier, want dan
   * staat diezelfde lijst op twee plekken en loopt er een keer een uit de pas.
   * Een nieuw onderwerp is een JSON in knowledge/droomgids/, en verschijnt hier
   * vanzelf.
   *
   * Het verschil dat een bezoeker moet begrijpen: de gids geeft de algemene
   * betekenis, de duiding hierboven geeft die van hem. Dat staat er met zoveel
   * woorden bij, want het is precies waar een abonnement voor is.
   */
  var gidsLijst = [];

  function gidsTonen(woord) {
    var doos = el("gids-woorden"), geen = el("gids-geen");
    // Nog niets opgehaald? Dan niets doen - anders staat er "daar staat nog
    // niets over" bij iemand die alleen van taal wisselde terwijl het verzoek
    // nog liep.
    if (!doos || !gidsLijst.length) { return; }
    woord = (woord || "").trim().toLowerCase();
    var raak = woord
      ? gidsLijst.filter(function (o) { return o.woorden.indexOf(woord) !== -1; })
      : gidsLijst;
    doos.innerHTML = "";
    raak.forEach(function (o, i) {
      if (i) { doos.appendChild(document.createTextNode(" · ")); }
      var a = document.createElement("a");
      a.href = (window.TAAL === "en" ? "" : "/nl") + "/dream-meaning/" + o.slug;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = (window.TAAL === "en" ? o.titel : (o.nl || o.titel));
      doos.appendChild(a);
    });
    if (geen) { geen.hidden = raak.length !== 0; }
  }

  function laadGids() {
    var blok = el("gidsblok");
    if (!blok || !el("gids-woorden")) { return; }
    fetch("/api/gids")
      .then(lees)
      .then(function (res) {
        gidsLijst = (res.body && res.body.onderwerpen) || [];
        if (!gidsLijst.length) { return; }
        gidsTonen("");
        blok.hidden = false;
      })
      .catch(function () { /* geen gids, geen blok */ });
  }

  if (el("gids-veld")) {
    el("gids-veld").addEventListener("input", function () { gidsTonen(this.value); });
    el("gids-veld").addEventListener("keydown", function (e) {
      if (e.key === "Escape") { this.value = ""; gidsTonen(""); }
      // Enter opent de eerste treffer: dat is wat je verwacht van een zoekvak.
      if (e.key === "Enter") {
        var eerste = el("gids-woorden").querySelector("a");
        if (eerste) { window.open(eerste.href, "_blank", "noopener"); }
      }
    });
  }

  /* -------------------------------------------------------- je droom delen */

  /* Een verticale kaart van 1080 bij 1920, gemaakt in de browser.
   *
   * Instagram heeft geen manier om vanaf een website te posten. De enige weg
   * die er echt uitkomt is het deelmenu van het toestel zelf: daar staat
   * Instagram in, en daar kun je een bestand naartoe sturen. Vandaar een
   * afbeelding en geen link — een link naar je paneel is bij een ander dood,
   * want die route controleert of het jouw gebruikersnummer is.
   *
   * **Wat er op de kaart staat is het beeld, niet je droom.** Geen duiding,
   * geen droomtekst, geen titel. Dat is het intieme deel, en iemand die op
   * "delen" drukt om een mooi plaatje te sturen hoort niet per ongeluk zijn
   * nacht op straat te leggen. Wat er wél op staat is "Vannacht droomde ik…"
   * en onderaan het merk — de kaart is de advertentie.
   */
  var KAART_B = 1080, KAART_H = 1920;

  /* Boven en onder blijft 285 pixels leeg. Dat is geen smaak maar de maat van
   * twee dingen die Instagram met deze kaart doet.
   *
   * In een verhaal legt Instagram zijn eigen bediening over je beeld heen:
   * bovenaan het profiel met het kruisje, onderaan het antwoordveld en de
   * knoppen om te delen. Instagram vraagt zelf om 250 pixels rust aan beide
   * kanten. En zet iemand de kaart in zijn feed in plaats van in een verhaal,
   * dan snijdt Instagram hem naar 4:5 - de hoogste verhouding die de feed
   * aanneemt - en dat is precies de middelste 1350 pixels, ofwel 285 eraf aan
   * beide kanten.
   *
   * De strengste van die twee is 285, en daar valt alles binnen. Dat was niet
   * zo: de merknaam stond op 1770 en het adres op 1828, dus in een verhaal lag
   * het antwoordveld eroverheen en in de feed werden ze weggesneden. Precies
   * de twee regels waarvoor de kaart bestaat - de kaart is de advertentie.
   */
  var VEILIG = 285;

  function kaartTekst() {
    return (window.TAAL === "en") ? "Last night I dreamed…" : "Vannacht droomde ik…";
  }

  function beeldLaden(bron) {
    // Een spelende video is zelf al te tekenen: het beeldje dat nu in de speler
    // staat is precies wat de dromer ziet, en bij een kernmoment is dat een
    // sterker beeld dan het stilstaande paneel waar de animatie mee begon.
    if (bron && bron.nodeName === "VIDEO") { return Promise.resolve(bron); }
    return new Promise(function (klaar, mis) {
      var im = new Image();
      im.onload = function () { klaar(im); };
      im.onerror = function () { mis(new Error("beeld niet geladen")); };
      im.src = bron;
    });
  }

  /* Het beeld vullend in een vak, midden uitgesneden. */
  function vullend(ctx, im, x, y, b, h) {
    var bw = im.videoWidth || im.width, bh = im.videoHeight || im.height;
    var s = Math.max(b / bw, h / bh);
    var bb = bw * s, hh = bh * s;
    ctx.drawImage(im, x + (b - bb) / 2, y + (h - hh) / 2, bb, hh);
  }

  async function kaartMaken(bron) {
    var c = document.createElement("canvas");
    c.width = KAART_B; c.height = KAART_H;
    var ctx = c.getContext("2d");

    // De grond van de app, met een violette gloed erachter.
    ctx.fillStyle = "#08060F";
    ctx.fillRect(0, 0, KAART_B, KAART_H);
    var gloed = ctx.createRadialGradient(KAART_B / 2, KAART_H * 0.34, 80,
                                         KAART_B / 2, KAART_H * 0.34, KAART_B);
    gloed.addColorStop(0, "rgba(110, 98, 218, .55)");
    gloed.addColorStop(1, "rgba(8, 6, 17, 0)");
    ctx.fillStyle = gloed;
    ctx.fillRect(0, 0, KAART_B, KAART_H);

    // Het paneel, groot en bijna vierkant, binnen de veilige strook.
    var vakY = 470, vakH = 980;
    var im = await beeldLaden(bron);
    ctx.save();
    ctx.beginPath();
    if (ctx.roundRect) { ctx.roundRect(60, vakY, KAART_B - 120, vakH, 40); }
    else { ctx.rect(60, vakY, KAART_B - 120, vakH); }
    ctx.clip();
    vullend(ctx, im, 60, vakY, KAART_B - 120, vakH);
    ctx.restore();

    // Naar onderen laten wegvloeien, zodat het beeld in de kaart zakt in
    // plaats van er als een plakker op te liggen.
    var vaag = ctx.createLinearGradient(0, vakY + vakH - 200, 0, vakY + vakH);
    vaag.addColorStop(0, "rgba(8, 6, 17, 0)");
    vaag.addColorStop(1, "rgba(8, 6, 17, .96)");
    ctx.fillStyle = vaag;
    ctx.fillRect(60, vakY + vakH - 200, KAART_B - 120, 200);

    ctx.textAlign = "center";
    ctx.fillStyle = "#F2EEFB";
    ctx.font = 'italic 300 96px "Cormorant Garamond", Georgia, serif';
    ctx.fillText(kaartTekst(), KAART_B / 2, 400);

    // Het merk: klein, onderaan, en niet schreeuwen. Wie de kaart mooi vindt
    // zoekt de naam wel op; wie hem opgedrongen krijgt deelt hem niet.
    ctx.font = '600 34px Karla, "Segoe UI", Helvetica, Arial, sans-serif';
    ctx.fillStyle = "rgba(167, 154, 203, .95)";
    ctx.letterSpacing = "6px";
    ctx.fillText("VERA DREAMVERSE", KAART_B / 2, 1548);
    ctx.letterSpacing = "0px";
    ctx.font = '400 30px Karla, "Segoe UI", Helvetica, Arial, sans-serif';
    ctx.fillStyle = "rgba(167, 154, 203, .65)";
    ctx.fillText("vera-dreamverse.com", KAART_B / 2, 1610);

    // JPEG en geen PNG: het beeld is geschilderd, niet een schermafdruk met
    // scherpe lijnen. PNG maakte er 2,5 MB van, wat op een telefoonbundel
    // telt en het deelmenu traag opent. Kwaliteit 92 is met het blote oog
    // niet van het origineel te onderscheiden.
    return new Promise(function (klaar) { c.toBlob(klaar, "image/jpeg", 0.92); });
  }

  /* Welk beeld gaat er op de kaart: wat er nu in de speler staat.
   *
   * Beweegt dit paneel, dan nemen we het beeldje van dit moment uit de video en
   * niet het stilstaande paneel. Dat paneel is het startbeeld waar de animatie
   * mee begon; halverwege staat er meestal meer te gebeuren. Een video van tien
   * seconden delen is te lang voor een verhaal - een still eruit is beter.
   */
  function huidigPaneelBeeld() {
    var v = stage.querySelector("video");
    // readyState 2 betekent: er is een beeldje om te tekenen. Zonder die
    // controle krijg je een zwart vlak op de kaart.
    if (v && v.readyState >= 2 && v.videoWidth) { return v; }
    return panelImages[index] || null;
  }

  function deelKnopBijwerken() {
    var knop = el("deel");
    if (!knop) { return; }
    var kan = !!huidigPaneelBeeld() && !(episode && episode.demo);
    knop.hidden = !kan;
  }

  if (el("deel")) {
    el("deel").addEventListener("click", async function () {
      var knop = this, melding = el("deel-melding");
      var bron = huidigPaneelBeeld();
      melding.className = "deel-melding";
      melding.textContent = "";
      if (!bron) { return; }

      knop.disabled = true;
      var oudeTekst = knop.textContent;
      knop.textContent = t("Bezig…");
      try {
        // De letters moeten binnen zijn, anders tekent het doek in Times New
        // Roman en ziet de kaart er niet uit als de app.
        if (document.fonts && document.fonts.ready) { await document.fonts.ready; }
        var blob = await kaartMaken(bron);
        var bestand = new File([blob], "dreamverse.jpg", { type: "image/jpeg" });

        if (navigator.canShare && navigator.canShare({ files: [bestand] })) {
          await navigator.share({ files: [bestand] });
          melding.textContent = "";
        } else {
          // Geen deelmenu — op een laptop is dat de regel. Dan opslaan, en
          // zeggen wat je er vervolgens mee doet.
          var url = URL.createObjectURL(blob);
          var a = document.createElement("a");
          a.href = url; a.download = "dreamverse.jpg";
          document.body.appendChild(a); a.click(); a.remove();
          setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
          melding.textContent = t("Opgeslagen als afbeelding. Delen naar Instagram gaat het makkelijkst vanaf je telefoon.");
        }
      } catch (e) {
        // Wegklikken van het deelmenu is geen fout.
        if (!(e && e.name === "AbortError")) {
          melding.className = "deel-melding err";
          melding.textContent = t("De kaart kon niet gemaakt worden.");
        }
      }
      knop.disabled = false;
      knop.textContent = oudeTekst;
    });
  }

  /* ------------------------------------------------------ wat kan er beter */

  /* Het enige kanaal waarlangs we horen wat er mis is.
   *
   * De app meet met opzet geen klikgedrag: dat zou een cookiebanner opleveren
   * en het gedrag van dromers bij een advertentiebedrijf leggen. Het rapport
   * ziet dus wel dat iemand niet terugkomt, maar nooit waarom. Dit veld is het
   * antwoord op die blinde vlek.
   *
   * Pas na de eerste verbeelding, niet bij binnenkomst: wie net binnen is heeft
   * geen mening, wie zijn droom in vijf panelen heeft zien staan wel. En het
   * gaat weg zodra hij iets heeft ingestuurd - nog eens vragen leest als "we
   * hebben het niet gelezen".
   */
  var TERUG_WEG = "dreamverse_feedback_weg";

  function terugAfgewezen() {
    try { return localStorage.getItem(TERUG_WEG) === "ja"; } catch (e) { return false; }
  }

  function toonTerugkoppeling() {
    var doos = el("terugkoppeling");
    if (!doos) { return; }
    var al = profiel && profiel.feedback_gegeven;
    doos.hidden = !!(al || terugAfgewezen());
  }

  if (el("feedback-weg")) {
    el("feedback-weg").addEventListener("click", function () {
      try { localStorage.setItem(TERUG_WEG, "ja"); } catch (e) { /* mag geweigerd zijn */ }
      el("terugkoppeling").hidden = true;
    });
  }

  if (el("feedback-op")) {
    el("feedback-op").addEventListener("click", function () {
      var veld = el("feedback-tekst");
      var tekst = (veld.value || "").trim();
      var melding = el("feedback-melding");
      if (!tekst) { veld.focus(); return; }

      var knop = this;
      knop.disabled = true;
      melding.textContent = "";

      fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tekst: tekst })
      })
        .then(lees)
        .then(function (res) {
          if (!res.ok) { throw new Error(res.body.error || t("Dat lukte niet.")); }
          if (profiel) { profiel.feedback_gegeven = true; }
          veld.value = "";
          el("terugkoppeling").hidden = true;
          statusEl.className = "status";
          statusEl.textContent = t("Dank je. Ik lees alles wat hier binnenkomt.");
        })
        .catch(function (err) {
          melding.textContent = err.message;
          knop.disabled = false;
        });
    });
  }

  /* ------------------------------------------------- vragen over je droom */

  /* Eén vraag per droom is inbegrepen, daarna kost hij een token.
   *
   * Dit is een proef: we willen weten of mensen hier iets mee doen voordat er
   * meer aan gebouwd wordt. Daarom wordt elk gebruik apart geteld in de meter.
   *
   * De grenzen zijn dezelfde als bij de duiding - geen gezondheid, geen geld,
   * geen voorspelling - en die staan in de prompt, niet hier. Wat hier staat is
   * alleen hoe het eruitziet.
   */
  function toonVragen(ep) {
    var blok = el("vraagblok");
    if (!blok) { return; }
    // Alleen bij een droom die echt bestaat; niet bij het voorbeeld.
    if (!ep || !ep.number || ep.demo) { blok.hidden = true; return; }
    blok.hidden = false;

    var lijst = el("vragen");
    var eerder = (ep.vragen || []);
    lijst.innerHTML = "";
    eerder.forEach(function (v) {
      var d = document.createElement("div");
      d.className = "vraag-paar";
      var vr = document.createElement("p");
      vr.className = "vraag-vraag";
      vr.textContent = v.vraag;
      var aw = document.createElement("p");
      aw.textContent = v.antwoord;
      d.appendChild(vr);
      d.appendChild(aw);
      lijst.appendChild(d);
    });

    var uitleg = el("vraag-uitleg");
    if (uitleg) {
      uitleg.textContent = eerder.length
        ? t("De volgende vraag kost 1 token.")
        : t("Je eerste vraag bij deze droom is inbegrepen.");
    }
  }

  if (el("vraag-op")) {
    el("vraag-op").addEventListener("click", function () {
      var veld = el("vraag");
      var tekst = (veld.value || "").trim();
      var melding = el("vraag-melding");
      melding.className = "vraag-melding";
      if (!tekst) { veld.focus(); return; }
      if (!episode || !episode.number) { return; }

      this.disabled = true;
      var knop = this;
      knop.textContent = t("Bezig…");
      melding.textContent = "";

      fetch("/api/vraag", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dream: episode.number, vraag: tekst })
      })
        .then(lees)
        .then(function (res) {
          if (!res.ok) {
            var op = new Error(res.body.error || t("Dat lukte niet."));
            op.tekort = res.body.need_tokens || 0;
            throw op;
          }
          episode.vragen = res.body.vragen;
          veld.value = "";
          toonVragen(episode);
          if (res.body.account) { toonAccount(res.body.account); }
          // Ging het over geweld of zelfdoding, dan hoort de verwijzing er ook
          // hier bij - dezelfde als bij de duiding.
          var laatste = res.body.vraag || {};
          if ((laatste.zorg || []).length) {
            toonZorg({ zorg: laatste.zorg });
          }
        })
        .catch(function (err) {
          melding.className = "vraag-melding err";
          melding.textContent = err.message;
          if (err.tekort) {
            var koop = document.createElement("button");
            koop.type = "button";
            koop.className = "call-koop";
            koop.textContent = t("Tokens kopen");
            koop.addEventListener("click", naarTokens);
            melding.appendChild(document.createElement("br"));
            melding.appendChild(koop);
          }
        })
        .then(function () {
          knop.disabled = false;
          knop.textContent = t("Vraag het");
        });
    });
  }

  /* --------------------------------------------------------------- knoppen */

  el("next").addEventListener("click", function () {
    show(index === episode.panels.length - 1 ? 0 : index + 1);
  });
  el("prev").addEventListener("click", function () { show(index - 1); });

  el("voice").addEventListener("click", function () {
    voiceOn = !voiceOn;
    this.setAttribute("aria-pressed", voiceOn ? "true" : "false");
    this.textContent = voiceOn ? t("Stem uit") : t("Stem aan");
    if (voiceOn && episode) {
      // Zonder panelen is er niets om doorheen te klikken, dus loopt het verhaal
      // in één keer door. Anders leest hij alleen het stuk dat in beeld staat.
      if (player.classList.contains("alleen-tekst")) { leesAlles(0); }
      else { speak(episode.panels[index].narration); }
    }
    else if ("speechSynthesis" in window) { window.speechSynthesis.cancel(); }
  });

  // Het hele verhaal achter elkaar, voor de tekstversie. De opgenomen stem
  // heeft de voorkeur; is die er niet, dan leest de browser voor.
  function leesAlles(vanaf) {
    if (!voiceOn || !episode || vanaf >= episode.panels.length) { return; }
    var verder = function () { leesAlles(vanaf + 1); };
    if (stemmen[vanaf]) {
      try {
        speler.pause();
        speler.onended = verder;
        speler.src = stemmen[vanaf];
        speler.play().catch(verder);
        return;
      } catch (e) { /* val terug op de browserstem */ }
    }
    if (!("speechSynthesis" in window)) { return; }
    var zin = new SpeechSynthesisUtterance(episode.panels[vanaf].narration);
    if (verteller) { zin.voice = verteller; }
    zin.lang = window.TAAL === "en" ? "en-US" : "nl-NL";
    zin.rate = 0.95;
    zin.onend = verder;
    window.speechSynthesis.speak(zin);
  }

  document.addEventListener("keydown", function (e) {
    if (e.target === input || !episode) { return; }
    if (e.key === "ArrowRight") { el("next").click(); }
    if (e.key === "ArrowLeft" && index > 0) { show(index - 1); }
  });

  // Losse aankopen: meer beeld bij een droom, tegen tokens.
  function koopKlik(e, nummerBron, meldingId) {
    var knop = e.target.closest ? e.target.closest(".koop") : null;
    if (!knop) { return; }
    var nummer = Number(nummerBron());
    if (!nummer) { return; }
    var melding = el(meldingId);
    melding.className = "extras-melding";
    melding.textContent = t("Bezig met aanvragen…");
    knop.disabled = true;
    fetch("/api/extra", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dream: nummer, kind: knop.dataset.kind })
    })
      .then(lees)
      .then(function (res) {
        if (!res.ok) {
          var op = new Error(res.body.error || t("Dat lukte niet."));
          op.kanPanelen = !!res.body.kan_panelen;
          throw op;
        }
        melding.textContent = t("Onderweg. De zandloper onderin loopt mee.");
        verwachtWerk();
        startBezig(t("Aanvraag gestart…"));
        toonAccount(res.body.account);
        pollPanels(nummer, POLL_TOTAAL);
      })
      .catch(function (err) {
        melding.className = "extras-melding err";
        melding.textContent = err.message;
        // Kan het wel zodra de panelen er zijn? Dan hoort daar een knop bij en
        // geen zin die vertelt wat het kost zonder een manier om het te doen.
        if (err.kanPanelen) {
          var doe = document.createElement("button");
          doe.type = "button";
          doe.className = "koop";
          doe.dataset.kind = "panelen";
          doe.innerHTML = t("Maak de panelen") + " <b>1</b>";
          melding.appendChild(document.createElement("br"));
          melding.appendChild(doe);
        }
      })
      .then(function () { knop.disabled = false; });
  }

  // Kies je een andere droom, dan veranderen de knoppen mee: bij een droom
  // zonder panelen kun je alleen panelen kopen, en andersom.
  if (el("kies")) {
    el("kies").addEventListener("change", function () { zetKoopKnoppen(keuzeDromen); });
  }

  el("extras").addEventListener("click", function (e) {
    koopKlik(e, function () { return el("extras").dataset.dream; }, "extras-melding");
  });
  document.querySelector(".kies-droom").addEventListener("click", function (e) {
    koopKlik(e, function () { return el("kies").value; }, "kies-melding");
  });

  el("antwoord-op").addEventListener("click", function () {
    var blok = el("antwoord-blok");
    var tekst = el("antwoord").value.trim();
    if (!tekst) { el("antwoord").focus(); return; }
    fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dream: Number(blok.dataset.dream), answer: tekst })
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.error) { el("antwoord-uitleg").textContent = d.error; return; }
      blok.classList.add("bewaard");
      el("antwoord-uitleg").textContent = t("Bewaard. Vera weet dit bij je volgende droom.");
      loadArchive();
    }).catch(function () {
      el("antwoord-uitleg").textContent = t("Bewaren lukte niet. Probeer het nog eens.");
    });
  });

  el("clear").addEventListener("click", function () {
    if (!window.confirm(t("Het hele archief wissen? De panelen, de animaties en de ingesproken tekst gaan mee. Je volgende droom wordt Droom 1."))) { return; }
    fetch("/api/archive", { method: "DELETE" })
      .then(function () {
        loadArchive();
        statusEl.className = "status";
        statusEl.textContent = t("Archief gewist.");
      });
  });

  el("go").addEventListener("click", function () {
    var text = input.value.trim();
    if (!text) {
      statusEl.className = "status";
      statusEl.textContent = t("Vertel eerst je droom.");
      input.focus();
      return;
    }
    if (listening && recogniser) { recogniser.stop(); }

    var go = this;
    go.disabled = true;
    go.textContent = t("Bezig…");
    statusEl.className = "status";
    statusEl.textContent = gekozenKwaliteit === "duiding"
      ? t("Je droom wordt geduid. Dit duurt ongeveer een halve minuut.")
      : t("Je droom wordt verbeeld. Dit duurt een halve tot anderhalve minuut.");
    guideLine.textContent = t("Ik kijk ernaar. Blijf even bij me.");
    verwachtWerk();
    startBezig(t("De duiding wordt geschreven"));

    fetch("/api/episode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dream: text, quality: gekozenKwaliteit, lens: gekozenBril })
    })
      .then(lees)
      .then(function (res) {
        if (!res.ok) { throw new Error(res.body.error || t("Het lukte niet.")); }
        if (res.body.buiten_bereik) {
          // Geen verbeelding, wel een antwoord. De invoer blijft staan: de
          // dromer heeft niets verkeerd gedaan en mag hem aanpassen.
          stopBezig();
          buitenBereik();
          return;
        }
        var ep = res.body.episode;
        render(ep);
        input.value = "";
        loadArchive();
        laadAccount();
        statusEl.textContent = ep.demo
          ? (ep.demo_reason || t("Dit is een voorbeeld."))
          : "Klaar. Dit was Droom " + ep.number + "; hij telt mee in je volgende duiding.";
        guideLine.textContent = t("Kijk maar. Ik heb er iets van gemaakt.");
        player.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function (e) {
        statusEl.className = "status err";
        statusEl.textContent = e.message;
        guideLine.textContent = t("Er ging iets mis. Probeer het zo nog eens.");
        stopBezig();
      })
      .then(function () {
        go.disabled = false;
        go.textContent = knopTekst();
        // Komt er geen tekenwerk, dan hoort de teller ook te stoppen.
        if (!werkGezien && !(episode && episode.images_pending)) { stopBezig(); }
      });
  });


  /* ------------------------------------------------------- gesprek met Vera */

  var room = null, micTrack = null, sessionId = null, callTimer = null, callEnds = 0;

  function callStatus(text) {
    el("call-status").textContent = text;
  }

  function veil(show) {
    el("call-veil").hidden = !show;
  }

  function tick() {
    var left = Math.max(0, Math.round((callEnds - Date.now()) / 1000));
    var m = Math.floor(left / 60), sec = left % 60;
    var klok = el("call-time");
    klok.textContent = m + ":" + (sec < 10 ? "0" : "") + sec;
    // Onder de minuut oranje, onder tien seconden rood: je wilt niet dat het
    // gesprek er zonder waarschuwing uit klapt.
    klok.className = "call-time" + (left <= 10 ? " kritiek" : left <= 60 ? " bijna" : "");
    if (left <= 0) { hangup(t("De vijf minuten zaten erop.")); }
  }

  function hangup(reason) {
    // Eerst de woorden veiligstellen: hierna gaat het paneel dicht.
    meeschrijvenStoppen();
    if (callTimer) { clearInterval(callTimer); callTimer = null; }
    if (room) { try { room.disconnect(); } catch (e) { /* al weg */ } room = null; }
    if (micTrack) { try { micTrack.stop(); } catch (e) { /* al gestopt */ } micTrack = null; }
    if (sessionId) {
      // Afsluiten bij Runway, anders loopt de teller door.
      fetch("/api/vera/session/" + sessionId, { method: "DELETE" })
        .then(function () { laadAccount(); }).catch(function () {});
      sessionId = null;
    }
    el("call-panel").hidden = true;
    el("call").disabled = false;
    el("call").textContent = t("Praat met Vera");
    guide.classList.remove("listening");
    if (reason) { guideLine.textContent = reason; }
    // Wat je verteld hebt, in de invoer. Dit overschrijft de regel hierboven
    // alleen als er echt iets te oogsten valt.
    gesprekOogsten();
  }

  /* Afbreken met een melding die blíjft staan, náást de knop.
   *
   * Twee dingen gingen hier eerder mis. De melding landde onderaan bij de
   * invoerbalk, terwijl je bovenaan op de knop klikte - dus je zag niets en dan
   * lijkt het stuk. En Vera zei "ik kon je niet horen", ook als het probleem
   * geld was en niet geluid. Dat is niet alleen verwarrend maar onwaar.
   *
   * `tekort` is het aantal tokens dat ontbreekt, als dát de reden was.
   */
  function staken(bericht, tekort) {
    console.warn("vera:", bericht);
    hangup();

    var doos = el("call-melding");
    if (doos) {
      doos.hidden = false;
      doos.className = "call-melding err";
      doos.textContent = bericht;
      // De vertaalslag zet de brontekst in data-nl en herstelt daaruit bij een
      // taalwissel. Zonder deze regel staat daar de lege begintekst, en dan
      // veegt een klik op EN/NL de melding weg.
      doos.dataset.nl = bericht;
      if (tekort) {
        var knop = document.createElement("button");
        knop.type = "button";
        knop.className = "call-koop";
        knop.textContent = t("Tokens kopen");
        knop.addEventListener("click", function () {
          naarTokens();
        });
        doos.appendChild(document.createElement("br"));
        doos.appendChild(knop);
      }
    }

    // Vera zegt alleen iets over horen als het echt over horen ging.
    guideLine.textContent = tekort
      ? t("Daar hebben we tokens voor nodig.")
      : t("Ik kon je niet horen.");
  }

  async function callVera() {
    var btn = el("call");
    if (el("call-melding")) { el("call-melding").hidden = true; }
    btn.disabled = true;
    btn.textContent = t("Verbinden…");
    el("call-panel").hidden = false;
    veil(true);
    callStatus("Vera wordt wakker…");

    // De verbinding moet beveiligd zijn, anders geeft de browser de microfoon
    // niet vrij. localhost is de enige uitzondering.
    if (!window.isSecureContext || !navigator.mediaDevices) {
      return staken("Je browser geeft de microfoon alleen vrij op een beveiligde " +
                    "verbinding (https). Op dit adres kan dat niet.");
    }
    if (typeof LivekitClient === "undefined") {
      return staken("Het onderdeel dat de verbinding maakt is niet geladen. Ververs de pagina.");
    }

    var stream;
    try {
      // Microfoon eerst, binnen de klik: browsers trekken de toestemming
      // anders in zodra er een await tussen zit.
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      var uitleg = {
        NotAllowedError: "Je hebt de microfoon geweigerd, of de browser blokkeert hem. " +
                         "Klik op het slotje in de adresbalk en zet de microfoon op toestaan.",
        NotFoundError: "Er is geen microfoon gevonden op dit apparaat.",
        NotReadableError: "De microfoon is in gebruik door een ander programma.",
        SecurityError: "De browser staat de microfoon hier niet toe."
      }[e && e.name] || ("De microfoon kon niet worden geopend: " + (e && e.name ? e.name : "onbekende fout"));
      return staken(uitleg);
    }

    var creds;
    try {
      var r = await fetch("/api/vera/session", { method: "POST" });
      creds = await r.json();
      if (!r.ok) {
        var op = new Error(creds.error || t("Verbinden mislukte."));
        op.tekort = creds.need_tokens || 0;
        throw op;
      }
    } catch (e) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      return staken(e.message, e.tekort);
    }

    sessionId = creds.session_id;
    callStatus("Ze komt in beeld…");
    if (!creds.server_url || !creds.token) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      return staken("Runway gaf geen bruikbare verbindingsgegevens terug.");
    }

    room = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });

    room.on(LivekitClient.RoomEvent.TrackSubscribed, function (track) {
      if (track.kind === "video") { track.attach(el("vera-video")); veil(false); }
      if (track.kind === "audio") { track.attach(el("vera-audio")); }
    });
    room.on(LivekitClient.RoomEvent.Disconnected, function () { hangup(); });

    try {
      await room.connect(creds.server_url, creds.token);
      var pub = new LivekitClient.LocalAudioTrack(stream.getAudioTracks()[0], undefined, false);
      await room.localParticipant.publishTrack(pub, { source: LivekitClient.Track.Source.Microphone });
      micTrack = pub;
    } catch (e) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      console.error("vera: verbinden mislukte", e);
      return staken("De verbinding met Vera kwam niet tot stand: " +
                    ((e && e.message) || "onbekende fout") +
                    ". Deze sessie is nu op; druk opnieuw op de knop voor een nieuwe.");
    }

    // Komt haar beeld niet binnen een halve minuut, dan komt het niet meer.
    // Eeuwig op "ze komt in beeld" blijven staan is geen wachten maar liegen.
    setTimeout(function () {
      var v = el("vera-video");
      if (room && (!v.srcObject || v.videoWidth === 0)) {
        staken("Er is verbinding, maar Vera verschijnt niet. Haar kant publiceert geen " +
               "beeld of geluid. Dit ligt niet aan je microfoon of je browser; probeer het " +
               "zo nog eens.");
      }
    }, 30000);

    btn.textContent = t("In gesprek");
    guide.classList.add("listening");
    // Vanaf hier praat je echt, dus vanaf hier schrijven we mee.
    meeschrijvenStarten();
    callEnds = Date.now() + (creds.max_duration || 600) * 1000;
    tick();
    callTimer = setInterval(tick, 1000);
  }

  el("call").addEventListener("click", callVera);
  el("hangup").addEventListener("click", function () { hangup("Tot morgenochtend."); });
  // Een dichtgeklapt tabblad mag geen sessie laten doorlopen.
  window.addEventListener("pagehide", function () { if (sessionId) { hangup(); } });

  /* ----------------------------------------------------------------- naam */

  var naamVeld = el("naam");
  var naamOpslaan = null;

  // De begroeting met de naam erin. Apart, omdat hij ook opnieuw moet als de
  // taal wisselt terwijl hij al op het scherm staat.
  var begroetteNaam = "";

  function begroet(naam) {
    begroetteNaam = naam || "";
    if (!begroetteNaam) { return; }
    guideLine.textContent = window.TAAL === "en"
      ? "Good morning " + begroetteNaam + ". Did you sleep well?"
      : "Goedemorgen " + begroetteNaam + ". Heb je lekker geslapen?";
  }

  function bewaarNaam() {
    var naam = naamVeld.value.trim();
    fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: naam })
    }).then(function () {
      if (naam) {
        guideLine.textContent = window.TAAL === "en"
          ? "Hello " + naam + ". Tell me what you saw."
          : "Dag " + naam + ". Vertel me wat je zag.";
        toonNaam(naam);
      }
    }).catch(function () { /* naam is een extraatje, geen voorwaarde */ });
  }

  // Wie zijn naam al bij de introductie gaf, hoort hem hier terug in plaats van
  // dezelfde vraag nog een keer te krijgen.
  function toonNaam(naam) {
    if (!naam) {
      el("who-bekend").hidden = true;
      el("who-vraag").hidden = false;
      return;
    }
    el("who-naam").textContent = naam;
    el("who-voor").textContent = window.TAAL === "en"
      ? "Vera calls you " : "Vera spreekt je aan als ";
    el("who-bekend").hidden = false;
    el("who-vraag").hidden = true;
  }

  el("who-anders").addEventListener("click", function () {
    el("who-bekend").hidden = true;
    el("who-vraag").hidden = false;
    naamVeld.focus();
    naamVeld.select();
  });

  naamVeld.addEventListener("input", function () {
    // Niet bij elke toetsaanslag naar de server; even wachten tot het stil is.
    if (naamOpslaan) { clearTimeout(naamOpslaan); }
    naamOpslaan = setTimeout(bewaarNaam, 800);
  });
  naamVeld.addEventListener("blur", bewaarNaam);

  fetch("/api/profile")
    .then(function (r) { return r.json(); })
    .then(function (p) {
      if (p.name) {
        naamVeld.value = p.name;
        begroet(p.name);
      }
    })
    .catch(function () {});

  /* -------------------------------------------------------------- de bril */

  /* Door welke bril wil je je droom gelezen hebben?
   *
   * Dit is iets anders dan het chakraveld. Een chakraveld is een gevoel dat het
   * model per paneel kiest en dat je achteraf ziet; een bril is een manier van
   * kijken die je vooraf kiest. Dezelfde droom over een huis met een dichte deur
   * geeft bij psychologisch iets over wat je van jezelf afhoudt, bij symbolisch
   * over wat een deur in jouw eigen dromen steeds betekent, en bij spiritueel
   * over waar je in je leven voor staat.
   *
   * "Vanzelf" staat voorop en is de standaard: dan kiest het model de bril die
   * bij deze droom past en zegt achteraf welke het werd. Wie er niet over wil
   * nadenken krijgt de classificatie dus toch.
   */
  var BRILLEN = [
    { key: "vanzelf", naam: "Vanzelf",
      uitleg: "Ik kies de bril die bij deze droom past, en zeg achteraf welke het werd." },
    { key: "psychologisch", naam: "Psychologisch",
      uitleg: "Wat de droom over jou zegt: wat je wegdrukt, waar spanning zit, welk gedrag terugkomt." },
    { key: "symbolisch", naam: "Symbolisch",
      uitleg: "Wat de tekens betekenen — en dan wat ze bij jou betekenen, niet wat een droomboek zegt." },
    { key: "spiritueel", naam: "Spiritueel",
      uitleg: "Waar je voor staat: wat je loslaat, wat op je afkomt, groter dan de dag zelf." }
  ];

  var gekozenBril = "vanzelf";

  function toonBrillen() {
    var doos = el("bril-knoppen");
    if (!doos) { return; }
    doos.innerHTML = "";
    BRILLEN.forEach(function (b) {
      var knop = document.createElement("button");
      knop.type = "button";
      knop.className = "bril";
      knop.dataset.bril = b.key;
      knop.setAttribute("aria-pressed", b.key === gekozenBril ? "true" : "false");
      knop.title = t(b.uitleg);
      knop.textContent = t(b.naam);
      knop.addEventListener("click", function () { kiesBril(b); });
      doos.appendChild(knop);
    });
  }

  function kiesBril(b) {
    gekozenBril = b.key;
    document.querySelectorAll(".bril").forEach(function (k) {
      k.setAttribute("aria-pressed", k.dataset.bril === b.key ? "true" : "false");
    });
    var melding = el("kwaliteit-melding");
    if (melding) {
      melding.className = "kwaliteit-melding";
      melding.textContent = t(b.uitleg);
    }
  }

  toonBrillen();

  /* De bril die het geworden is, bij de duiding.
   *
   * Vooral bij "vanzelf" is dit het antwoord op zijn vraag: dan heeft hij niet
   * gekozen en wil hij weten hoe de droom geclassificeerd is.
   */
  function toonBril(ep) {
    var doos = el("bril-uitslag");
    if (!doos) { return; }
    var bril = ep && ep.lens;
    if (!bril) { doos.hidden = true; return; }
    var vanzelf = (ep.lens_gekozen || "vanzelf") === "vanzelf";
    doos.hidden = false;
    doos.innerHTML = '<span class="bril-merk bril-' + bril + '">' + t(hoofdletter(bril)) + "</span>" +
      "<span>" + (vanzelf ? t("zo is deze droom gelezen") : t("zoals je vroeg")) + "</span>";
  }

  function hoofdletter(woord) {
    return woord.charAt(0).toUpperCase() + woord.slice(1);
  }

  /* ------------------------------------------------------ pakket en saldo */

  var gekozenKwaliteit = "standaard";

  function toonKwaliteiten(a) {
    var doos = el("kwaliteit-knoppen");
    if (!doos || !a.kwaliteiten) { return; }
    doos.innerHTML = "";
    // Kost er niets meer iets? Dan is de prijs geen onderscheid meer.
    var allesGratis = a.kwaliteiten.every(function (k) { return k.inbegrepen; });
    a.kwaliteiten.forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "kwaliteit" + (k.tokens && !k.betaalbaar ? " tekort" : "");
      b.dataset.kwaliteit = k.key;
      b.setAttribute("aria-pressed", k.key === gekozenKwaliteit ? "true" : "false");
      zetKnopTekst();
      b.title = k.uitleg;
      /* Wat je krijgt, en wat het kost als het iets kost.
       *
       * De nul is er om te contrasteren: naast een knop van "10 tokens" leest
       * een knop zonder prijs als een prijs die je niet ziet, en dan durf je
       * niet te klikken. Maar kost geen enkele optie iets - bij Ultra is alles
       * inbegrepen - dan staat er vier keer "0 tokens" en zegt die nul niets
       * meer. Dan alleen wat je krijgt.
       */
      var kost = k.inbegrepen
        ? t("0 tokens")
        : k.tokens + " " + t(k.tokens === 1 ? "token" : "tokens");
      var regel = k.inbegrepen ? (allesGratis ? k.bevat : k.bevat + " · " + kost) : kost;
      if (k.kern_op) {
        // Hoort bij je pakket, maar je maandtegoed is op. Dat is iets anders dan
        // "zit er niet in", en het staat er dus ook anders.
        regel = kost + " · " + t("maandtegoed op");
      }
      b.innerHTML = k.naam + "<small>" + regel + "</small>";
      if (k.beste) {
        b.classList.add("beste");
        b.insertAdjacentHTML("afterbegin", '<span class="vlagje">' + t("in je pakket") + '</span>');
      }
      b.addEventListener("click", function () { kiesKwaliteit(k); });
      doos.appendChild(b);
    });
  }

  /* Wat er op de knop staat, hangt af van wat je gekozen hebt.
   *
   * "Verbeeld mijn droom" was maar de helft van het verhaal - er wordt ook
   * geduid, en dat is de helft waar mensen voor terugkomen. Erger nog: bij
   * "Alleen de duiding" wordt er niets verbeeld, en dan stond er iets wat
   * gewoon niet waar was.
   */
  function knopTekst() {
    return gekozenKwaliteit === "duiding"
      ? t("Duid mijn droom")
      : t("Verbeeld en duid mijn droom");
  }

  function zetKnopTekst() {
    var go = el("go");
    if (go && !go.disabled) { go.textContent = knopTekst(); }
  }

  function kiesKwaliteit(k) {
    var melding = el("kwaliteit-melding");
    melding.className = "kwaliteit-melding";
    if (!k.betaalbaar) {
      // Wel aanklikbaar, maar met een eerlijk antwoord in plaats van stilte.
      melding.className = "kwaliteit-melding err";
      melding.textContent = k.naam + " kost " + k.tokens + " tokens en je hebt er niet genoeg. " +
                            "Koop tokens bij, of kies een lichtere optie.";
      return;
    }
    gekozenKwaliteit = k.key;
    document.querySelectorAll(".kwaliteit").forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.kwaliteit === k.key ? "true" : "false");
    });
    melding.textContent = k.uitleg + (k.tokens ? "  Kost je " + k.tokens + " tokens." : "");
    zetKnopTekst();
  }

  /* Je tegoed, boven de knoppen waar je het uitgeeft.
   *
   * Het stond alleen verderop op de pagina, bij de pakketten. Maar je kiest hier
   * wat je van je droom wilt, en dan hoor je hier te zien wat je hebt - anders
   * klik je op Supreme en hoor je pas daarna dat je tien tokens tekortkomt.
   */
  function toonTegoed(a) {
    var doos = el("tegoed");
    if (!doos) { return; }
    var stukken = [];
    stukken.push('<b>' + a.plan_naam + "</b>");
    stukken.push(a.dromen_over + " " + t(a.dromen_over === 1 ? "droom over" : "dromen over"));
    // Alleen tonen als je pakket er heeft: bij Gratis en Lite zou "0 kernmomenten"
    // klinken als iets wat je kwijt bent in plaats van iets wat er nooit was.
    if (a.kern_inbegrepen) {
      stukken.push("<b>" + a.kern_over + "</b> " +
                   t(a.kern_over === 1 ? "kernmoment" : "kernmomenten"));
    }
    stukken.push('<b>' + a.tokens + "</b> " + t("tokens"));
    doos.innerHTML = stukken.join('<i aria-hidden="true">·</i>');
    if (betalenAan) {
      var knop = document.createElement("button");
      knop.type = "button";
      knop.className = "opwaardeer";
      knop.dataset.nl = "opwaarderen";
      knop.textContent = t("opwaarderen");
      knop.addEventListener("click", naarTokens);
      doos.appendChild(knop);
    }
    doos.hidden = false;
    doos.classList.toggle("op", a.dromen_over === 0 && a.tokens < a.tokens_per_extra_droom);
  }

  /* Wat een kernmoment kost, op de knop zelf.
   *
   * Zit het nog in je maandtegoed, dan hoort daar geen tokenprijs te staan -
   * anders lijkt iets geld te kosten wat je al betaald hebt, en dan gebruikt
   * niemand zijn tegoed. Welke aankopen inbegrepen zijn zegt de server
   * (`extra_inbegrepen`), zodat die regel op één plek staat.
   */
  function toonKernPrijzen(a) {
    var inbegrepen = a.extra_inbegrepen || {};
    document.querySelectorAll(".koop[data-kind]").forEach(function (knop) {
      var soort = knop.dataset.kind;
      if (!(soort in inbegrepen)) { return; }
      // Niets aan de innerHTML van de knop veranderen. taal.js onthoudt die als
      // sleutel, dus zodra hier de prijs wordt overschreven - of er zelfs maar
      // een data-attribuut in de <b> bijkomt - matcht de sleutel niet meer en
      // blijft de hele knop Nederlands. Vandaar een attribuut op de knop zelf
      // en een ::after in de CSS: de opmaak verandert, de tekst niet.
      knop.dataset.inbegrepen = t("in je pakket");
      knop.classList.toggle("inbegrepen", !!inbegrepen[soort]);
    });
  }

  function toonAccount(a) {
    toonKernPrijzen(a);
    // Welk pakket het is bepaalt of "Vera zag iets" verschijnt. Die kaart is
    // het betaalmoment, dus wie al betaalt hoeft hem niet te zien.
    rekeningPlan = a.plan || rekeningPlan;
    toonVeraZag(laatsteSamen);
    toonTegoed(a);
    toonKwaliteiten(a);
    var op = a.dromen_over === 0 ? " op" : "";
    var minuten = Math.floor(a.avatar_seconden_over / 60);
    var html = "";
    // Wie ben ik hier eigenlijk? Zonder dit zie je je pakket en je saldo, maar
    // niet met welk account je binnen bent - en op een gedeelde computer weet je
    // dan niet wiens dromen je zit te lezen.
    if (profiel && profiel.email) {
      html += "<div class='wie-ben-ik'><b>" + profiel.email + "</b><span>" +
              t("ingelogd als") + "</span></div>";
    }
    html += "<div class='" + op + "'><b>" + a.dromen_over + "</b><span>" + t("dromen over") + "</span></div>";
    html += "<div><b>" + a.tokens + "</b><span>" + t("tokens") + "</span></div>";
    html += "<div><b>" + (minuten + Math.floor(a.tokens / a.tokens_per_minuut)) +
            "</b><span>" + t("minuten vera") + "</span></div>";
    html += "<div><b>" + a.plan_naam + "</b><span>" + t("pakket") + "</span></div>";
    html += "<div class='schakel'>";
    if (betalenAan) {
      html += "<button type='button' data-opwaarderen='1'>" +
              t("Tokens kopen") + "</button>";
    }
    // Hier stonden de pakketknoppen en +10 tokens van het beheer. Die zaten in
    // de kaart van elke dromer, verborgen achter een vlag in JavaScript, en dat
    // is geen slot maar een gordijn. Ze staan nu op /beheer.
    if (a.plan !== "gratis") {
      html += "<button type='button' class='ghost' data-portaal='1'>" +
              t("abonnement") + "</button>";
    }
    html += "<button type='button' class='ghost uitloggen' data-uit='1'>" +
            t("uitloggen") + "</button>";
    html += "</div>";
    el("account").innerHTML = html;

    el("account").querySelectorAll("[data-opwaarderen]").forEach(function (b) {
      b.addEventListener("click", naarTokens);
    });
    el("account").querySelectorAll("[data-uit]").forEach(function (b) {
      b.addEventListener("click", uitloggen);
    });
    el("account").querySelectorAll("[data-portaal]").forEach(function (b) {
      b.addEventListener("click", naarPortaal);
    });
  }

  // Staat afrekenen aan? Komt uit /api/health. Zonder dit weten de kaarten niet
  // of er een opwaardeerknop bij mag.
  var betalenAan = false;

  // Wanneer elke droom was, op nummer. Gevuld bij het laden van het archief.
  var wanneerPerDroom = {};

  // Hoeveel dromen er in het archief staan. De lege stand van "Je dromen samen"
  // vertelt daarmee hoe ver je bent in plaats van alleen dat er niets is.
  var aantalDromen = 0;

  function laadAccount() {
    fetch("/api/account").then(function (r) { return r.json(); })
      .then(toonAccount).catch(function () {});
  }

  /* ------------------------------------------------- introductie en profiel */

  var profiel = { language: "nl" };

  function toonMinderjarig(p) {
    var blok = el("minderjarig");
    if (!p.minor) { blok.hidden = true; return; }
    blok.hidden = false;
    blok.innerHTML = p.language === "en"
      ? "<strong>You are under 18.</strong> You can use Dreamverse, but ask a parent " +
        "or guardian before buying anything in the app — subscriptions, tokens or video."
      : "<strong>Je bent onder de achttien.</strong> Je mag Dreamverse gewoon gebruiken, " +
        "maar vraag eerst toestemming aan je ouder of voogd voordat je iets koopt — " +
        "een abonnement, tokens of video.";
  }

  // Elk taalfilmpje is apart ingesproken en gelipsynchroniseerd; de tekst
  // eronder verandert mee.
  // stilVanaf is het punt waar hij na afloop naartoe terugspoelt: de plek in de
  // stille staart waarvan het beeld het meest op het slotbeeld lijkt. Daardoor
  // is de rondgang nauwelijks te zien, en het blijft één opname.
  var INTRO = {
    nl: { video: "vera-intro-nl.mp4", stilVanaf: 8.46,
          tekst: "Hi, ik ben Vera, de digitale droom-annalist. Wil je je droom met mij delen?" },
    en: { video: "vera-intro-en.mp4", stilVanaf: 5.4,
          tekst: "Hi, I'm Vera, your digital dream analyst. Would you like to share your dream with me?" }
  };

  function zetIntroTaal(taal) {
    var i = INTRO[taal] || INTRO.nl;
    el("intro-tekst").textContent = i.tekst;
    if (el("intro-video")) { begroetingSpelen(); }
  }

  function zetVlaggen(taal) {
    document.querySelectorAll(".vlag").forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.taal === taal ? "true" : "false");
    });
    // De taal eerlijk melden, maar vertalen blijft uit: de knoppen zijn Nederlands
    // tot de hele interface vertaald is, en een half vertaalde pagina leest slechter
    // dan een hele in één taal.
    document.documentElement.lang = taal;
    document.documentElement.setAttribute("translate", "no");
    if (window.vertaalPagina) { window.vertaalPagina(taal); }
    laadAccount();
    // De legenda van het spectrum wordt in JavaScript gebouwd, dus die moet
    // opnieuw getekend worden; de woordenlijst komt er niet vanzelf langs.
    laadSpectrum();
    // En de knop van de uitklap: taal.js heeft "Bekijken" als data-nl onthouden
    // en zet die bij een taalwissel terug, ook als er "Verbergen" stond. Dan
    // klopt het opschrift niet meer met wat er open staat.
    spectrumUitklap(!el("spectrum-inhoud") || !el("spectrum-inhoud").hidden);
    // Zelfde verhaal voor de gidslinks: die bestonden nog niet toen taal.js
    // keek, dus die blijven anders in de oude taal staan naast een vertaalde
    // placeholder. En de adressen wisselen mee: /dream-meaning of /nl daarvoor.
    gidsTonen(el("gids-veld") ? el("gids-veld").value : "");
    // De brilknoppen worden in JavaScript gemaakt, dus die komen niet langs de
    // vertaalslag van de pagina.
    toonBrillen();
    begroet(begroetteNaam);
    toonNaam(begroetteNaam || naamVeld.value.trim());
    zetIntroTaal(taal);
  }

  function bewaarProfiel(extra) {
    var body = {
      name: el("i-naam").value.trim(),
      birthdate: el("i-geboorte").value,
      gender: el("i-geslacht").value,
      language: profiel.language
    };
    Object.keys(extra || {}).forEach(function (k) { body[k] = extra[k]; });
    return fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); }).then(function (p) {
      profiel = p;
      toonMinderjarig(p);
      zetVlaggen(p.language);
      naamVeld.value = p.name || "";
      toonNaam(p.name || "");
      return p;
    });
  }

  // Taal raden uit de browser als er nog niets gekozen is. Amerikaans-Engels
  // is de standaard; Nederlands alleen als de browser dat zegt.
  function geradenTaal() {
    var t = (navigator.language || "en").toLowerCase();
    return t.indexOf("nl") === 0 ? "nl" : "en";
  }

  document.querySelectorAll(".vlag").forEach(function (b) {
    b.addEventListener("click", function () {
      profiel.language = b.dataset.taal;
      zetVlaggen(profiel.language);
      bewaarProfiel().then(function () { laadAccount(); });
    });
  });

  el("i-geboorte").addEventListener("change", function () { bewaarProfiel(); });

  /* Wie de introductie een keer gezien heeft, krijgt hem niet meer.
   *
   * Hij stond onvoorwaardelijk aan, dus Vera stelde zich bij elke keer openen
   * opnieuw voor - ook aan iemand die zijn negende droom komt vertellen. Dat is
   * een begroeting die een drempel wordt. Hij is niet weg: bij Je gegevens haal
   * je hem terug via "Introductie opnieuw" bij Je gegevens.
   */
  var INTRO_GEZIEN = "dreamverse_intro_gezien";

  function introSluiten() {
    el("intro").hidden = true;
    try { el("intro-video").pause(); } catch (e) { /* al gestopt */ }
    try { localStorage.setItem(INTRO_GEZIEN, "ja"); } catch (e) { /* mag niet */ }
  }

  function introAlGezien() {
    try { return localStorage.getItem(INTRO_GEZIEN) === "ja"; } catch (e) { return false; }
  }

  el("intro-start").addEventListener("click", function () {
    bewaarProfiel().then(function () {
      introSluiten();
      el("dream").focus();
    });
  });
  el("intro-later").addEventListener("click", introSluiten);

  // De weg terug. Zonder dit zijn je naam, geboortedatum en geslacht na de
  // eerste keer onbereikbaar - dat venster is de enige plek waar ze staan, en
  // de geboortedatum bepaalt de leeftijdscontrole bij een aankoop.
  if (el("intro-terug")) {
    el("intro-terug").addEventListener("click", function () {
      el("intro").hidden = false;
      el("intro").scrollIntoView({ block: "center" });
    });
  }

  // Eén klik zet het geluid aan en speelt vanaf het begin. Daarna mag de
  // browser de rest van de sessie ook geluid van ons afspelen.
  /* Vera's welkomstboodschap.
   *
   * Ze moet gewoon praten zodra de app opengaat. Wat er niet mag gebeuren is
   * dat ze haar tekst geluidloos staat te mimen: dat is het eerste wat iemand
   * van Dreamverse ziet, en het leest als een storing.
   *
   * Browsers weigeren geluid voordat je iets hebt aangeklikt. Lukt het niet,
   * dan komt niet de pratende clip in beeld maar de stille lus - ademen en
   * knipperen, mond dicht - met een knop ernaast. Zo klopt het beeld altijd bij
   * wat je hoort.
   */
  var geluidKnop = el("geluid-aan");
  var introVideo = el("intro-video");

  function introDeel() {
    return INTRO[(profiel && profiel.language) || "nl"] || INTRO.nl;
  }

  function zetKnop(soort) {
    if (!geluidKnop) { return; }
    geluidKnop.hidden = false;
    geluidKnop.dataset.doet = soort;
    if (soort === "dempen") {
      geluidKnop.innerHTML = '<span aria-hidden="true">🔇</span> ' + t("Geluid uit");
    } else {
      geluidKnop.innerHTML = '<span aria-hidden="true">🔊</span> ' +
                             t(introVideo.dataset.gehoord ? "Nog een keer" : "Hoor Vera");
    }
  }

  // Naar de stille staart van dezelfde clip: daar praat ze niet meer maar staat
  // ze wel te ademen en te kijken. Eén bestand, dus er valt niets te knippen.
  function stilZetten() {
    introVideo.dataset.staat = "stil";
    introVideo.muted = true;
    introVideo.loop = false;
    var spoel = function () {
      introVideo.currentTime = introDeel().stilVanaf;
      introVideo.play().catch(function () { /* mag mislukken */ });
    };
    // Terugspoelen kan pas als de lengte bekend is; anders begint hij bij nul en
    // staat ze alsnog geluidloos te mimen.
    if (introVideo.readyState >= 1) {
      spoel();
    } else {
      introVideo.addEventListener("loadedmetadata", function eenmalig() {
        introVideo.removeEventListener("loadedmetadata", eenmalig);
        spoel();
      });
    }
    zetKnop("horen");
  }

  // Welke taal er al begroet heeft. Zonder dit begint Vera opnieuw zodra iets
  // anders de taalfunctie aanroept, en valt ze zichzelf in de rede.
  var begroetIn = "";

  /* Welke poging is de jongste?
   *
   * Twee aanroepen kort na elkaar vechten om dezelfde videospeler. De oudste
   * krijgt van de browser een afgebroken play() terug, en die belandde in de
   * catch hieronder - die zette de speler op stil en zette een nieuwe wachter,
   * dus midden in de jongere begroeting. Met een rondenummer weet een poging of
   * hij nog de actuele is.
   */
  var begroetingRonde = 0;

  function begroetingSpelen(geforceerd) {
    if (!introVideo) { return; }
    // Kom je terug van een aankoop, dan begint ze niet. Anders praat ze door in
    // een verborgen scherm - je hoort haar wel en ziet haar niet.
    if (terugVanBetaling && !geforceerd) { return; }
    var taal = (profiel && profiel.language) || "nl";
    if (!geforceerd && begroetIn === taal) { return; }
    begroetIn = taal;
    introVideo.dataset.staat = "praat";
    introVideo.muted = false;
    introVideo.loop = false;
    var bron = introDeel().video;
    if (introVideo.getAttribute("src") !== bron) {
      introVideo.setAttribute("src", bron);
      introVideo.load();
    } else {
      introVideo.currentTime = 0;
    }
    var ronde = ++begroetingRonde;
    var poging = introVideo.play();
    if (!poging || !poging.then) { return; }
    poging.then(function () {
      if (ronde !== begroetingRonde) { return; }
      introVideo.dataset.gehoord = "ja";
      zetKnop("dempen");
    }).catch(function () {
      // Achterhaald: er loopt al een nieuwere begroeting. Die niet stilzetten.
      if (ronde !== begroetingRonde) { return; }
      // De browser wil nog geen geluid voordat je iets hebt aangeklikt; dat is
      // een regel van de browser en daar komt geen enkele app omheen. Dan liever
      // de stille staart dan een pratende Vera die je niet hoort - en zodra je
      // wat dan ook aanraakt begint ze alsnog. Zo hoef je die knop niet te
      // zoeken.
      stilZetten();
      wachtOpAanraking();
    });
  }

  var aanrakingWacht = false;

  function wachtOpAanraking() {
    if (aanrakingWacht) { return; }
    aanrakingWacht = true;
    var soorten = ["pointerdown", "keydown", "touchstart"];
    var alsnog = function (e) {
      // Een klik op een taalvlag of op de geluidsknop niet opeten.
      //
      // Zo'n klik was tot nu toe twee dingen tegelijk: deze wachter startte de
      // begroeting in de taal van daarvoor, en de knop zelf startte hem in de
      // nieuwe. Dan hoorde je Vera twee keer, in twee talen, op één speler.
      // Die knoppen regelen hun eigen begroeting; hier alleen doorlaten.
      var doel = e && e.target && e.target.closest
        ? e.target.closest(".vlag, .geluid-aan")
        : null;
      if (doel) { return; }
      soorten.forEach(function (n) { document.removeEventListener(n, alsnog, true); });
      aanrakingWacht = false;
      // Niet als de introductie al weg is: dan wil je geen stem uit het niets.
      if (el("intro") && !el("intro").hidden) { begroetingSpelen(true); }
    };
    soorten.forEach(function (n) { document.addEventListener(n, alsnog, true); });
  }

  if (geluidKnop && introVideo) {
    geluidKnop.addEventListener("click", function () {
      if (geluidKnop.dataset.doet === "dempen") { stilZetten(); } else { begroetingSpelen(true); }
    });
    introVideo.addEventListener("ended", function () {
      // Aan het eind terug naar de staart in plaats van stilstaan op het laatste
      // beeld. Alles komt uit dezelfde opname, dus ze blijft dezelfde vrouw.
      stilZetten();
    });
  }

  function toonIntro() {
    fetch("/api/profile").then(function (r) { return r.json(); }).then(function (p) {
      profiel = p;
      if (!p.language) { profiel.language = geradenTaal(); }
      el("i-naam").value = p.name || "";
      el("i-geboorte").value = p.birthdate || "";
      el("i-geslacht").value = p.gender || "onbekend";
      zetVlaggen(profiel.language);
      toonMinderjarig(p);
      naamVeld.value = p.name || "";
      toonNaam(p.name || "");
      if (terugVanBetaling) {
        // Overslaan, en zorgen dat Vera niet alsnog begint te praten.
        el("intro").hidden = true;
        try { el("intro-video").pause(); } catch (e) { /* al stil */ }
        var doel = el("account");
        if (doel) { doel.scrollIntoView({ behavior: "smooth", block: "center" }); }
        return;
      }
      // Alleen bij de eerste keer. Daarna is het geen introductie meer maar
      // een tussenscherm tussen jou en je droom.
      //
      // En ook niet bij wie zijn droom al verteld heeft voordat hij een account
      // maakte. Die heeft zijn naam net ingevuld, staat op het punt zijn droom
      // te zien, en krijgt dan een venster dat opnieuw om zijn naam vraagt plus
      // geboortedatum en geslacht. Dat is precies het scherm waar dit hele
      // eerste-droom-pad omheen gebouwd is. Geboortedatum wordt pas gevraagd
      // bij een aankoop, en de introductie staat bij Je gegevens.
      el("intro").hidden = introAlGezien() || startteMetDroom;
    }).catch(function () { el("intro").hidden = introAlGezien(); });
  }

  /* --------------------------------------------------------------- starten */

  /* ------------------------------------------------------------- inloggen */

  /* De poort.
   *
   * Zonder account is er niets te zien: je dromen horen bij jou, en tien mensen
   * in hetzelfde archief is geen product maar een ongeluk. Registreren logt
   * meteen in - een bevestigingsmail mag niet tussen iemand en zijn eerste
   * droom in staan.
   */
  var poortModus = "inloggen";

  // Kom je terug van een aankoop, dan geen introductiefilmpje: dan wil je zien
  // wat je gekocht hebt.
  var terugVanBetaling = false;

  function zetPoortModus(modus) {
    poortModus = modus;
    var nieuw = modus === "nieuw";
    el("tab-inloggen").setAttribute("aria-pressed", nieuw ? "false" : "true");
    el("tab-nieuw").setAttribute("aria-pressed", nieuw ? "true" : "false");
    el("veld-naam").hidden = !nieuw;
    el("p-hint").hidden = !nieuw;
    el("p-wachtwoord").setAttribute("autocomplete",
                                    nieuw ? "new-password" : "current-password");
    el("p-vergeten").hidden = nieuw;
    el("poort-door").textContent = nieuw ? t("Account maken") : t("Inloggen");
    el("poort-fout").hidden = true;
  }

  /* Eerst de droom, dan pas het account.
   *
   * Het eerste scherm was naam, e-mail en wachtwoord - gevraagd aan iemand die
   * nog niet weet wat hij ervoor terugkrijgt. Nu vertelt hij eerst zijn droom;
   * dat is waarvoor hij kwam, en daarna is er ook een reden om een account te
   * maken: hij wil zien wat ermee gebeurt.
   *
   * De tekst blijft tot dat moment alleen in deze browser. Een droom is een
   * bijzonder persoonsgegeven en er is nog geen account om hem aan te hangen,
   * dus hij gaat pas naar de server als de gebruiker bestaat. Een dag is de
   * grens: daarna is het geen "net gedroomd" meer en zou een oude tekst in een
   * nieuwe ochtend opduiken.
   */
  var EERSTE_DROOM = "dreamverse_eerste_droom";
  var EERSTE_DROOM_UUR = 24;
  // Of deze sessie begon met een droom die vóór het account verteld is.
  // toonIntro() haalt eerst het profiel op en is dus later klaar dan
  // eersteDroomOverzetten(), die de opslag leegmaakt; zonder deze vlag zou de
  // introductie alsnog opengaan omdat er tegen die tijd niets meer staat.
  var startteMetDroom = false;

  /* De taal van de poort komt niet uit het profiel, want dat is er nog niet.
   *
   * Zolang de poort een inlogvenster was viel dat nauwelijks op. Nu is het het
   * eerste scherm van het product: iemand komt van de Engelse landingspagina,
   * drukt op "Start for free", en kreeg dan een Nederlandse vraag. Dezelfde
   * sleutel als welkom.html en privacy.html, dus de keuze die daar gemaakt is
   * geldt hier ook - en anders wat de browser zegt, met Engels als standaard.
   */
  function poortTaal() {
    var opgeslagen = null;
    try { opgeslagen = localStorage.getItem("dreamverse_taal"); } catch (e) { /* niets */ }
    if (opgeslagen === "nl" || opgeslagen === "en") { return opgeslagen; }
    return /^nl\b/i.test(navigator.language || "") ? "nl" : "en";
  }

  function poortOpenen() {
    el("poort").hidden = false;
    var taal = poortTaal();
    document.documentElement.lang = taal;
    // Alleen de pagina vertalen: zetVlaggen() haalt er ook het account en het
    // spectrum bij, en die bestaan zonder sessie niet.
    if (window.vertaalPagina) { window.vertaalPagina(taal); }
    document.querySelectorAll(".vlag").forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.taal === taal ? "true" : "false");
    });
    poortStap(eersteDroomLezen() ? "account" : "vertel");
  }

  function eersteDroomLezen() {
    try {
      var rauw = localStorage.getItem(EERSTE_DROOM);
      if (!rauw) { return ""; }
      var d = JSON.parse(rauw);
      if (!d || !d.tekst) { return ""; }
      if (Date.now() - (d.wanneer || 0) > EERSTE_DROOM_UUR * 3600000) {
        localStorage.removeItem(EERSTE_DROOM);
        return "";
      }
      return d.tekst;
    } catch (e) { return ""; }
  }

  function eersteDroomBewaren(tekst) {
    try {
      localStorage.setItem(EERSTE_DROOM,
                           JSON.stringify({ tekst: tekst, wanneer: Date.now() }));
    } catch (e) { /* privévenster: dan leeft hij alleen in dit tabblad */ }
  }

  function eersteDroomWissen() {
    try { localStorage.removeItem(EERSTE_DROOM); } catch (e) { /* niets */ }
  }

  /* Welke van de drie stappen de poort laat zien.
   *
   * "vertel"   het droomveld, geen account in beeld
   * "account"  je droom staat klaar, maak er een aan
   * "inloggen" de gewone poort, voor wie er al een heeft
   */
  function poortStap(naam) {
    var vertel = el("poort-vertel");
    var klaar = el("poort-klaar");
    var tabs = document.querySelector(".poort-tabs");
    var form = el("poort-form");
    if (!vertel || !klaar || !tabs || !form) { return; }

    vertel.hidden = naam !== "vertel";
    klaar.hidden = naam !== "account";
    tabs.hidden = naam === "vertel";
    form.hidden = naam === "vertel";
    // De belofte bovenaan zegt waar dit over gaat; bij het droomveld is dat de
    // vraag zelf, en dan staan er twee koppen boven elkaar.
    var belofte = document.querySelector(".poort-belofte");
    var sub = document.querySelector(".poort-sub");
    if (belofte) { belofte.hidden = naam !== "vertel"; }
    if (sub) { sub.hidden = naam === "vertel"; }

    if (naam === "account") {
      zetPoortModus("nieuw");
      setTimeout(function () { el("p-naam").focus(); }, 60);
    } else if (naam === "inloggen") {
      zetPoortModus("inloggen");
      setTimeout(function () { el("p-email").focus(); }, 60);
    } else {
      el("poort-droom").value = eersteDroomLezen();
      setTimeout(function () { el("poort-droom").focus(); }, 60);
    }
  }

  /* Inspreken op het eerste scherm.
   *
   * Bewust niet setupMic(): die schrijft in het invoerveld van de app en praat
   * tegen Vera's regel en de statusbalk, en geen van drieën bestaat hier. Wat de
   * twee wél delen is de taalkeuze, de vertaling van de foutcodes en de
   * niveaumeter.
   */
  function poortMic() {
    var knop = el("poort-mic");
    var veld = el("poort-droom");
    var fout = el("poort-vertel-fout");
    if (!knop || !veld) { return; }
    if (!Recognition) {
      knop.disabled = true;
      // Dit is het eerste scherm, en dus wat iemand van de bio-link ziet.
      hintVervangen(el("poort-vertel").querySelector(".invoer-hint"),
                    geenSpraakUitleg());
      return;
    }
    knop.addEventListener("click", function () {
      if (listening) { recogniser.stop(); return; }
      recogniser = new Recognition();
      recogniser.lang = taalcode();
      recogniser.continuous = true;
      recogniser.interimResults = true;
      var settled = veld.value ? veld.value + " " : "";

      recogniser.onstart = function () {
        listening = true;
        knop.classList.add("rec");
        knop.textContent = t("Stop met opnemen");
        meterStarten("poort-mic-meter");
      };
      recogniser.onresult = function (e) {
        var live = "";
        for (var i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) { settled += e.results[i][0].transcript + " "; }
          else { live += e.results[i][0].transcript; }
        }
        veld.value = (settled + live).replace(/\s+/g, " ").trimStart();
      };
      recogniser.onerror = function (e) {
        fout.textContent = t(spraakfout(e.error));
        fout.hidden = false;
      };
      recogniser.onend = function () {
        listening = false;
        meterStoppen();
        knop.classList.remove("rec");
        knop.textContent = t("Inspreken");
      };
      recogniser.start();
    });
  }
  poortMic();

  /* Eén regel bij de knop van Vera, als we in de browser van Instagram staan.
   *
   * Een gesprek wordt ná afloop afgerekend op werkelijk gesproken tijd. Wie
   * hier begint en niet gehoord wordt omdat de app-browser niet bij de
   * microfoon komt, heeft dus wél betaald voor de minuut waarin hij tegen niets
   * praatte. Vóór de klik waarschuwen is daarom geen vriendelijkheid maar het
   * verschil tussen een mislukte poging en een mislukte poging met een rekening.
   */
  function instagramWaarschuwing() {
    var doos = el("call-melding");
    if (!instagramBrowser() || !doos) { return; }
    var bron = "Je bekijkt Dreamverse in de browser van Instagram. Praten met"
      + " Vera werkt daar niet altijd: tik op de drie puntjes en kies Openen in"
      + " Safari of Openen in Chrome.";
    doos.hidden = false;
    doos.dataset.nl = bron;
    doos.textContent = t(bron);
  }
  instagramWaarschuwing();

  if (el("poort-verder")) {
    el("poort-verder").addEventListener("click", function () {
      var veld = el("poort-droom");
      var fout = el("poort-vertel-fout");
      var tekst = veld.value.trim();
      // Twintig tekens is geen kwaliteitseis maar een vergissingsdrempel: onder
      // dat aantal heeft iemand op Verder gedrukt zonder iets te vertellen, en
      // dan is een account maken zinloos.
      if (tekst.length < 20) {
        fout.textContent = t("Vertel er nog iets meer over, dan kan Vera er iets mee.");
        fout.hidden = false;
        veld.focus();
        return;
      }
      fout.hidden = true;
      eersteDroomBewaren(tekst);
      poortStap("account");
    });
  }
  if (el("poort-al-account")) {
    el("poort-al-account").addEventListener("click", function () {
      poortStap("inloggen");
    });
  }
  if (el("poort-terug")) {
    el("poort-terug").addEventListener("click", function () {
      poortStap("vertel");
    });
  }

  /* De droom die vóór het account verteld is, in de app zetten.
   *
   * Niet meteen versturen. Verbeelden kost geld en soms tokens, en de kwaliteit
   * is een keuze die hij nog niet gemaakt heeft - dezelfde reden waarom een
   * gesprek met Vera ook nooit vanzelf een verbeelding wordt. Dus: de tekst
   * staat er, de knop licht op, en hij drukt.
   */
  function eersteDroomOverzetten() {
    var tekst = eersteDroomLezen();
    if (!tekst) { return; }
    var veld = el("dream");
    if (!veld) { return; }
    if (!veld.value.trim()) { veld.value = tekst; }
    eersteDroomWissen();
    setTimeout(function () {
      veld.scrollIntoView({ behavior: "smooth", block: "center" });
      var go = el("go");
      if (go) {
        go.classList.add("wijs");
        setTimeout(function () { go.classList.remove("wijs"); }, 3000);
      }
    }, 400);
  }

  // Laten zien wat je typt. Zonder dit is een wachtwoord op een telefoon
  // intypen de snelste manier om iemand te laten afhaken.
  el("p-oog").addEventListener("click", function () {
    var veld = el("p-wachtwoord");
    var open = veld.type === "text";
    veld.type = open ? "password" : "text";
    this.textContent = t(open ? "laat zien" : "verberg");
    this.setAttribute("aria-label", t(open ? "Wachtwoord laten zien" : "Wachtwoord verbergen"));
    veld.focus();
  });

  el("p-vergeten").addEventListener("click", function () {
    var fout = el("poort-fout");
    var adres = el("p-email").value.trim();
    if (!adres) {
      fout.className = "poort-fout";
      fout.textContent = t("Vul eerst je e-mailadres in, dan sturen we je een nieuwe link.");
      fout.hidden = false;
      el("p-email").focus();
      return;
    }
    fout.className = "poort-fout";
    fout.textContent = t("Bezig…");
    fout.hidden = false;
    fetch("/api/wachtwoord-vergeten", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: adres })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) { fout.textContent = d.melding || t("Verstuurd."); })
      .catch(function () { fout.textContent = t("Dat lukte niet."); });
  });

  el("tab-inloggen").addEventListener("click", function () { zetPoortModus("inloggen"); });
  el("tab-nieuw").addEventListener("click", function () { zetPoortModus("nieuw"); });

  el("poort-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var knop = el("poort-door");
    var fout = el("poort-fout");
    fout.hidden = true;
    knop.disabled = true;
    knop.textContent = t("Bezig…");

    var pad = poortModus === "nieuw" ? "/api/registreren" : "/api/inloggen";
    fetch(pad, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: el("p-email").value.trim(),
        wachtwoord: el("p-wachtwoord").value,
        naam: el("p-naam").value.trim(),
        // De taal waarin de poort staat is de taal waarin hij zijn droom net
        // verteld heeft. De duiding wordt geschreven en niet vertaald, dus dit
        // is de enige plek waar dat nog goed te zetten is.
        taal: poortTaal()
      })
    })
      .then(lees)
      .then(function (res) {
        if (!res.ok) { throw new Error(res.body.error || t("Dat lukte niet.")); }
        el("poort").hidden = true;
        el("p-wachtwoord").value = "";
        binnen(res.body.profile || {});
      })
      .catch(function (err) {
        fout.textContent = err.message;
        fout.hidden = false;
      })
      .then(function () {
        // Alleen de knop terugzetten. zetPoortModus() zou de foutmelding die we
        // net getoond hebben meteen weer verbergen.
        knop.disabled = false;
        knop.textContent = poortModus === "nieuw" ? t("Account maken") : t("Inloggen");
      });
  });

  /* ------------------------------------------------------------- afrekenen */

  /* Betalen gebeurt op de pagina van Stripe, niet hier.
   *
   * Zij worden de verkoper: zij innen de btw en dragen hem af in ruim tachtig
   * landen. Er komt daarom geen kaartnummer in deze app - niet in het formulier,
   * niet in het geheugen, nergens. Wij sturen je erheen en horen achteraf van
   * Stripe wat er gekocht is.
   */
  /* Opwaarderen moet één klik zijn vanaf het getal dat je aankijkt.
   *
   * De koopknoppen stonden er al, maar onderaan de pagina onder "Los te koop" -
   * voorbij de invoer, de panelen, het archief en de pakketten. Wie ziet dat hij
   * nul tokens heeft, staat bovenaan en gaat niet zoeken. Dus wijst het getal nu
   * zelf de weg, en licht het doel even op zodat je ziet dat je goed bent.
   */
  function naarTokens() {
    var doel = el("tokenpakketten");
    if (!doel || doel.hidden) {
      // Afrekenen staat uit; dan is er niets om naartoe te wijzen.
      return;
    }
    doel.scrollIntoView({ behavior: "smooth", block: "center" });
    doel.classList.add("wijs");
    setTimeout(function () { doel.classList.remove("wijs"); }, 2400);
  }

  function naarStripe(body) {
    /* Voor een minderjarige eerst een vraag, en alleen hier.
     *
     * Niet bij binnenkomst: een leeftijdsvraag op de deurmat is precies de
     * drempel die we juist weghalen, en hij zegt niets - iedereen klikt "ja".
     * Bij het afrekenen doet hij er wel toe, want dáár gaat geld om, en daar
     * weten we de leeftijd ook echt: die staat in het profiel en is bij het
     * aanmelden gevraagd, niet geraden.
     */
    if (profiel && profiel.minor) {
      var vraag = t("Je bent nog geen achttien. Vraag eerst toestemming aan je "
                    + "ouder of voogd voordat je iets koopt. Heb je die toestemming?");
      if (!window.confirm(vraag)) {
        var m = el("koop-melding");
        if (m) {
          m.className = "koop-melding err";
          m.textContent = t("Geen probleem. Dreamverse blijft gewoon werken; je "
                            + "kunt elke maand drie dromen laten duiden.");
        }
        return;
      }
    }

    var melding = el("koop-melding");
    if (melding) {
      melding.className = "koop-melding";
      melding.textContent = t("Je gaat naar de betaalpagina van Stripe…");
    }
    fetch("/api/kopen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
      .then(lees)
      .then(function (res) {
        if (!res.ok || !res.body.url) {
          throw new Error(res.body.error || t("Afrekenen lukte niet."));
        }
        window.location.href = res.body.url;
      })
      .catch(function (err) {
        if (melding) {
          melding.className = "koop-melding err";
          melding.textContent = err.message;
        }
      });
  }

  document.querySelectorAll(".koop-pakket").forEach(function (b) {
    b.addEventListener("click", function () {
      naarStripe({ soort: "pakket", welk: b.dataset.pakket });
    });
  });
  document.querySelectorAll(".koop-tokens").forEach(function (b) {
    b.addEventListener("click", function () {
      naarStripe({ soort: "tokens", welk: b.dataset.tokens });
    });
  });

  // De knoppen komen pas als afrekenen echt aanstaat. Een knop die "dat kan nog
  // niet" antwoordt is erger dan geen knop.
  /* Kwam hij binnen via een pakketknop op de landingspagina?
   *
   * Dan onthouden we welke, en brengen we hem na het inloggen naar de
   * pakketten. Niet kopen: dat blijft zijn eigen klik. Maar hij hoeft ook niet
   * opnieuw te zoeken wat hij net al had aangewezen.
   */
  var gekozenViaWelkom = (function () {
    var m = /[?&]kies=(gratis|lite|plus|ultra)/.exec(location.search);
    if (!m) { return ""; }
    history.replaceState(null, "", location.pathname);
    return m[1];
  })();

  function naarPakket() {
    if (!gekozenViaWelkom) { return; }
    var doel = document.querySelector('.koop-pakket[data-pakket="' + gekozenViaWelkom + '"]');
    var sectie = doel ? doel.closest("section") : null;
    gekozenViaWelkom = "";
    if (!sectie) { return; }
    sectie.scrollIntoView({ behavior: "smooth", block: "center" });
    if (doel) {
      doel.classList.add("wijs");
      setTimeout(function () { doel.classList.remove("wijs"); }, 2400);
    }
  }

  function toonKoopknoppen(aan) {
    betalenAan = !!aan;
    document.querySelectorAll(".koop-pakket").forEach(function (b) { b.hidden = !aan; });
    var doos = el("tokenpakketten");
    if (doos) { doos.hidden = !aan; }
    // De opwaardeerknoppen zitten in kaarten die al getekend kunnen zijn
    // voordat /api/health antwoord gaf.
    laadAccount();
    if (aan) { setTimeout(naarPakket, 400); }
  }

  function naarPortaal() {
    fetch("/api/portaal", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.url) { window.location.href = d.url; }
      })
      .catch(function () { /* niets */ });
  }

  /* -------------------------------------------------- je gegevens weghalen */

  /* Verwijderen vraagt om het wachtwoord.
   *
   * Dit is onomkeerbaar en het gaat over iemands hele archief. Een verdwaalde
   * klik, of een openstaand tabblad op een gedeelde computer, mag dat niet
   * kosten. Het wachtwoord is het enige wat een ander niet heeft.
   */
  if (el("verwijder-open")) {
    el("verwijder-open").addEventListener("click", function () {
      el("verwijder-vraag").hidden = false;
      el("verwijder-open").hidden = true;
      el("verwijder-wachtwoord").focus();
    });
    el("verwijder-terug").addEventListener("click", function () {
      el("verwijder-vraag").hidden = true;
      el("verwijder-open").hidden = false;
      el("verwijder-wachtwoord").value = "";
      el("verwijder-melding").textContent = "";
    });
    el("verwijder-echt").addEventListener("click", function () {
      var melding = el("verwijder-melding");
      melding.className = "verwijder-melding";
      melding.textContent = t("Bezig…");
      fetch("/api/account-verwijderen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ wachtwoord: el("verwijder-wachtwoord").value })
      })
        .then(lees)
        .then(function (res) {
          if (!res.ok) { throw new Error(res.body.error || t("Dat lukte niet.")); }
          document.body.innerHTML =
            '<div class="afscheid"><h1>' + t("Alles is weg.") + "</h1><p>" +
            t("Je account, je dromen en al het beeld zijn verwijderd. Er is geen kopie.") +
            "</p></div>";
        })
        .catch(function (err) {
          melding.className = "verwijder-melding err";
          melding.textContent = err.message;
        });
    });
  }

  function uitloggen() {
    fetch("/api/uitloggen", { method: "POST" })
      .then(function () { location.reload(); })
      .catch(function () { location.reload(); });
  }

  // Alles wat pas mag als je binnen bent.
  function binnen(p) {
    profiel = p;
    document.body.classList.add("ingelogd");

    // Terug van de betaalpagina.
    //
    // Niet bij Vera uitkomen die opnieuw begint te praten: je komt van een
    // aankoop en wilt zien wat je gekocht hebt. Dus de introductie overslaan en
    // meteen naar je pakket.
    //
    // De webhook van Stripe komt los binnen en is er meestal al, maar niet
    // altijd - vandaar nog twee keer kijken.
    var betaald = /[?&]betaald=1/.test(location.search);
    if (betaald) {
      terugVanBetaling = true;
      setTimeout(laadAccount, 2500);
      setTimeout(laadAccount, 7000);
      history.replaceState(null, "", location.pathname);
    } else if (/[?&]betaald=0/.test(location.search)) {
      history.replaceState(null, "", location.pathname);
    }

    // Terug van de link uit de welkomstmail. Zeggen dat het gelukt is, want
    // anders klik je op een link in je mail en beland je op een pagina die doet
    // alsof er niets gebeurd is.
    if (/[?&]bevestigd=1/.test(location.search)) {
      statusEl.className = "status";
      statusEl.textContent = t("Je e-mailadres is bevestigd. Dank je.");
      history.replaceState(null, "", location.pathname);
    } else if (/[?&]bevestigd=0/.test(location.search)) {
      statusEl.className = "status err";
      statusEl.textContent = t("Die bevestigingslink is niet geldig of al gebruikt.");
      history.replaceState(null, "", location.pathname);
    }
    startteMetDroom = !!eersteDroomLezen();
    toonIntro();
    laadGids();
    loadArchive();
    laadAccount();
    // Heeft hij zijn droom verteld voordat hij een account had, dan staat die
    // hier klaar. Hier en niet in de poort: zo werkt het ook als de pagina
    // tussendoor ververst is.
    eersteDroomOverzetten();
  }

  /* --------------------------------------------------------------- starten */

  setupMic();

  // Wie is er? Bestaat er geen sessie, dan de poort en niets anders.
  fetch("/api/profile")
    .then(function (r) {
      if (r.status === 401) {
        // Staat er al een droom klaar, dan is het account de volgende stap; zo
        // niet, dan begint het bij de vraag waarvoor hij kwam.
        poortOpenen();
        return null;
      }
      return r.json();
    })
    .then(function (p) { if (p) { binnen(p); } })
    .catch(function () { poortOpenen(); });
  fetch("/api/health")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      // De brontekst meegeven, anders weet de vertaalslag straks niet meer
      // welke van de twee toestanden hier stond.
      toonKoopknoppen(!!d.betalen);
      el("mode").dataset.nl = d.key ? "verbonden" : "voorbeeldmodus";
      el("mode").textContent = t(el("mode").dataset.nl);
      if (!d.vera) {
        el("call").disabled = true;
        el("call").title = t("Vera is niet aangesloten");
      }
    })
    .catch(function () { el("mode").dataset.nl = "offline"; el("mode").textContent = "offline"; });
})();
