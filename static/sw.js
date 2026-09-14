/* De service worker: het minimum dat een PWA nodig heeft, en niets meer.
 *
 * Een service worker die te veel wil, serveert op een dag een oude versie van
 * de app terwijl jij net gepusht hebt - en dan zoek je een fout die er niet is.
 * Daarom is alles hier network-first: het net wint altijd, de cache is er
 * alleen voor als er geen net is.
 *
 * Wat hij nooit aanraakt:
 *   /api/      antwoorden per gebruiker, en dromen die net geschreven zijn
 *   /panels/   beeld van een specifieke dromer, met zijn nummer in de naam
 *   navigaties  het opvragen van een pagina - zie hieronder
 * Die gaan onaangeroerd naar het net. Een gecachet antwoord van iemand anders
 * is het ergste wat een cache in deze app kan doen.
 *
 * ---------------------------------------------------------------------------
 * 14 september 2026: HIJ RAAKT PAGINA'S NIET MEER AAN, EN DAT IS DE BELANGRIJKSTE
 * REGEL IN DIT BESTAND.
 *
 * Ruud klikte op de link in de Instagram-bio en kreeg een zwarte pagina met
 * "Je bent offline" - terwijl hij online was en de server draaide. Dat kwam
 * hiervandaan: `fetch()` verwerpt bij elke hapering, en de browser in de
 * Instagram-app hapert. Eén blip op een navigatie en er stond een doodlopende
 * pagina zonder knop om het opnieuw te proberen.
 *
 * Dat is de verklaring voor nul aanmeldingen bij honderden bezoeken. Al het
 * verkeer komt uit die browser, en een deel daarvan kreeg dus nooit de site te
 * zien maar een bericht dat zij iets fout deden.
 *
 * De afweging is niet dicht: **offline is voor deze app waardeloos.** Er is geen
 * enkel scherm dat iets doet zonder net - duiden, panelen, Vera, inloggen, alles
 * gaat over de lijn. De winst van een gecachete pagina was dus nul, en de prijs
 * was een zwarte pagina bij de eerste hapering. Een navigatie gaat nu
 * rechtstreeks naar het net, en hapert die, dan krijgt de bezoeker het
 * foutscherm van zijn eigen browser - mét een knop om het opnieuw te proberen,
 * wat de onze niet had.
 *
 * Wat blijft is het caching van stylesheet, script en iconen. Dat versnelt een
 * tweede bezoek en kan niemand buitensluiten.
 * ---------------------------------------------------------------------------
 */

// Nieuwe naam, want de oude cache bevat pagina's die er niet meer in horen. Een
// oude cache wordt bij `activate` weggegooid, dus dit ruimt zichzelf op.
var CACHE = "dreamverse-v2";

// De schil: wat nodig is om iets te laten zien zonder net. Geen HTML met
// gegevens erin - alleen de onderdelen die voor iedereen hetzelfde zijn.
var SCHIL = [
  "/style.css",
  "/taal.js",
  "/icoon-192.png",
  "/apple-touch-icon.png"
];

self.addEventListener("install", function (e) {
  // Meteen de nieuwe versie worden; niet wachten tot alle tabbladen dicht zijn.
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      // Faalt er een, dan gaat de installatie gewoon door: de schil is een
      // extraatje en mag de app niet tegenhouden.
      return Promise.all(SCHIL.map(function (u) {
        return c.add(u).catch(function () { return null; });
      }));
    })
  );
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (namen) {
      return Promise.all(namen.map(function (n) {
        return n === CACHE ? null : caches.delete(n);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") { return; }

  // Een paginaverzoek gaat buiten ons om. Zie de uitleg bovenaan: dit is de
  // regel die voorkomt dat iemand uit de Instagram-browser een zwarte pagina
  // krijgt in plaats van de site.
  if (req.mode === "navigate") { return; }

  var url = new URL(req.url);
  if (url.origin !== self.location.origin) { return; }
  if (url.pathname.indexOf("/api/") === 0) { return; }
  if (url.pathname.indexOf("/panels/") === 0) { return; }

  e.respondWith(
    fetch(req).then(function (res) {
      // Alleen bewaren wat gelukt is en niet persoonlijk is.
      if (res && res.ok && res.type === "basic") {
        var kopie = res.clone();
        caches.open(CACHE).then(function (c) { c.put(req, kopie); });
      }
      return res;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        if (hit) { return hit; }
        // Geen net en niets in de cache. Hier komt alleen nog een stylesheet,
        // een script of een icoon langs - nooit een pagina - dus een kale 504
        // is genoeg. De offline-pagina die hier stond is weg: die kon alleen
        // nog verschijnen waar hij niet hoorde.
        return new Response("", { status: 504, statusText: "offline" });
      });
    })
  );
});
