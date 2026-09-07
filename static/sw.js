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
 * Die gaan onaangeroerd naar het net. Een gecachet antwoord van iemand anders
 * is het ergste wat een cache in deze app kan doen.
 */

var CACHE = "dreamverse-v1";

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
        // Geen net en niets in de cache. Bij een paginaverzoek een eerlijk
        // bericht in plaats van de foutpagina van de browser; verder een 504.
        if (req.mode === "navigate") {
          return new Response(
            "<!doctype html><meta charset=utf-8>" +
            "<meta name=viewport content='width=device-width,initial-scale=1'>" +
            "<title>Dreamverse</title>" +
            "<body style=\"margin:0;display:grid;place-items:center;height:100vh;" +
            "background:#0A0714;color:#F2EEFB;font:16px system-ui,sans-serif\">" +
            "<p style=\"max-width:22rem;text-align:center;line-height:1.6\">" +
            "Je bent offline. Dreamverse heeft internet nodig om je droom te " +
            "verbeelden.<br><br>Your device is offline. Dreamverse needs a " +
            "connection to imagine your dream.</p>",
            { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } });
        }
        return new Response("", { status: 504, statusText: "offline" });
      });
    })
  );
});
