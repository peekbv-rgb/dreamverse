/* De hulpnummers. Eén lijst, twee pagina's.
 *
 * Dit stond in `app.js`, binnen de IIFE, en daar kon `welkom.html` er niet bij.
 * Sinds de gratis duiding zonder account bestaat, wordt een droom óók op de
 * landingspagina geduid - en een droom over zelfdoding of geweld is daar niet
 * minder ernstig dan in de app. Twee lijsten bijhouden is geen optie: dan
 * loopt er een keer eentje achter, en dat is precies de fout die je hier niet
 * mag maken.
 *
 * Wat je gebruikt: `Zorg.kaderHtml(soorten, taal)` geeft de HTML terug, of een
 * lege string als er niets te melden valt. `soorten` is wat het model
 * classificeerde ("suicide", "geweld"); `taal` is "nl" of "en".
 *
 * Drie regels, en ze zijn geen van drieën onderhandelbaar.
 *
 * 1. **Geen letter komt uit een model.** Het model classificeert alleen; deze
 *    nummers staan hier in de code. Een gehallucineerd crisisnummer is het
 *    ergste wat deze app kan doen.
 * 2. **Alleen wat nagekeken is.** In LANDEN staat uitsluitend wat bij de bron
 *    is geverifieerd. Een land dat er niet in staat krijgt geen nummer, en
 *    dat is beter dan een nummer dat daar niet werkt.
 * 3. **Er is altijd een vangnet.** Find A Helpline (ThroughLine) houdt
 *    hulplijnen bij in ruim 175 landen en heeft een pagina per land. Dat is
 *    beter onderhouden dan een lijst die wij bijhouden, dus die link staat er
 *    altijd bij - ook als we het land wel kennen.
 *
 * Een land toevoegen is één regel in LANDEN. Doe dat alleen met de bron erbij.
 */
(function (root) {
  "use strict";

  var HELPLINE = "https://findahelpline.com/";

  var LANDEN = {
    nl: {
      naam: "Nederland", nood: "112",
      suicide: [
        { naam: "113 Zelfmoordpreventie", waarde: "113", href: "tel:113",
          noot: "dag en nacht, gratis" },
        { naam: "Of gratis", waarde: "0800-0113", href: "tel:08000113", noot: "" },
        { naam: "Online", waarde: "113.nl", href: "https://www.113.nl", noot: "" }
      ],
      geweld: [
        { naam: "Veilig Thuis", waarde: "0800-2000", href: "tel:08002000",
          noot: "gratis, dag en nacht" },
        { naam: "Online", waarde: "veiligthuis.nl",
          href: "https://www.veiligthuis.nl/nl", noot: "" }
      ]
    },
    be: {
      naam: "België", nood: "112",
      suicide: [
        { naam: "Zelfmoordlijn", waarde: "1813", href: "tel:1813",
          noot: "dag en nacht, gratis" },
        { naam: "Online", waarde: "zelfmoord1813.be",
          href: "https://www.zelfmoord1813.be", noot: "" }
      ],
      geweld: [
        { naam: "Nulijn geweld en misbruik", waarde: "1712", href: "tel:1712",
          noot: "gratis en anoniem" },
        { naam: "Online", waarde: "1712.be", href: "https://www.1712.be", noot: "" }
      ]
    },
    de: {
      naam: "Deutschland", nood: "112",
      suicide: [
        { naam: "TelefonSeelsorge", waarde: "0800 111 0 111", href: "tel:08001110111",
          noot: "rund um die Uhr, kostenlos" },
        { naam: "Auch", waarde: "0800 111 0 222", href: "tel:08001110222", noot: "" }
      ],
      geweld: [
        { naam: "Hilfetelefon Gewalt gegen Frauen", waarde: "116 016",
          href: "tel:116016", noot: "kostenlos, rund um die Uhr" },
        { naam: "Online", waarde: "hilfetelefon.de",
          href: "https://www.hilfetelefon.de", noot: "" }
      ]
    },
    gb: {
      naam: "United Kingdom", nood: "999",
      suicide: [
        { naam: "Samaritans", waarde: "116 123", href: "tel:116123",
          noot: "day and night, free" }
      ],
      geweld: [
        { naam: "National Domestic Abuse Helpline", waarde: "0808 2000 247",
          href: "tel:08082000247", noot: "24 hours, free" }
      ]
    },
    us: {
      naam: "United States", nood: "911",
      suicide: [
        { naam: "Suicide & Crisis Lifeline", waarde: "988", href: "tel:988",
          noot: "day and night, free" }
      ],
      geweld: [
        { naam: "National Domestic Violence Hotline", waarde: "1-800-799-7233",
          href: "tel:18007997233", noot: "24 hours, free" }
      ]
    }
  };

  /* In welk land is deze dromer waarschijnlijk?
   *
   * Zonder het te vragen en zonder zijn IP-adres ergens heen te sturen. Eerst de
   * regio uit de taalinstelling van de browser ("de-DE" -> de), want die is het
   * nauwkeurigst als hij er staat. Anders de tijdzone, voor de landen die we
   * kennen. Weten we het niet, dan blijft het leeg - en dan doet Find A Helpline
   * het werk.
   */
  var ZONES = {
    "Europe/Amsterdam": "nl", "Europe/Brussels": "be", "Europe/Berlin": "de",
    "Europe/London": "gb", "Europe/Busingen": "de"
  };

  function landcode() {
    try {
      var talen = navigator.languages || [navigator.language || ""];
      for (var i = 0; i < talen.length; i++) {
        var deel = String(talen[i]).split("-");
        if (deel.length > 1) {
          var code = deel[deel.length - 1].toLowerCase();
          if (LANDEN[code]) { return code; }
        }
      }
      var zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (ZONES[zone]) { return ZONES[zone]; }
      if (/^America\//.test(zone) && /^en/i.test(navigator.language || "")) {
        // Grof, en daarom alleen voor het noodnummer en met de zoeker erbij.
        return null;
      }
    } catch (e) { /* dan weten we het niet */ }
    return null;
  }

  var TEKST = {
    nl: {
      kopSuicide: "Praat erover met iemand.",
      suicide: "In je droom kwam zelfdoding voor. Denk je hier ook wakker aan, "
             + "praat er dan vandaag met iemand over: iemand die je vertrouwt, of "
             + "je huisarts.",
      kopGeweld: "Praat erover met iemand.",
      geweld: "Er kwam geweld voor in je droom. Speelt er in je leven iets waar "
            + "geweld bij komt, dan hoef je dat niet alleen op te lossen. Praat met "
            + "iemand die je vertrouwt.",
      nood: "Direct gevaar",
      zoeker: "Hulplijnen in jouw land",
      elders: "Woon je ergens anders, dan vind je daar de hulplijnen van jouw land."
    },
    en: {
      kopSuicide: "Talk to someone about it.",
      suicide: "Your dream involved suicide. If this is on your mind when you are "
             + "awake too, talk to someone today: someone you trust, or your doctor.",
      kopGeweld: "Talk to someone about it.",
      geweld: "Your dream involved violence. If something in your life involves "
            + "violence, you do not have to solve it alone. Talk to someone you trust.",
      nood: "Immediate danger",
      zoeker: "Helplines in your country",
      elders: "Living somewhere else? That page lists the helplines for your country."
    }
  };

  function regel(naam, waarde, href, noot) {
    var extern = href.indexOf("http") === 0;
    return "<li><span>" + naam + "</span> " +
      '<a href="' + href + '"' + (extern ? ' target="_blank" rel="noopener"' : "") +
      ">" + waarde + "</a>" +
      (noot ? " <em>" + noot + "</em>" : "") + "</li>";
  }

  /* Het hulpkader, als HTML.
   *
   * Het hoort bóven de duiding te staan en niet eronder: wie dit nodig heeft
   * moet het zien voordat hij begint te lezen. En de duiding zelf gaat er niet
   * over - het model heeft opdracht om geen hulp aan te raden, juist zodat het
   * niet over deze nummers kan liegen.
   */
  function kaderHtml(soorten, taal) {
    soorten = soorten || [];
    var w = TEKST[taal === "en" ? "en" : "nl"];
    var code = landcode();
    var land = LANDEN[code] || null;
    var stukken = [];

    ["suicide", "geweld"].forEach(function (soort) {
      if (soorten.indexOf(soort) === -1) { return; }
      var html = '<div class="zorg-blok zorg-' + soort + '">' +
        '<p class="zorg-kop">' + (soort === "suicide" ? w.kopSuicide : w.kopGeweld) +
        "</p><p>" + (soort === "suicide" ? w.suicide : w.geweld) + "</p><ul>";

      // Wat we van dit land weten. Kennen we het land niet, dan slaan we dit
      // over - een nummer uit een ander land is erger dan geen nummer.
      (land ? land[soort] : []).forEach(function (r) {
        html += regel(r.naam, r.waarde, r.href, r.noot);
      });
      if (land && land.nood) {
        html += regel(w.nood, land.nood, "tel:" + land.nood.replace(/\s/g, ""), "");
      }
      // En altijd de zoeker: ruim 175 landen, door mensen die dit bijhouden.
      html += regel(w.zoeker, "findahelpline.com",
                    HELPLINE + (land ? "countries/" + code : ""), "");
      html += "</ul>";
      if (!land) { html += '<p class="zorg-elders">' + w.elders + "</p>"; }
      html += "</div>";
      stukken.push(html);
    });

    return stukken.join("");
  }

  root.Zorg = { kaderHtml: kaderHtml, landcode: landcode, HELPLINE: HELPLINE };
})(window);
