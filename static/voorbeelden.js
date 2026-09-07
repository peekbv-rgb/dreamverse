/* Voorbeelden van een kernmoment: klikken om te spelen.
 *
 * De drie clips zijn samen ruim 8 MB en er is geen ffmpeg om ze te verkleinen.
 * Zou de pagina ze vooraf laden, dan kost hij op een telefoon een halve minuut
 * en een hap uit iemands bundel - voor iets wat de meeste bezoekers niet eens
 * aanklikken.
 *
 * Dus staat er een posterplaatje van een paar tientallen kB, en wordt de video
 * pas aangemaakt als iemand erop drukt. Wie kijkt, kiest daar zelf voor.
 *
 * Werkt op de landingspagina en in de app; die eerste heeft geen app.js, dus dit
 * staat los van allebei.
 */
(function () {
  "use strict";

  function speel(doos) {
    if (doos.dataset.speelt === "ja") { return; }
    doos.dataset.speelt = "ja";

    var v = document.createElement("video");
    v.src = doos.dataset.clip;
    v.poster = doos.dataset.poster || "";
    v.controls = true;
    v.autoplay = true;
    v.playsInline = true;
    v.setAttribute("playsinline", "");
    v.preload = "auto";

    var oud = doos.querySelector(".voorbeeld-plaat");
    if (oud) { oud.replaceWith(v); }
    else { doos.insertBefore(v, doos.firstChild); }

    var knop = doos.querySelector(".voorbeeld-play");
    if (knop) { knop.remove(); }

    // Mislukt het afspelen - een browser die geluid tegenhoudt bijvoorbeeld -
    // dan blijven de bedieningsknoppen staan en kan de bezoeker het zelf doen.
    var poging = v.play();
    if (poging && poging.catch) { poging.catch(function () { /* knoppen staan er */ }); }
  }

  document.querySelectorAll(".voorbeeld").forEach(function (doos) {
    doos.addEventListener("click", function () { speel(doos); });
    doos.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); speel(doos); }
    });
  });
})();
