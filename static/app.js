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

  // Wat er op dit moment gemaakt wordt, met een zandloper erbij. Zonder dit
  // gebeurt er minutenlang iets duurs zonder dat er iets te zien is.
  function toonVoortgang(state) {
    var balk = el("voortgang");
    if (!balk) { return; }
    var regels = [];
    var totaal = (episode && episode.panels) ? episode.panels.length : 5;

    var klaar = Object.keys(state.images || {}).length;
    if (state.status === "busy") {
      regels.push(t("Panelen tekenen —") + " " + klaar + " " + t("van de") + " " + totaal);
    }
    if (state.stem_status === "busy") {
      regels.push(t("Inspreken —") + " " + Object.keys(state.stem || {}).length + " " + t("van de") + " " + totaal);
    }
    if (state.video_status === "busy") {
      regels.push(t("Kernmoment animeren — dit duurt ongeveer een minuut"));
    }
    if (state.film_status === "busy") {
      var f = Object.keys(state.film || {}).length;
      regels.push(t("Film maken —") + " " + f + " " + t("van de") + " " + totaal + " " + t("panelen klaar"));
    }

    if (!regels.length) {
      balk.hidden = true;
      balk.innerHTML = "";
      return;
    }
    balk.hidden = false;
    balk.innerHTML = '<span class="zandloper" aria-hidden="true">⧗</span><span>' +
                     regels.join(" · ") + "</span>";
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

  function render(ep) {
    episode = ep;
    panelImages = {};
    kernVideo = null;
    stemmen = {};
    filmpjes = {};
    try { speler.pause(); } catch (e) { /* niets aan de hand */ }
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    if (ep.images_pending) { pollPanels(ep.number, 90); }
    el("title").textContent = ep.title;
    // De kop draagt nu de titel van de droom, niet meer de slogan: dat is de
    // nieuwe brontekst, anders zet een taalwissel de slogan terug.
    el("title").dataset.nl = ep.title;
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

  function toonSpectrum(sp) {
    spectrumData = sp;
    var sectie = el("spectrum-section");
    var dromen = sp.dreams || [];
    // Onder de drie dromen is er niets te zien, alleen ruis.
    if (dromen.length < 3) { sectie.hidden = true; return; }
    sectie.hidden = false;

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
    statusEl.innerHTML = '<span class="zandloper" aria-hidden="true">⧗</span> ' +
                         "De duiding wordt opnieuw geschreven bij je panelen…";
    fetch("/api/episode/" + nummer + "/herstel", { method: "POST" })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
      .then(function (res) {
        if (!res.ok) { throw new Error(res.body.error || t("Herstellen lukte niet.")); }
        render(res.body.episode);
        pollPanels(nummer, 3);
        statusEl.className = "status";
        statusEl.textContent = t("Droom %s is weer compleet.").replace("%s", nummer);
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
      o.textContent = "Droom " + d.n + " — " + (d.title || d.text || "").slice(0, 40);
      kies.appendChild(o);
    });
    if (!dreams.length) {
      var leeg = document.createElement("option");
      leeg.textContent = t("nog geen dromen");
      leeg.value = "";
      kies.appendChild(leeg);
    }
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
      recogniser.lang = "nl-NL";
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
        el("voortgang").hidden = false;
        el("voortgang").innerHTML = '<span class="zandloper" aria-hidden="true">⧗</span>' +
                                    "<span>Aanvraag gestart…</span>";
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
    if (!window.confirm(t("Het hele archief wissen? Je volgende droom wordt Droom 1."))) { return; }
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

    fetch("/api/episode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dream: text, quality: gekozenKwaliteit })
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
      })
      .then(function () {
        go.disabled = false;
        go.textContent = t("Verbeeld mijn droom");
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
  }

  // Afbreken met een melding die blíjft staan. De oude versie liet hem na twee
  // seconden verdwijnen, waardoor een mislukking eruitzag als "hij doet niets".
  function staken(bericht) {
    console.warn("vera:", bericht);
    hangup();
    statusEl.className = "status err";
    statusEl.textContent = bericht;
    guideLine.textContent = t("Ik kon je niet horen.");
  }

  async function callVera() {
    var btn = el("call");
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
      if (!r.ok) { throw new Error(creds.error || "Verbinden mislukte."); }
    } catch (e) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      return staken(e.message);
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
      // Wat je krijgt zegt meer dan wat het kost, zolang het in je pakket zit.
      var regel = k.inbegrepen ? k.bevat : k.tokens + " tokens";
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

  function toonAccount(a) {
    toonKwaliteiten(a);
    var op = a.dromen_over === 0 ? " op" : "";
    var minuten = Math.floor(a.avatar_seconden_over / 60);
    var html = "";
    html += "<div class='" + op + "'><b>" + a.dromen_over + "</b><span>" + t("dromen over") + "</span></div>";
    html += "<div><b>" + a.tokens + "</b><span>" + t("tokens") + "</span></div>";
    html += "<div><b>" + (minuten + Math.floor(a.tokens / a.tokens_per_minuut)) +
            "</b><span>" + t("minuten vera") + "</span></div>";
    html += "<div><b>" + a.plan_naam + "</b><span>" + t("pakket") + "</span></div>";
    html += "<div class='schakel'>";
    ["gratis", "plus", "ultra"].forEach(function (p) {
      html += "<button type='button' data-plan='" + p + "' aria-pressed='" +
              (a.plan === p ? "true" : "false") + "'>" + t(p) + "</button>";
    });
    html += "<button type='button' data-tokens='10'>" + t("+10 tokens") + "</button></div>";
    el("account").innerHTML = html;

    el("account").querySelectorAll("[data-plan]").forEach(function (b) {
      b.addEventListener("click", function () { zetAccount({ plan: b.dataset.plan }); });
    });
    el("account").querySelectorAll("[data-tokens]").forEach(function (b) {
      b.addEventListener("click", function () { zetAccount({ tokens: 10 }); });
    });
  }

  function zetAccount(body) {
    fetch("/api/account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); }).then(toonAccount).catch(function () {});
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

  function laadVerbruik() {
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

  function begroetingSpelen(geforceerd) {
    if (!introVideo) { return; }
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
    var poging = introVideo.play();
    if (!poging || !poging.then) { return; }
    poging.then(function () {
      introVideo.dataset.gehoord = "ja";
      zetKnop("dempen");
    }).catch(function () {
      // De browser wil nog geen geluid. Dan liever de stille staart dan een
      // pratende Vera die je niet hoort.
      stilZetten();
    });
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
      el("intro").hidden = false;
    }).catch(function () { el("intro").hidden = false; });
  }

  /* --------------------------------------------------------------- starten */

  setupMic();
  toonIntro();
  loadArchive();
  laadVerbruik();
  laadAccount();
  fetch("/api/health")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      // De brontekst meegeven, anders weet de vertaalslag straks niet meer
      // welke van de twee toestanden hier stond.
      el("mode").dataset.nl = d.key ? "verbonden" : "voorbeeldmodus";
      el("mode").textContent = t(el("mode").dataset.nl);
      if (!d.vera) {
        el("call").disabled = true;
        el("call").title = t("Vera is niet aangesloten");
      }
    })
    .catch(function () { el("mode").dataset.nl = "offline"; el("mode").textContent = "offline"; });
})();
