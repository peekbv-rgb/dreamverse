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
