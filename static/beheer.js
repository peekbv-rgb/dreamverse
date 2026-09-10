/* Het beheerpaneel, op zijn eigen pagina.
 *
 * Dit stond allemaal in app.js: de sleutel, de knoppen, het rapport, de
 * kostenmeter en de webhooklog. Daarmee downloadde elke ingelogde dromer de
 * hele beheerlaag. Wijzigen kon hij niet - de server eist de sleutel - maar
 * lezen wel: hoe het beheer werkt, welke eindpunten er zijn, en wat een droom
 * ons kost.
 *
 * Wat hier anders is dan daar:
 *
 * - De sleutel wordt niet bewaard. Hij ging naar localStorage, op dezelfde
 *   origin als de app, en dan is één cross-site scripting in de dromerkant
 *   genoeg om hem te lezen. Nu gaat hij één keer naar /api/beheer/inloggen en
 *   komt terug als een HttpOnly cookie: JavaScript kan er niet bij, ook dit
 *   script niet. Daarom staat er hieronder ook nergens een Authorization- of
 *   X-Admin-Token-header - de browser stuurt het cookie vanzelf mee.
 * - Er is geen dromersessie voor nodig. Beheren doe je als beheerder.
 * - De opmaak van het paneel komt van de server en alleen als de sleutel klopt.
 *
 * Geen taal.js hier: dit is een pagina voor één persoon en die spreekt
 * Nederlands. Een tweede taal onderhouden voor een scherm dat niemand anders
 * ziet, is werk zonder lezer.
 */
(function () {
  "use strict";

  var el = function (id) { return document.getElementById(id); };

  function lees(r) {
    return r.json().then(function (body) { return { ok: r.ok, body: body }; },
                         function () { return { ok: r.ok, body: {} }; });
  }

  function euro(n) { return "€" + n.toFixed(2).replace(".", ","); }

  function cel(waarde, label, klasse) {
    return '<div class="meter-cel ' + (klasse || "") + '"><b>' + waarde +
           "</b><span>" + label + "</span></div>";
  }

  /* --------------------------------------------------------------- de poort */

  function toonPoort(melding) {
    el("poort-sectie").hidden = false;
    el("paneel").hidden = true;
    el("afmelden-sectie").hidden = true;
    if (melding) {
      el("sleutel-fout").textContent = melding;
      el("sleutel-fout").hidden = false;
    }
    setTimeout(function () { el("sleutel").focus(); }, 60);
  }

  function binnen() {
    el("poort-sectie").hidden = true;
    el("sleutel").value = "";
    el("sleutel-fout").hidden = true;
    paneelLaden();
  }

  el("sleutel-oog").addEventListener("click", function () {
    var veld = el("sleutel");
    veld.type = veld.type === "password" ? "text" : "password";
    this.textContent = veld.type === "password" ? "laat zien" : "verberg";
  });

  el("sleutel-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var sleutel = el("sleutel").value.trim();
    var fout = el("sleutel-fout");
    var knop = el("sleutel-door");
    if (!sleutel) { el("sleutel").focus(); return; }
    fout.hidden = true;
    knop.disabled = true;
    knop.textContent = "Bezig…";
    fetch("/api/beheer/inloggen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sleutel: sleutel })
    })
      .then(lees)
      .then(function (res) {
        if (!res.ok) {
          fout.textContent = res.body.error || "Die sleutel wordt niet geaccepteerd.";
          fout.hidden = false;
          return;
        }
        binnen();
      })
      .catch(function () {
        fout.textContent = "De server antwoordde niet. Probeer het nog eens.";
        fout.hidden = false;
      })
      .then(function () {
        knop.disabled = false;
        knop.textContent = "Aanmelden";
      });
  });

  el("afmelden").addEventListener("click", function () {
    fetch("/api/beheer/uitloggen", { method: "POST" })
      .then(function () { location.reload(); })
      .catch(function () { location.reload(); });
  });

  /* -------------------------------------------------------------- het paneel */

  function paneelLaden() {
    fetch("/api/beheer/paneel")
      .then(function (r) {
        if (!r.ok) { throw new Error("geen toegang"); }
        return r.text();
      })
      .then(function (html) {
        var doos = el("paneel");
        doos.innerHTML = html;
        doos.hidden = false;
        el("afmelden-sectie").hidden = false;
        knopenAanzetten();
        laadRapport();
        laadWebhooklog();
        laadVerbruik();
      })
      .catch(function () {
        toonPoort("De sessie is verlopen. Vul de sleutel opnieuw in.");
      });
  }

  /* Pakket en saldo zetten.
   *
   * "Voor wie" is verplicht. Vroeger was leeg-laten "mijzelf", want dit liep via
   * de ingelogde dromer; op een eigen beheerpagina is er geen mijzelf, en raden
   * bij een handeling die gratis Ultra uitdeelt is precies wat je niet wilt.
   */
  function melding(tekst, mis) {
    var doos = el("beheerrij-melding");
    if (!doos) { return; }
    doos.hidden = false;
    doos.className = "beheerrij-melding" + (mis ? " mis" : "");
    doos.textContent = tekst;
  }

  function zetAccount(body) {
    var wie = el("beheer-wie");
    if (!wie || !wie.value.trim()) {
      melding("Voor wie? Vul een e-mailadres in.", true);
      wie && wie.focus();
      return;
    }
    body.wie = wie.value.trim();
    fetch("/api/beheer/account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
      .then(lees)
      .then(function (res) {
        if (res.body && res.body.login === undefined && !res.ok) {
          melding(res.body.error || "Dat lukte niet.", true);
          return;
        }
        var a = res.body;
        melding("Gezet voor " + a.wie + ": " + a.plan_naam + ", " + a.tokens + " tokens.");
        // Het rapport toont pakketten per persoon, dus dat is nu verouderd.
        laadRapport();
      })
      .catch(function () { melding("De server antwoordde niet.", true); });
  }

  function knopenAanzetten() {
    document.querySelectorAll("#beheerrij [data-plan]").forEach(function (b) {
      b.addEventListener("click", function () { zetAccount({ plan: b.dataset.plan }); });
    });
    var zet = el("beheer-zet");
    var veld = el("beheer-saldo");
    if (!zet || !veld) { return; }
    zet.addEventListener("click", function () {
      var n = parseInt(veld.value, 10);
      if (isNaN(n) || n < 0) { veld.focus(); return; }
      zet.disabled = true;
      zet.textContent = "Bezig…";
      zetAccount({ saldo: n });
      setTimeout(function () { zet.disabled = false; zet.textContent = "Zet saldo"; }, 900);
    });
    veld.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); zet.click(); }
    });
  }

  /* Het cijfer waar dit project op staat of valt.
   *
   * Wie komt er op dag vier uit zichzelf terug. Alles hiervoor stond al in de
   * database; er was alleen geen scherm dat het liet zien. Geen derde partij,
   * geen cookies, geen banner - en dus ook geen klikgedrag, want dat zou
   * clientmeting vragen.
   */
  /* Alles wat uit de database komt gaat hier langs voordat het in innerHTML
   * belandt.
   *
   * Een e-mailadres is door de gebruiker getypt, en de controle in
   * `accounts.EMAIL` laat alles toe wat geen apenstaartje of witruimte is -
   * dus ook punthaken. Onbeschermd is dit paneel daarmee de gevaarlijkste
   * plek van de app om script binnen te krijgen: het cookie is wel HttpOnly,
   * maar script dat híer draait hoeft die sleutel niet te lezen om hem te
   * gebruiken. Het kan gewoon /api/beheer/account aanroepen en zichzelf Ultra
   * geven.
   */
  function esc(waarde) {
    return String(waarde === undefined || waarde === null ? "" : waarde)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function laadRapport() {
    var doos = el("rapport");
    if (!doos) { return; }
    fetch("/api/beheer/rapport")
      .then(lees)
      .then(function (res) {
        // Niet stil verbergen. Ging dit mis, dan zag je een lege pagina en geen
        // reden - en dan ga je zoeken naar cijfers die er niet zijn in plaats
        // van naar een verzoek dat niet lukte.
        if (!res.ok) {
          doos.hidden = false;
          doos.innerHTML = '<p class="beheerrij-melding mis">Het rapport kon niet '
            + "geladen worden: " + esc((res.body && res.body.error) || res.status)
            + ".</p>";
          return;
        }
        var c = res.body;
        doos.hidden = false;
        var deel = c.oud_genoeg
          ? Math.round(100 * c.terug_dag4 / c.oud_genoeg) + "%"
          : "—";
        var html = '<div class="rapport-groot"><b>' + c.terug_dag4 + " / " + c.oud_genoeg +
                "</b><span>terug op dag vier of later (" + deel + ")</span></div>";
        html += '<div class="rapport-rij">';
        [[c.gebruikers, "mensen"], [c.met_droom, "met een droom"],
         [c.dromen, "dromen"], [c.meerdaags, "meer dan een dag actief"],
         [c.vragen, "vragen gesteld"], [c.omzet.toFixed(2), "euro omzet"]
        ].forEach(function (r) {
          html += "<div><b>" + r[0] + "</b><span>" + r[1] + "</span></div>";
        });
        html += "</div>";

        /* De trechter, en dit is het stuk dat hier niet stond.
         *
         * "Mensen" hierboven is een totaal, en de tabel eronder gaat over wie
         * er al is. Wat er niet stond is wanneer er iemand bijkwam, en of er
         * überhaupt iemand langs de deur liep - en dat is precies wat je wil
         * weten als je je afvraagt of er aanmeldingen zijn. Het stond wél in
         * het antwoord van de server; alleen tekende deze pagina het niet, dus
         * was het alleen te zien met `python rapport.py` op de eigen machine.
         */
        if ((c.trechter || []).length) {
          html += '<p class="lbl">Per dag: bezoek, account, droom</p>';
          html += '<table class="rapport-tabel"><thead><tr>' +
            ["datum", "landing", "gids", "app", "nieuw", "dromen"]
              .map(function (k) { return "<th>" + k + "</th>"; }).join("") +
            "</tr></thead><tbody>";
          var tot = { landing: 0, gids: 0, app: 0, nieuw: 0, dromen: 0 };
          // Alleen dagen waarop er ook echt geteld is. Het tellen begon later
          // dan de eerste accounts, en anders deel je twee getallen op elkaar
          // die over verschillende weken gaan.
          var gemeten = { landing: 0, nieuw: 0 };
          c.trechter.slice(0, 14).forEach(function (r) {
            html += "<tr><td>" + esc(r.datum) + "</td>";
            Object.keys(tot).forEach(function (k) {
              html += "<td>" + (r[k] || 0) + "</td>";
              tot[k] += r[k] || 0;
            });
            html += "</tr>";
            if (r.landing || r.app) {
              gemeten.landing += r.landing || 0;
              gemeten.nieuw += r.nieuw || 0;
            }
          });
          html += "<tr><td><b>samen</b></td>";
          Object.keys(tot).forEach(function (k) {
            html += "<td><b>" + tot[k] + "</b></td>";
          });
          html += "</tr></tbody></table>";
          if (gemeten.landing >= 10) {
            html += '<p class="meter-noot">Van ' + gemeten.landing +
              " bezoeken aan de landingspagina werden er " + gemeten.nieuw +
              " een account: " +
              Math.round(100 * gemeten.nieuw / gemeten.landing) + "%.</p>";
          } else if (gemeten.landing) {
            html += '<p class="meter-noot">Nog te weinig bezoek (' +
              gemeten.landing + ") om er een percentage van te maken.</p>";
          }
        }

        /* Waar ze vandaan kwamen. `ig-app` is de eigen browser van Instagram en
         * werkt ook zonder tag in de link; de rest komt van ?van=... erachter. */
        html += '<p class="lbl">Waar ze vandaan kwamen</p>';
        var bronnen = Object.keys(c.bronnen || {});
        if (bronnen.length) {
          html += '<table class="rapport-tabel"><tbody>';
          bronnen.forEach(function (naam) {
            html += "<tr><td>" + esc(naam) + "</td><td>" +
              (c.bronnen[naam] || 0) + "</td></tr>";
          });
          html += "</tbody></table>";
        } else {
          html += '<p class="meter-noot">Nog niets gemeten. Zet <b>?van=ig</b> ' +
            "achter het adres in de Instagram-bio; de eigen browser van " +
            "Instagram wordt ook zonder dat herkend.</p>";
        }

        if ((c.mensen || []).length) {
          html += '<p class="lbl">Wie er is</p>';
          html += '<table class="rapport-tabel"><thead><tr>' +
            ["", "pakket", "sinds", "dromen", "dagen", "vragen", "terug"]
              .map(function (k) { return "<th>" + k + "</th>"; }).join("") +
            "</tr></thead><tbody>";
          c.mensen.forEach(function (m) {
            html += "<tr><td>" + esc(m.email) + "</td><td>" + esc(m.pakket) +
              "</td><td>" + esc(m.sinds) + "</td><td>" + (m.dromen || 0) +
              "</td><td>" + (m.actieve_dagen || 0) + "</td><td>" +
              (m.vragen || 0) + "</td><td>" + (m.terug ? "ja" : "—") +
              "</td></tr>";
          });
          html += "</tbody></table>";
        } else {
          html += '<p class="meter-noot">Nog geen enkel account.</p>';
        }
        doos.innerHTML = html;
      })
      .catch(function () { doos.hidden = true; });
  }

  /* Wat Stripe heeft aangeboden, en wat wij ermee deden.
   *
   * Zonder dit kijkglas is een webhook die niet aankomt onzichtbaar: de klant
   * heeft betaald, Stripe zegt dat hij het heeft afgeleverd, en wij weten van
   * niets. Dat kostte een middag zoeken.
   */
  function laadWebhooklog() {
    var doos = el("webhooklog");
    if (!doos) { return; }
    fetch("/api/beheer/webhooklog")
      .then(lees)
      .then(function (res) {
        if (!res.ok) { doos.hidden = true; return; }
        var log = res.body.log || [];
        doos.hidden = false;
        if (!log.length) {
          doos.innerHTML = '<p class="webhooklog-leeg">Stripe heeft nog niets aangeboden.</p>';
          return;
        }
        var html = "";
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

  /* Wat het gekost heeft. Dit is de reden dat deze pagina niet in de app hoort:
   * hier staat de kostprijs per droom, en dat is precies wat een klant niet
   * hoort te zien. */
  function laadVerbruik() {
    fetch("/api/beheer/usage")
      .then(lees)
      .then(function (res) { if (res.ok) { toonVerbruik(res.body); } })
      .catch(function () { /* de meter is bijzaak */ });
  }

  function toonVerbruik(u) {
    var t = u.totals, m = el("meter");
    if (!m) { return; }
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

  /* ---------------------------------------------------------------- starten */

  // Eerst vragen of we er al in mogen. Zo verschijnt of het sleutelveld of het
  // paneel, en nooit allebei tegelijk.
  fetch("/api/beheer/status")
    .then(lees)
    .then(function (res) {
      if (res.body.uit) {
        toonPoort("ADMIN_TOKEN staat niet in de omgeving. Zet hem bij Render " +
                  "onder Environment; zonder die variabele kan beheren helemaal niet.");
        el("sleutel-door").disabled = true;
        return;
      }
      if (res.body.ok) { binnen(); } else { toonPoort(); }
    })
    .catch(function () { toonPoort("De server antwoordde niet."); });
})();
