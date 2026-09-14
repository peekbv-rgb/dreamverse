/* Deze service worker doet nog één ding: zichzelf opruimen.
 *
 * 14 september 2026. Ruud klikte op de link in de Instagram-bio en kreeg een
 * zwarte pagina met "Je bent offline" - terwijl hij online was en de server
 * draaide. De oorzaak stond in de vorige versie van dit bestand: elke navigatie
 * ging door een network-first fetch met een offline-pagina in de catch, en
 * `fetch()` verwerpt bij elke hapering. De browser in de Instagram-app hapert.
 * Eén blip en er stond een doodlopend scherm dat de bezoeker vertelde dat het
 * aan hem lag.
 *
 * Daarna heb ik navigaties met rust gelaten in plaats van de worker weg te
 * halen. Dat was niet genoeg, en dat is de les: **een service worker die al
 * geïnstalleerd staat, bedient het eerstvolgende bezoek nog.** De browser haalt
 * de nieuwe versie pas op nádat hij de pagina al uit de oude heeft geserveerd.
 * Wie vastzat kreeg de zwarte pagina dus nog één keer - en bij verkeer dat in
 * één tik binnenkomt en in één tik weg is, is één keer alles.
 *
 * Dus gaat hij eruit. De afweging is niet dicht:
 *
 *   - **Offline is voor deze app waardeloos.** Duiden, panelen, Vera, inloggen:
 *     alles gaat over de lijn. Er is geen scherm dat iets doet zonder net.
 *   - **Wat hij opleverde was een iets snellere tweede pagina.** Wat hij kostte
 *     was een onbekend aantal bezoekers die de site nooit gezien hebben.
 *   - **Op het beginscherm zetten blijft werken.** Op een iPhone gaat dat via
 *     Deel -> Zet op beginscherm, en daar is geen service worker voor nodig -
 *     `manifest.json` en het apple-touch-icon doen dat werk. Wat vervalt is de
 *     installatieballon van Chrome op Android; die eist een worker met een
 *     fetch-handler. Dat is de prijs, en die is klein.
 *
 * Wat hier staat is een zelfontmanteling. Hij wist zijn caches, meldt zichzelf
 * af, en herlaadt de openstaande tabbladen zodat de bezoeker meteen de echte
 * site ziet in plaats van te moeten verversen. Daarna is er geen worker meer en
 * haalt `app.js` hem ook niet opnieuw op.
 *
 * **Laat dit bestand staan.** Weghalen zou een 404 geven, en dan blijft de oude
 * worker bij iedereen die hem heeft gewoon draaien - precies het probleem dat we
 * hier oplossen. Hij mag weg als er maanden overheen zijn.
 */

self.addEventListener("install", function () {
  // Niet wachten tot alle tabbladen dicht zijn: dit moet nu gebeuren.
  self.skipWaiting();
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (namen) {
        return Promise.all(namen.map(function (n) { return caches.delete(n); }));
      })
      .then(function () { return self.registration.unregister(); })
      .then(function () { return self.clients.matchAll({ type: "window" }); })
      .then(function (vensters) {
        // Herladen, want dit venster kan zojuist de offline-pagina hebben
        // gekregen. Zonder dit blijft die staan tot iemand zelf ververst, en
        // dat doet niemand die denkt dat de site stuk is.
        vensters.forEach(function (v) { v.navigate(v.url); });
      })
      .catch(function () { /* opruimen mag nooit een pagina kosten */ })
  );
});

// Geen fetch-handler. Dat is het hele punt: er komt geen verzoek meer langs dat
// hier fout kan gaan.
