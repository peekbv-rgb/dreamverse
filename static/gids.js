/* Zoeken in de Dream Guide.
 *
 * Alles staat al op de pagina, dus dit filtert alleen wat er is — geen verzoek
 * naar de server, geen wachten. Zolang de bibliotheek uit tientallen onderwerpen
 * bestaat is dat sneller dan wat dan ook; wordt het er ooit vijfhonderd, dan
 * hoort het zoeken naar de server te verhuizen.
 *
 * Deze pagina's staan los van de app: geen app.js en geen taal.js. Ze zijn
 * Engels, want de zoekvraag is Engels.
 */
(function () {
  "use strict";

  // De knop naar de app, geteld. **Dit staat boven de zoekcode met opzet.**
  //
  // Hieronder springt dit bestand er met een `return` uit zodra er geen
  // zoekveld is - en dat veld staat alleen op de overzichtspagina. De knop
  // naar de app staat juist op elk artikel. Onderaan zou deze teller dus
  // precies nergens werken waar hij nodig is.
  //
  // Waarom hij er is: de gids is het enige onderdeel dat uit zichzelf bezoek
  // trekt - 22 van de 43 onderwerpen hadden bezoek, verspreid zoals verkeer
  // uit een zoekmachine zich verspreidt. Of zo iemand dan ook doorklikt was
  // niet te zien, en dat is precies de stap waar het om gaat.
  //
  // `sendBeacon` en geen `fetch`: deze knop navigeert meteen weg, en een
  // lopende fetch wordt door die navigatie afgebroken. Een beacon wordt juist
  // wél afgeleverd nadat de pagina weg is.
  //
  // Eén vaste naam en niet de slug erbij: `weergaven` heeft (datum, pagina)
  // als sleutel, dus een vrij veld laat iemand die tabel volschrijven. Welk
  // onderwerp het was staat toch al in de gidsteller van diezelfde dag.
  [].slice.call(document.querySelectorAll('.gids-cta a[href="/app"]'))
    .forEach(function (a) {
      a.addEventListener("click", function () {
        try {
          navigator.sendBeacon("/api/tel",
            new Blob([JSON.stringify({ wat: "gids:naar-app" })],
                     { type: "application/json" }));
        } catch (e) { /* een teller mag nooit een klik kosten */ }
      });
    });

  var veld = document.getElementById("gids-zoek");
  var doos = document.getElementById("gids-kaarten");
  var leeg = document.getElementById("gids-leeg");
  if (!veld || !doos) { return; }

  var kaarten = [].slice.call(doos.querySelectorAll(".gids-kaart"));

  function filter() {
    var woord = veld.value.trim().toLowerCase();
    var raak = 0;
    kaarten.forEach(function (k) {
      var past = !woord || (k.dataset.zoek || "").indexOf(woord) !== -1;
      k.hidden = !past;
      if (past) { raak++; }
    });
    // Een categoriekop zonder zichtbare kaarten eronder is een kop boven niets.
    doos.querySelectorAll(".gids-kaarten").forEach(function (r) {
      var iets = [].slice.call(r.querySelectorAll(".gids-kaart"))
                   .some(function (k) { return !k.hidden; });
      r.hidden = !iets;
      var kop = r.previousElementSibling;
      if (kop && kop.classList.contains("gids-groep")) { kop.hidden = !iets; }
    });
    if (leeg) { leeg.hidden = raak !== 0; }
  }

  veld.addEventListener("input", filter);
  // Een lege Escape leegt het veld; dat verwacht iedereen van een zoekvak.
  veld.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { veld.value = ""; filter(); }
  });
})();
