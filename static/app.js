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

  function speak(text) {
    if (!voiceOn || !("speechSynthesis" in window)) { return; }
    try {
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text);
      u.lang = "nl-NL"; u.rate = 0.86; u.pitch = 0.95;
      window.speechSynthesis.speak(u);
    } catch (e) { /* stil terugvallen op alleen tekst */ }
  }

  /* --------------------------------------------------------------- speler */

  function show(n) {
    var total = episode.panels.length;
    index = Math.max(0, Math.min(total - 1, n));
    var panel = episode.panels[index];
    stage.innerHTML = scene(panel);
    // Het kernmoment: op dit ene paneel staat geen plaatje maar echte video.
    if (kernVideo && kernVideo.panel === index && kernVideo.src) {
      var v = document.createElement("video");
      v.className = "kernmoment";
      v.src = kernVideo.src;
      v.playsInline = true;
      v.loop = true;
      v.controls = false;
      stage.appendChild(v);
      // Met geluid proberen; blokkeert de browser dat, dan gedempt verder.
      v.play().catch(function () { v.muted = true; v.play().catch(function () {}); });
      var merk = document.createElement("span");
      merk.className = "kern-merk";
      merk.textContent = "kernmoment";
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
      wacht.textContent = "kernmoment wordt gemaakt…";
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
        if (state.video_panel !== undefined) {
          var was = kernVideo && kernVideo.src;
          kernVideo = { panel: state.video_panel, src: state.video || null,
                        status: state.video_status || "busy" };
          if (kernVideo.src && !was) { fresh = true; }
        }
        // Staat het net binnengekomen paneel in beeld, dan meteen tonen.
        if (fresh && panelImages[index] && !stage.querySelector(".painted")) { show(index); }
        if (state.status !== "done" || (kernVideo && kernVideo.status === "busy")) {
          pollTimer = setTimeout(function () { pollPanels(number, tries - 1); }, 4000);
        }
      })
      .catch(function () { /* beeld is bijzaak; de aflevering staat er al */ });
  }

  function render(ep) {
    episode = ep;
    panelImages = {};
    kernVideo = null;
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    if (ep.images_pending) { pollPanels(ep.number, 90); }
    el("title").textContent = ep.title;
    player.hidden = false;

    bar.innerHTML = "";
    ep.panels.forEach(function () { bar.appendChild(document.createElement("span")); });
    show(0);

    threadsEl.innerHTML = "";
    el("threads-section").hidden = false;
    if (ep.threads && ep.threads.length) {
      el("threads-title").textContent = "Wat terugkwam";
      ep.threads.forEach(function (t) {
        var d = document.createElement("div");
        d.className = "thread";
        d.innerHTML = "";
        var tag = document.createElement("span"); tag.className = "tag"; tag.textContent = t.ref;
        var was = document.createElement("p"); was.textContent = "Toen: " + t.was;
        var now = document.createElement("p"); now.className = "then"; now.textContent = "Nu: " + t.now;
        d.appendChild(tag); d.appendChild(was); d.appendChild(now);
        threadsEl.appendChild(d);
      });
    } else {
      el("threads-title").textContent = "Nog geen draden";
      var d2 = document.createElement("div");
      d2.className = "thread";
      d2.textContent = "Deze droom staat nog op zichzelf. Vanaf je tweede of derde droom vormt het web zich.";
      threadsEl.appendChild(d2);
    }

    el("reading-section").hidden = false;
    el("why").textContent = ep.why;
    el("meaning").textContent = ep.meaning;
    el("future").textContent = ep.future;
    el("question").textContent = ep.question;
  }

  /* -------------------------------------------------------------- archief */

  function renderArchive(dreams) {
    archiveEl.innerHTML = "";
    if (!dreams.length) {
      var empty = document.createElement("div");
      empty.className = "entry";
      empty.textContent = "Nog leeg. Je eerste droom wordt Droom 1.";
      archiveEl.appendChild(empty);
      return;
    }
    dreams.forEach(function (d) {
      var row = document.createElement("div");
      row.className = "entry";
      var no = document.createElement("span"); no.className = "no"; no.textContent = "Droom " + d.n;
      var txt = document.createElement("span"); txt.className = "txt"; txt.textContent = d.title || d.text;
      row.appendChild(no); row.appendChild(txt);
      archiveEl.appendChild(row);
    });
  }

  function loadArchive() {
    fetch("/api/archive")
      .then(function (r) { return r.json(); })
      .then(function (d) { renderArchive(d.dreams || []); })
      .catch(function () { /* archief is bijzaak; de app werkt zonder */ });
  }

  /* ------------------------------------------------------------- inspreken */

  var Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  var recogniser = null, listening = false;

  function setupMic() {
    var mic = el("mic");
    if (!Recognition) {
      mic.disabled = true;
      mic.title = "Inspreken werkt in Chrome en Edge";
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
        mic.textContent = "Stop met opnemen";
        guide.classList.add("listening");
        guideLine.textContent = "Ik luister. Neem de tijd.";
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
          ? "Geen toegang tot de microfoon. Sta dat toe in je browser."
          : "Het opnemen stopte onverwacht. Typ anders even.";
      };
      recogniser.onend = function () {
        listening = false;
        mic.classList.remove("rec");
        mic.textContent = "Inspreken";
        guide.classList.remove("listening");
        guideLine.textContent = input.value
          ? "Genoteerd. Zal ik er een aflevering van maken?"
          : "Ik heb niets opgevangen. Probeer het nog eens.";
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
    this.textContent = voiceOn ? "Stem uit" : "Stem aan";
    if (voiceOn && episode) { speak(episode.panels[index].narration); }
    else if ("speechSynthesis" in window) { window.speechSynthesis.cancel(); }
  });

  document.addEventListener("keydown", function (e) {
    if (e.target === input || !episode) { return; }
    if (e.key === "ArrowRight") { el("next").click(); }
    if (e.key === "ArrowLeft" && index > 0) { show(index - 1); }
  });

  el("clear").addEventListener("click", function () {
    if (!window.confirm("Het hele archief wissen? Je volgende droom wordt Droom 1.")) { return; }
    fetch("/api/archive", { method: "DELETE" })
      .then(function () {
        loadArchive();
        statusEl.className = "status";
        statusEl.textContent = "Archief gewist.";
      });
  });

  el("go").addEventListener("click", function () {
    var text = input.value.trim();
    if (!text) {
      statusEl.className = "status";
      statusEl.textContent = "Vertel eerst je droom.";
      input.focus();
      return;
    }
    if (listening && recogniser) { recogniser.stop(); }

    var go = this;
    go.disabled = true;
    go.textContent = "Bezig…";
    statusEl.className = "status";
    statusEl.textContent = "Je aflevering wordt geschreven. Dit duurt een halve tot anderhalve minuut.";
    guideLine.textContent = "Ik kijk ernaar. Blijf even bij me.";

    fetch("/api/episode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dream: text })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
      .then(function (res) {
        if (!res.ok) { throw new Error(res.body.error || "Het lukte niet."); }
        var ep = res.body.episode;
        render(ep);
        input.value = "";
        loadArchive();
        laadVerbruik();
        laadAccount();
        statusEl.textContent = ep.demo
          ? (ep.demo_reason || "Voorbeeldaflevering.")
          : "Klaar. Dit was Droom " + ep.number + "; hij telt mee in je volgende duiding.";
        guideLine.textContent = "Kijk maar. Ik heb er iets van gemaakt.";
        player.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function (e) {
        statusEl.className = "status err";
        statusEl.textContent = e.message;
        guideLine.textContent = "Er ging iets mis. Probeer het zo nog eens.";
      })
      .then(function () {
        go.disabled = false;
        go.textContent = "Maak mijn aflevering";
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
    if (left <= 0) { hangup("De vijf minuten zaten erop."); }
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
    el("call").textContent = "Praat met Vera";
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
    guideLine.textContent = "Ik kon je niet horen.";
  }

  async function callVera() {
    var btn = el("call");
    btn.disabled = true;
    btn.textContent = "Verbinden…";
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

    btn.textContent = "In gesprek";
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

  function bewaarNaam() {
    var naam = naamVeld.value.trim();
    fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: naam })
    }).then(function () {
      if (naam) { guideLine.textContent = "Dag " + naam + ". Vertel me wat je zag."; }
    }).catch(function () { /* naam is een extraatje, geen voorwaarde */ });
  }

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
        guideLine.textContent = "Goedemorgen " + p.name + ". Heb je lekker geslapen?";
      }
    })
    .catch(function () {});

  /* ------------------------------------------------------ pakket en saldo */

  function toonAccount(a) {
    var op = a.dromen_over === 0 ? " op" : "";
    var minuten = Math.floor(a.avatar_seconden_over / 60);
    var html = "";
    html += "<div class='" + op + "'><b>" + a.dromen_over + "</b><span>dromen over</span></div>";
    html += "<div><b>" + a.tokens + "</b><span>tokens</span></div>";
    html += "<div><b>" + (minuten + Math.floor(a.tokens / a.tokens_per_minuut)) +
            "</b><span>minuten vera</span></div>";
    html += "<div><b>" + a.plan_naam + "</b><span>pakket</span></div>";
    html += "<div class='schakel'>";
    ["gratis", "plus", "ultra"].forEach(function (p) {
      html += "<button type='button' data-plan='" + p + "' aria-pressed='" +
              (a.plan === p ? "true" : "false") + "'>" + p + "</button>";
    });
    html += "<button type='button' data-tokens='10'>+10 tokens</button></div>";
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

  /* --------------------------------------------------------------- starten */

  setupMic();
  loadArchive();
  laadVerbruik();
  laadAccount();
  fetch("/api/health")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      el("mode").textContent = d.key ? "verbonden" : "voorbeeldmodus";
      if (!d.vera) {
        el("call").disabled = true;
        el("call").title = "Vera is niet aangesloten";
      }
    })
    .catch(function () { el("mode").textContent = "offline"; });
})();
