/* Een levende achtergrond: zeven stromen licht die door elkaar heen bewegen,
   elk in de kleur van een chakra.

   Waarom canvas en geen CSS: met verlopen kun je een beeld laten schuiven, maar
   niet laten stromen. Hier verandert de vorm zelf, elke frame, zodat het licht
   ademt in plaats van verschuift.

   Het draait op een klein doek (een derde van het scherm) dat door CSS wordt
   uitgerekt en vervaagd. Dat scheelt zo veel rekenwerk dat het ook op een
   telefoon soepel blijft, en de onscherpte hoort toch bij het beeld.

   Twee regels netheid: bij `prefers-reduced-motion` staat hij stil op één beeld,
   en zodra het tabblad niet zichtbaar is stopt de lus. Een droom-app hoort geen
   batterij leeg te trekken terwijl niemand kijkt. */

(function () {
  "use strict";

  var doek = document.getElementById("achtergrond");
  if (!doek || !doek.getContext) { return; }
  var ctx = doek.getContext("2d", { alpha: false });
  if (!ctx) { return; }

  // Van kroon naar wortel: dezelfde volgorde als de kolom naast Vera.
  var STROMEN = [
    { kleur: [214, 150, 255], hoogte: 0.10, snelheid: 0.00170, golf: 0.9, drift: 0.030 },
    { kleur: [130, 116, 255], hoogte: 0.22, snelheid: 0.00138, golf: 1.3, drift: -0.024 },
    { kleur: [ 74, 176, 255], hoogte: 0.34, snelheid: 0.00198, golf: 1.1, drift: 0.036 },
    { kleur: [ 64, 214, 150], hoogte: 0.47, snelheid: 0.00116, golf: 1.6, drift: -0.030 },
    { kleur: [255, 214,  92], hoogte: 0.60, snelheid: 0.00178, golf: 1.2, drift: 0.027 },
    { kleur: [255, 146,  60], hoogte: 0.74, snelheid: 0.00152, golf: 1.45, drift: -0.033 },
    { kleur: [255,  92,  86], hoogte: 0.88, snelheid: 0.00129, golf: 1.0, drift: 0.021 }
  ];

  var SCHAAL = 3;            // een derde van de schermgrootte
  var breedte = 0, hoogte = 0;
  var stil = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var lus = null;

  function meten() {
    breedte = doek.width = Math.max(160, Math.ceil(window.innerWidth / SCHAAL));
    hoogte = doek.height = Math.max(160, Math.ceil(window.innerHeight / SCHAAL));
  }

  function teken(t) {
    // De nacht eronder.
    var lucht = ctx.createLinearGradient(0, 0, 0, hoogte);
    lucht.addColorStop(0, "#241640");
    lucht.addColorStop(0.55, "#120A24");
    lucht.addColorStop(1, "#080611");
    ctx.fillStyle = lucht;
    ctx.fillRect(0, 0, breedte, hoogte);

    // Licht stapelt op in plaats van te bedekken: zo mengen de kleuren.
    ctx.globalCompositeOperation = "lighter";

    for (var i = 0; i < STROMEN.length; i++) {
      var s = STROMEN[i];
      // De hele band drijft ook op en neer, anders golft alleen de rand.
      var basis = hoogte * (s.hoogte + Math.sin(t * s.snelheid * 0.45 + i) * s.drift);
      var fase = t * s.snelheid + i * 1.7;

      // Elke stroom is een band die van links naar rechts golft. Twee sinussen
      // over elkaar, zodat het patroon zich niet hoorbaar herhaalt.
      ctx.beginPath();
      ctx.moveTo(0, hoogte);
      for (var x = 0; x <= breedte; x += 6) {
        var u = x / breedte;
        var y = basis
              + Math.sin(u * Math.PI * s.golf * 2 + fase) * hoogte * 0.16
              + Math.sin(u * Math.PI * s.golf * 5 + fase * 1.7) * hoogte * 0.06
              + Math.sin(u * Math.PI * s.golf * 9 - fase * 0.8) * hoogte * 0.025;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(breedte, hoogte);
      ctx.closePath();

      var band = ctx.createLinearGradient(0, basis - hoogte * 0.2, 0, basis + hoogte * 0.35);
      var k = s.kleur;
      band.addColorStop(0, "rgba(" + k[0] + "," + k[1] + "," + k[2] + ",0)");
      band.addColorStop(0.35, "rgba(" + k[0] + "," + k[1] + "," + k[2] + ",0.40)");
      band.addColorStop(1, "rgba(" + k[0] + "," + k[1] + "," + k[2] + ",0)");
      ctx.fillStyle = band;
      ctx.fill();
    }

    // Drie lichtvlekken die langzaam over het beeld trekken, elk zijn eigen baan.
    var vlekken = [
      { k: [255, 170, 255], x: 0.5 + 0.36 * Math.sin(t * 0.00030), y: 0.22 + 0.10 * Math.cos(t * 0.00042), r: 0.42 },
      { k: [120, 220, 255], x: 0.5 + 0.42 * Math.sin(t * 0.00021 + 2.1), y: 0.55 + 0.14 * Math.cos(t * 0.00028 + 1), r: 0.38 },
      { k: [255, 190, 110], x: 0.5 + 0.38 * Math.cos(t * 0.00025 + 4), y: 0.80 + 0.10 * Math.sin(t * 0.00034 + 3), r: 0.34 }
    ];
    for (var w = 0; w < vlekken.length; w++) {
      var v = vlekken[w];
      var vg = ctx.createRadialGradient(v.x * breedte, v.y * hoogte, 0,
                                        v.x * breedte, v.y * hoogte, hoogte * v.r);
      vg.addColorStop(0, "rgba(" + v.k[0] + "," + v.k[1] + "," + v.k[2] + ",0.26)");
      vg.addColorStop(1, "rgba(" + v.k[0] + "," + v.k[1] + "," + v.k[2] + ",0)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, breedte, hoogte);
    }

    // De lichtkern bovenin, die langzaam ademt.
    var puls = 0.5 + 0.5 * Math.sin(t * 0.0021);
    var kern = ctx.createRadialGradient(
      breedte * 0.5, hoogte * 0.04, 0,
      breedte * 0.5, hoogte * 0.04, hoogte * (0.34 + puls * 0.06));
    kern.addColorStop(0, "rgba(255,255,255,0.34)");
    kern.addColorStop(0.35, "rgba(214,150,255,0.20)");
    kern.addColorStop(1, "rgba(214,150,255,0)");
    ctx.fillStyle = kern;
    ctx.fillRect(0, 0, breedte, hoogte);

    ctx.globalCompositeOperation = "source-over";
  }

  function frame(t) {
    teken(t);
    lus = window.requestAnimationFrame(frame);
  }

  function start() {
    if (lus !== null || stil) { return; }
    lus = window.requestAnimationFrame(frame);
  }

  function stop() {
    if (lus !== null) { window.cancelAnimationFrame(lus); lus = null; }
  }

  window.addEventListener("resize", function () { meten(); if (stil) { teken(0); } });
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) { stop(); } else { start(); }
  });

  meten();
  // Altijd meteen één beeld neerzetten. requestAnimationFrame loopt niet in een
  // tabblad dat op de achtergrond staat, en dan zou het doek zwart blijven tot
  // iemand terugkomt.
  teken(0);
  if (!stil) { start(); }
})();
