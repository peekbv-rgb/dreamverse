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
      merk.textContent = eigenFilm ? "film" : "kernmoment";
      stage.appendChild(merk);
      narration.textContent = panel.narration;
      counter.textContent = (index + 1) + " / " + total;
      el("prev").disabled = index === 0;
      el("next").textContent = index === total - 1 ? "Opnieuw" : "Verder";
      var pips2 = bar.querySelectorAll("span");
      for (var q = 0; q < pips2.length; q++) { pips2[q].classList.toggle("done", q <= index); }
      speak(panel.narration);
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
      regels.push(t("Kernmoment animeren — dit duurt ongeveer een minuut"));
    }
    if (state.film_status === "busy") {
      var f = Object.keys(state.film || {}).length;
      regels.push(t("Film maken —") + " " + f + " " + t("van de") + " " + totaal + " " +
                  t("panelen klaar"));
    }

    var stuk = [];
    if (state.video_status === "failed") {
      stuk.push(t("Het kernmoment lukte niet") +
                (state.video_error ? " — " + state.video_error : ""));
    }
    if (state.film_status === "failed") { stuk.push(t("De film lukte niet")); }
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

  function pollPanels(number, tries) {
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    if (tries <= 0) { return; }
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
        toonVoortgang(state);
        var bezig = state.status !== "done"
                 || (kernVideo && kernVideo.status === "busy")
                 || state.film_status === "busy"
                 || state.stem_status === "busy";
        if (bezig) {
          pollTimer = setTimeout(function () { pollPanels(number, tries - 1); }, 4000);
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

  function toonSamen(nummer, tekst, draden) {
    nummer = nummer || 0;
    if (nummer && nummer < samenVan) { return; }
    samenVan = nummer || samenVan;

    var samen = el("samen");
    samen.textContent = tekst || "";
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
        toen.textContent = t("Toen:") + " " + draad.was;
        var nu = document.createElement("p");
        nu.className = "then";
        nu.textContent = t("Nu:") + " " + draad.now;
        d.appendChild(tag); d.appendChild(toen); d.appendChild(nu);
        threadsEl.appendChild(d);
      });
    } else if (!tekst) {
      el("threads-title").textContent = t("Nog geen patroon");
      var leeg = document.createElement("div");
      leeg.className = "thread";
      leeg.textContent = t("Deze droom staat nog op zichzelf. Vanaf je tweede of derde droom vormt het web zich.");
      threadsEl.appendChild(leeg);
    } else {
      el("threads-title").textContent = t("Je dromen samen");
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
    var gezegd = {raak: "Je zei dat dit klopte.", deels: "Je zei dat dit deels klopte.",
                  mis: "Je zei dat dit niet uitkwam."};
    el("oordeel-vraag").textContent = gegeven
      ? t(gezegd[gegeven])
      : t("Dit stond hier") + " " + dagen + " " + t("dagen geleden. Klopte het?");
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
    if (ep.images_pending) { verwachtWerk(); pollPanels(ep.number, 90); }
    el("title").textContent = ep.title;
    // De kop draagt nu de titel van de droom, niet meer de slogan: dat is de
    // nieuwe brontekst, anders zet een taalwissel de slogan terug.
    el("title").dataset.nl = ep.title;
    toonBril(ep);
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

    toonSamen(ep.number, ep.together, ep.threads);

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
        if (!window.confirm("Droom " + d.n + " verwijderen? De panelen en de video gaan mee.")) { return; }
        fetch("/api/dream/" + d.n, { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function () { loadArchive(); laadVerbruik(); laadAccount(); })
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
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
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
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
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
  function vulKeuzelijst(dreams) {
    var kies = el("kies");
    if (!kies) { return; }
    kies.innerHTML = "";
    dreams.forEach(function (d) {
      var o = document.createElement("option");
      o.value = d.n;
      // Bewegend beeld heeft een getekend paneel nodig als startframe. Zonder
      // panelen valt er niets te kopen, en dat hoort hier te staan en niet pas
      // in een foutmelding nadat je geklikt hebt.
      o.disabled = !d.thumb;
      o.textContent = t("Droom") + " " + d.n + " — " +
                      (d.title || d.text || "").slice(0, 40) +
                      (d.thumb ? "" : "  (" + t("geen beeld") + ")");
      kies.appendChild(o);
    });
    if (!dreams.length) {
      var leeg = document.createElement("option");
      leeg.textContent = t("nog geen dromen");
      leeg.value = "";
      kies.appendChild(leeg);
    }
    // De eerste droom die wel beeld heeft, want een uitgeschakelde optie kan
    // niet geselecteerd staan.
    var bruikbaar = dreams.filter(function (d) { return d.thumb; })[0];
    kies.value = bruikbaar ? String(bruikbaar.n) : "";
    zetKoopKnoppen(!!bruikbaar);
  }

  function zetKoopKnoppen(mag) {
    document.querySelectorAll(".kies-droom .koop").forEach(function (b) {
      b.disabled = !mag;
      b.title = mag ? "" : t("Kies een droom waar panelen bij gemaakt zijn.");
    });
  }

  function loadArchive() {
    fetch("/api/archive")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        renderArchive(d.dreams || []);
        vulKeuzelijst(d.dreams || []);
        laadSpectrum();
        var samen = d.samen || {};
        toonSamen(samen.number, samen.together, samen.threads);
      })
      .catch(function () { /* archief is bijzaak; de app werkt zonder */ });
  }

  /* ------------------------------------------------------------- inspreken */

  var Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recogniser = null, listening = false;

  function setupMic() {
    var mic = el("mic");
    if (!Recognition) {
      mic.disabled = true;
      mic.title = t("Inspreken werkt in Chrome en Edge");
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
        statusEl.textContent = e.error === "not-allowed"
          ? t("Geen toegang tot de microfoon. Sta dat toe in je browser.")
          : t("Het opnemen stopte onverwacht. Typ anders even.");
      };
      recogniser.onend = function () {
        listening = false;
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

  function meeschrijvenStarten() {
    if (!Recognition) {
      // Firefox en Safari kunnen dit niet. Dat eerlijk zeggen is beter dan een
      // gesprek dat stil verdwijnt.
      meeschrijfMelding(t("Meeschrijven kan alleen in Chrome en Edge."), true);
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
      meeschrijfMelding(t("Meeschrijven stopte:") + " " + e.error, true);
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
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
      .then(function (res) {
        if (!res.ok) { throw new Error(res.body.error || t("Dat lukte niet.")); }
        melding.textContent = t("Onderweg. De zandloper onderin loopt mee.");
        verwachtWerk();
        startBezig(t("Aanvraag gestart…"));
        toonAccount(res.body.account);
        laadVerbruik();
        pollPanels(nummer, 90);
      })
      .catch(function (err) {
        melding.className = "extras-melding err";
        melding.textContent = err.message;
      })
      .then(function () { knop.disabled = false; });
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
    if (!window.confirm(t("Het hele archief wissen? De panelen, de video's en de ingesproken tekst gaan mee. Je volgende droom wordt Droom 1."))) { return; }
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
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
      .then(function (res) {
        if (!res.ok) { throw new Error(res.body.error || t("Het lukte niet.")); }
        var ep = res.body.episode;
        render(ep);
        input.value = "";
        loadArchive();
        laadVerbruik();
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
        go.textContent = t("Verbeeld mijn droom");
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
        .then(function () { laadVerbruik(); laadAccount(); }).catch(function () {});
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
    a.kwaliteiten.forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "kwaliteit" + (k.tokens && !k.betaalbaar ? " tekort" : "");
      b.dataset.kwaliteit = k.key;
      b.setAttribute("aria-pressed", k.key === gekozenKwaliteit ? "true" : "false");
      b.title = k.uitleg;
      /* Wat je krijgt én wat het kost.
       *
       * Hier stond alleen wat je kreeg zolang het in je pakket zat. Naast twee
       * knoppen met "4 tokens" en "10 tokens" leest dat als een prijs die er nog
       * bij komt maar die je niet ziet - en dan durf je niet te klikken. Nul
       * hardop zeggen is het hele punt van een pakket.
       */
      var kost = k.inbegrepen
        ? t("0 tokens")
        : k.tokens + " " + t(k.tokens === 1 ? "token" : "tokens");
      var regel = k.inbegrepen ? k.bevat + " · " + kost : kost;
      b.innerHTML = k.naam + "<small>" + regel + "</small>";
      if (k.beste) {
        b.classList.add("beste");
        b.insertAdjacentHTML("afterbegin", '<span class="vlagje">' + t("in je pakket") + '</span>');
      }
      b.addEventListener("click", function () { kiesKwaliteit(k); });
      doos.appendChild(b);
    });
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

  function toonAccount(a) {
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
    if (beheerAan) {
      ["gratis", "lite", "plus", "ultra"].forEach(function (p) {
        html += "<button type='button' data-plan='" + p + "' aria-pressed='" +
                (a.plan === p ? "true" : "false") + "'>" + t(p) + "</button>";
      });
      html += "<button type='button' data-tokens='10'>" + t("+10 tokens") + "</button>";
    }
    // Geen zichtbare beheerknop: dat is het enige knopje dat een bezoeker ziet
    // en niet snapt. Beheer zet je aan met ?beheer achter het adres; daarna
    // blijft de sleutel in deze browser staan en verschijnen de knoppen vanzelf.
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
    el("account").querySelectorAll("[data-plan]").forEach(function (b) {
      b.addEventListener("click", function () { zetAccount({ plan: b.dataset.plan }); });
    });
    el("account").querySelectorAll("[data-tokens]").forEach(function (b) {
      b.addEventListener("click", function () { zetAccount({ tokens: 10 }); });
    });
    el("account").querySelectorAll("[data-beheer]").forEach(function (b) {
      b.addEventListener("click", vraagBeheer);
    });
    el("account").querySelectorAll("[data-uit]").forEach(function (b) {
      b.addEventListener("click", uitloggen);
    });
    el("account").querySelectorAll("[data-portaal]").forEach(function (b) {
      b.addEventListener("click", naarPortaal);
    });
  }

  /* Pakket en saldo met de hand zetten.
   *
   * Dat is een beheerdershandeling: het is gratis Ultra met tien avatarminuten.
   * De server vraagt sindsdien om ADMIN_TOKEN, en die sleutel woont alleen in
   * deze browser. Wie hem niet heeft ziet de knoppen niet eens.
   */
  var BEHEER_SLEUTEL = "dreamverse_admin";

  // Staat afrekenen aan? Komt uit /api/health. Zonder dit weten de kaarten niet
  // of er een opwaardeerknop bij mag.
  var betalenAan = false;

  /* Zit je nú in beheer?
   *
   * De sleutel blijft in deze browser staan zodat je hem niet elke keer hoeft te
   * plakken, maar dat is iets anders dan in beheer zitten. Op de sleutel alleen
   * bleef de kostenmeter, de webhooklog en de pakketknoppen voorgoed in beeld,
   * ook als je de app gewoon als dromer opende. Beheer is een stand van dit
   * paginabezoek: aan met ?beheer achter het adres, weg zodra je de pagina
   * ververst zonder.
   */
  var beheerAan = false;

  function beheerSleutel() {
    try { return localStorage.getItem(BEHEER_SLEUTEL) || ""; } catch (e) { return ""; }
  }

  function zetAccount(body) {
    var sleutel = beheerSleutel();
    if (!sleutel) { return; }
    fetch("/api/account", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Admin-Token": sleutel },
      body: JSON.stringify(body)
    })
      .then(function (r) {
        if (r.status === 403) {
          try { localStorage.removeItem(BEHEER_SLEUTEL); } catch (e) { /* niets */ }
          throw new Error("sleutel afgekeurd");
        }
        return r.json();
      })
      .then(toonAccount)
      .catch(function () { laadAccount(); });
  }

  /* Beheer aanzetten met ?beheer achter het adres.
   *
   * Hier stond een letterlijk backspace-teken in de reguliere expressie: een
   * woordgrens die als stuurteken is weggeschreven in plaats van als tekst.
   * Daardoor matchte hij nooit en gebeurde er bij ?beheer niets, zonder enig
   * spoor: geen fout, geen melding, geen venster. Zoiets is in een editor
   * onzichtbaar; `python build/controle.py` zoekt er nu naar.
   */
  if (/[?&]beheer/.test(location.search)) {
    if (beheerSleutel()) {
      // Sleutel al bekend: meteen aan, zonder er weer om te vragen.
      beheerAan = true;
      history.replaceState(null, "", location.pathname);
    } else {
      setTimeout(function () { vraagBeheer(); }, 400);
    }
  }

  /* De beheersleutel vragen met een veld in de pagina.
   *
   * Dit was een window.prompt, en die kwam op Render niet. Chrome onderdrukt zo
   * een dialoog zodra het tabblad de focus niet heeft of de bezoeker ooit "geen
   * dialoogvensters meer" heeft aangevinkt - en dan is beheer onbereikbaar
   * zonder dat er iets te zien is. Een kaart in de pagina heeft dat probleem
   * niet, ligt boven het introvenster, en werkt op een telefoon.
   */
  function vraagBeheer() {
    var poort = el("beheerpoort");
    if (!poort) { return; }
    el("beheerpoort-fout").hidden = true;
    el("beheerpoort-sleutel").value = "";
    poort.hidden = false;
    setTimeout(function () { el("beheerpoort-sleutel").focus(); }, 60);
  }

  function beheerpoortSluiten() {
    if (el("beheerpoort")) { el("beheerpoort").hidden = true; }
    // Het adres schoon achterlaten, ook als je afhaakt: anders vraagt elke
    // verversing het opnieuw.
    if (/[?&]beheer/.test(location.search)) {
      history.replaceState(null, "", location.pathname);
    }
  }

  if (el("beheerpoort")) {
    el("beheerpoort-weg").addEventListener("click", beheerpoortSluiten);
    el("beheerpoort-oog").addEventListener("click", function () {
      var veld = el("beheerpoort-sleutel");
      var open = veld.type === "text";
      veld.type = open ? "password" : "text";
      this.textContent = open ? t("laat zien") : t("verberg");
      veld.focus();
    });
    el("beheerpoort").addEventListener("click", function (e) {
      if (e.target === this) { beheerpoortSluiten(); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !el("beheerpoort").hidden) { beheerpoortSluiten(); }
    });
    el("beheerpoort-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var sleutel = el("beheerpoort-sleutel").value.trim();
      var fout = el("beheerpoort-fout");
      var door = el("beheerpoort-door");
      if (!sleutel) { el("beheerpoort-sleutel").focus(); return; }
      fout.hidden = true;
      door.disabled = true;
      door.textContent = t("Bezig…");
      fetch("/api/account", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Token": sleutel },
        body: JSON.stringify({})
      }).then(function (r) {
        door.disabled = false;
        door.textContent = t("Aanzetten");
        if (r.status === 403) {
          // Twee verschillende oorzaken, en het scheelt een middag zoeken om te
          // weten welke van de twee het is.
          return r.json().catch(function () { return {}; }).then(function (d) {
            fout.textContent = /staat uit/.test(d.error || "")
              ? t("ADMIN_TOKEN staat niet in de omgeving van de server. Zonder die "
                  + "sleutel kan beheer helemaal niet - dat is de veilige stand.")
              : t("Die sleutel wordt niet geaccepteerd.");
            fout.hidden = false;
          });
        }
        if (!r.ok) {
          fout.textContent = t("Die sleutel wordt niet geaccepteerd.");
          fout.hidden = false;
          return;
        }
        try { localStorage.setItem(BEHEER_SLEUTEL, sleutel); } catch (e2) { /* niets */ }
        beheerAan = true;
        beheerpoortSluiten();
        laadAccount();
        laadVerbruik();
        naarBeheerrij();
      }).catch(function () {
        door.disabled = false;
        door.textContent = t("Aanzetten");
        fout.textContent = t("De server antwoordde niet. Probeer het nog eens.");
        fout.hidden = false;
      });
    });
  }

  /* Na het aanzetten meteen laten zien waar de knoppen staan.
   *
   * Zonder dit verschijnt er ergens onderaan de pagina een sectie die je niet
   * ziet, en lijkt het alsof de sleutel niets deed.
   */
  function naarBeheerrij() {
    setTimeout(function () {
      var doel = el("beheerrij");
      var sectie = el("meter-section");
      if (!doel || !sectie || sectie.hidden) { return; }
      doel.scrollIntoView({ behavior: "smooth", block: "center" });
      doel.classList.add("wijs");
      setTimeout(function () { doel.classList.remove("wijs"); }, 2400);
    }, 250);
  }

  function laadAccount() {
    fetch("/api/account").then(function (r) { return r.json(); })
      .then(toonAccount).catch(function () {});
  }

  /* ----------------------------------------------------------- wat het kost */

  function euro(n) { return "€" + n.toFixed(2).replace(".", ","); }

  function cel(waarde, label, klasse) {
    return '<div class="meter-cel ' + (klasse || "") + '"><b>' + waarde +
           "</b><span>" + label + "</span></div>";
  }

  function toonVerbruik(u) {
    var t = u.totals, m = el("meter");
    if (!t.dreams && !t.sessions && !t.panels) { return; }

    var html = '<div class="meter-cijfers">';
    html += cel(t.dreams, "dromen");
    html += cel(t.panels, "panelen");
    html += cel(t.sessions, "gesprekken");
    html += cel(Math.round(t.avatar_seconds) + " s", "avatartijd");
    html += cel(u.cost_per_dream === null ? "—" : euro(u.cost_per_dream),
                "per droom", "uitgelicht");
    html += cel(u.totals.videos, "kernmomenten");
    html += cel(euro(u.avatar_per_5min), "gesprek van 5 min", "uitgelicht");
    html += "</div>";

    if (u.by_day.length) {
      html += '<table class="dagen"><thead><tr><th>dag</th><th>dromen</th>' +
              "<th>panelen</th><th>gesprekken</th><th>avatartijd</th></tr></thead><tbody>";
      u.by_day.forEach(function (d) {
        html += "<tr><td>" + d.date + "</td><td>" + d.dreams + "</td><td>" + d.panels +
                "</td><td>" + d.sessions + "</td><td>" + Math.round(d.avatar_seconds) + " s</td></tr>";
      });
      html += "</tbody></table>";
    }

    html += '<p class="meter-noot">Tekst ' + euro(u.costs.tekst) + ", panelen " +
            euro(u.costs.panelen) + ", video " + euro(u.costs.video || 0);
    html += ", avatar " + euro(u.costs.avatar) + ". Runway rekent 2 credits bij het " +
            "starten en 2 per aangebroken zes seconden, dus " + euro(u.avatar_per_minute) +
            " per gesprekminuut — en ook wie meteen ophangt kost al iets.</p>";
    m.innerHTML = html;
  }

  /* De kostenmeter is voor jou, niet voor de bezoeker.
   *
   * Daar staat de kostprijs in - wat een droom ons kost aan tekst, beeld en
   * stem. Dat is precies wat een klant niet hoort te zien. Weggooien is zonde,
   * want zonder die cijfers weet je niet of je prijs klopt; dus achter dezelfde
   * beheersleutel als de pakketknoppen.
   */
  function toonMeter() {
    var sectie = el("meter-section");
    if (sectie) { sectie.hidden = !beheerAan; }
  }

  /* Pakket en saldo met de hand, in het beheerpaneel.
   *
   * Zonder dit is "zet mij op vijfhonderd tokens" een shell op de server, en op
   * Render is er geen shell. De knoppen staan in de sectie die alleen met de
   * beheersleutel zichtbaar is, dus een bezoeker ziet ze nooit.
   */
  function knoopBeheerrij() {
    document.querySelectorAll("#beheerrij [data-plan]").forEach(function (b) {
      b.addEventListener("click", function () {
        zetAccount({ plan: b.dataset.plan });
      });
    });
    var zet = el("beheer-zet");
    var veld = el("beheer-saldo");
    if (!zet || !veld) { return; }
    zet.addEventListener("click", function () {
      var n = parseInt(veld.value, 10);
      if (isNaN(n) || n < 0) { veld.focus(); return; }
      zet.disabled = true;
      zet.textContent = t("Bezig…");
      zetAccount({ saldo: n });
      setTimeout(function () {
        zet.disabled = false;
        zet.textContent = t("Zet saldo");
      }, 900);
    });
    veld.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); zet.click(); }
    });

    /* Beheer weer uit.
     *
     * Aanzetten kon, uitzetten niet - de sleutel bleef voorgoed in deze browser
     * staan en daarmee de kostenmeter, de webhooklog en de pakketknoppen. Dat
     * is precies wat je niet in beeld wilt als je de app als dromer gebruikt,
     * of als je hem aan iemand laat zien.
     */
    var uit = el("beheer-uit");
    if (uit) {
      uit.addEventListener("click", function () {
        // Alleen de stand uit. De sleutel blijft, anders moet je hem de volgende
        // keer weer opzoeken bij Render - en daar was hij nu net voor bewaard.
        beheerAan = false;
        toonMeter();
        laadWebhooklog();
        laadAccount();
        var doos = el("webhooklog");
        if (doos) { doos.hidden = true; }
      });
    }
  }
  knoopBeheerrij();

  /* Wat Stripe heeft aangeboden, en wat wij ermee deden.
   *
   * Zonder dit kijkglas is een webhook die niet aankomt onzichtbaar: de klant
   * heeft betaald, Stripe zegt dat hij het heeft afgeleverd, en wij weten van
   * niets. Dat kostte een middag zoeken.
   */
  function laadWebhooklog() {
    var doos = el("webhooklog");
    if (!doos) { return; }
    if (!beheerAan) { doos.hidden = true; return; }
    fetch("/api/webhooklog", { headers: { "X-Admin-Token": beheerSleutel() } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var log = d.log || [];
        doos.hidden = false;
        if (!log.length) {
          doos.innerHTML = '<p class="webhooklog-leeg">' +
            t("Stripe heeft nog niets aangeboden.") + "</p>";
          return;
        }
        var html = '<p class="webhooklog-kop">' + t("Wat Stripe aanbood") + "</p>";
        log.forEach(function (r) {
          var mis = /geweigerd|MISLUKT|geen gebruiker/.test(r.soort + r.uitkomst);
          html += '<div class="webhooklog-rij' + (mis ? " mis" : "") + '">' +
                  '<span class="wl-tijd">' + (r.wanneer || "").slice(0, 19).replace("T", " ") +
                  "</span>" +
                  '<span class="wl-soort">' + r.soort + "</span>" +
                  '<span class="wl-uit">' + r.uitkomst + "</span></div>";
        });
        doos.innerHTML = html;
      })
      .catch(function () { doos.hidden = true; });
  }

  function laadVerbruik() {
    toonMeter();
    laadWebhooklog();
    if (!beheerAan) { return; }
    fetch("/api/usage").then(function (r) { return r.json(); })
      .then(toonVerbruik).catch(function () {});
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

  el("intro-start").addEventListener("click", function () {
    bewaarProfiel().then(function () {
      el("intro").hidden = true;
      try { el("intro-video").pause(); } catch (e) { /* al gestopt */ }
      el("dream").focus();
    });
  });
  el("intro-later").addEventListener("click", function () {
    el("intro").hidden = true;
    try { el("intro-video").pause(); } catch (e) { /* al gestopt */ }
  });

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
      el("intro").hidden = false;
    }).catch(function () { el("intro").hidden = false; });
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
        naam: el("p-naam").value.trim()
      })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
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
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
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
  function toonKoopknoppen(aan) {
    betalenAan = !!aan;
    document.querySelectorAll(".koop-pakket").forEach(function (b) { b.hidden = !aan; });
    var doos = el("tokenpakketten");
    if (doos) { doos.hidden = !aan; }
    // De opwaardeerknoppen zitten in kaarten die al getekend kunnen zijn
    // voordat /api/health antwoord gaf.
    laadAccount();
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
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
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
    toonIntro();
    loadArchive();
    laadVerbruik();
    laadAccount();
  }

  /* --------------------------------------------------------------- starten */

  setupMic();

  // Wie is er? Bestaat er geen sessie, dan de poort en niets anders.
  fetch("/api/profile")
    .then(function (r) {
      if (r.status === 401) {
        el("poort").hidden = false;
        zetPoortModus("inloggen");
        el("p-email").focus();
        return null;
      }
      return r.json();
    })
    .then(function (p) { if (p) { binnen(p); } })
    .catch(function () {
      el("poort").hidden = false;
      zetPoortModus("inloggen");
    });
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
