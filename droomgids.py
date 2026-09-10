"""Vera's Dream Guide: de publieke kennislaag.

Google levert de eerste droom, Dreamverse zorgt dat iemand zijn volgende ook wil
bewaren. Dat is de hele redenering achter deze pagina's: wie zoekt op *dream
about snakes* krijgt een algemene betekenis, en onderaan de enige vraag die die
betekenis persoonlijk maakt — wat deed die slang, en hoe voelde jij je.

**De artikelen zijn gegevens, geen HTML.** Eén JSON per onderwerp in
`knowledge/droomgids/`, één sjabloon hier. Onderwerp eenentwintig is daarmee een
bestandje van tien regels in plaats van een pagina overtikken, en een wijziging
in de vormgeving raakt ze allemaal tegelijk.

**Engels, en niet tweetalig.** De zoekvraag is Engels: *dream about teeth
falling out* wordt honderdduizenden keren per maand gezocht, de Nederlandse
variant een fractie daarvan. Twintig artikelen vertalen verdubbelt het werk voor
een markt die hier vijftig keer kleiner is. De app blijft wel tweetalig; dit is
de laag ervoor.

**Dezelfde grenzen als de duiding.** Wat hier staat zijn associaties uit
tradities en uit de psychologie, geen feiten en geen diagnose. Nooit over
gezondheid, ziekte, geld, zwangerschap als voorspelling, of iemands dood. Een
pagina die zegt "dromen over tanden betekent dat er iemand ziek wordt" bezorgt
mensen echte angst, en die kun je niet terugnemen.
"""

import html
import json
from pathlib import Path

WORTEL = Path(__file__).parent
GIDS = WORTEL / "knowledge" / "droomgids"
BASIS = "/dream-meaning"

# Waar de canonieke adressen naartoe wijzen. Google wil één adres per pagina, en
# zonder dit concurreren het kale domein en www met elkaar om dezelfde tekst.
SITE = "https://vera-dreamverse.com"

# Het beeld dat een gedeelde link laat zien. Heeft een onderwerp er zelf een,
# dan wint die; anders het vaste beeld van de site.
#
# Dit was leeg zolang een onderwerp geen eigen beeld had - en dat heeft er nog
# geen enkele. Een gidspagina in een Instagram-verhaal, een DM of een
# WhatsApp-bericht was daarmee een grijze regel tekst, terwijl dit juist de
# pagina's zijn die bedoeld zijn om te delen. Komt het beeld per onderwerp er,
# dan valt deze regel vanzelf weg.
OG_STANDAARD = "/og-beeld.jpg"

# "Terug naar Dreamverse" wijst naar de landingspagina en niet naar "/".
#
# De gids hoort bij de publieke laag, en de publieke laag begint bij
# welkom.html. Voor iemand van Google verandert er niets - die komt op "/"
# toch op welkom.html uit. Maar wie ingelogd is werd door "/" de app in
# geduwd, met Vera's introductie erbij, en dat is geen "terug".
THUIS = "/welkom.html"


TALEN = ("en", "nl")


def pad_voor(taal, slug=""):
    """Het adres van een pagina in een taal. Engels is de kale vorm."""
    voor = "" if taal == "en" else "/" + taal
    return voor + BASIS + ("/" + slug if slug else "/")


def veld(d, sleutel, taal, standaard=""):
    """Een veld in de gevraagde taal, met het Engels als terugval.

    Zo hoeft een nieuw onderwerp niet meteen vertaald te zijn: dan staat de
    Engelse tekst er, en dat is beter dan een half lege pagina.
    """
    if taal != "en":
        anders = (d.get(taal) or {})
        if anders.get(sleutel):
            return anders[sleutel]
    return d.get(sleutel, standaard)


def heeft_taal(d, taal):
    return taal == "en" or bool((d.get(taal) or {}).get("intro"))


# De categorieën, in de volgorde waarin ze op de pagina staan. Een onderwerp
# zonder categorie belandt onderaan bij "Other" - beter dan verdwijnen.
GROEPEN = ("people", "animals", "events", "places", "emotions", "other")
GROEPNAAM = {
    "en": {"people": "People", "animals": "Animals", "events": "Events",
           "places": "Places", "emotions": "Emotions", "other": "Other"},
    "nl": {"people": "Mensen", "animals": "Dieren", "events": "Gebeurtenissen",
           "places": "Plaatsen", "emotions": "Gevoelens", "other": "Overig"},
}


def _e(tekst):
    return html.escape(str(tekst or ""), quote=True)


def onderwerpen():
    """Alle onderwerpen, op titel gesorteerd. Stille overslag bij kapotte JSON.

    Een tikfout in één bestand mag de hele bibliotheek niet platleggen: dan is
    de pagina waar Google op staat ineens leeg, en dat merk je pas als het
    verkeer weg is.
    """
    uit = []
    if not GIDS.is_dir():
        return uit
    for pad in sorted(GIDS.glob("*.json")):
        try:
            d = json.loads(pad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        d.setdefault("slug", pad.stem)
        if d.get("title"):
            uit.append(d)
    return sorted(uit, key=lambda d: d["title"].lower())


def onderwerp(slug):
    pad = GIDS / (slug + ".json")
    if not pad.is_file():
        return None
    try:
        d = json.loads(pad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    d.setdefault("slug", slug)
    return d


# --------------------------------------------------------------------------- #
# Het omhulsel
# --------------------------------------------------------------------------- #

KOP = """<!doctype html>
<html lang="{taal}" translate="no" class="notranslate">
<head>
<meta charset="utf-8">
<meta name="google" content="notranslate">
<title>{titel}</title>
<meta name="description" content="{beschrijving}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="{canoniek}">
{alternatief}
<meta property="og:type" content="article">
<meta property="og:title" content="{titel}">
<meta property="og:description" content="{beschrijving}">
<meta property="og:url" content="{canoniek}">
{ogbeeld}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=Karla:wght@400;500;600&display=swap">
<link rel="stylesheet" href="/style.css">
{schema}
</head>
<body class="tekstpagina gids">

<div class="wrap">
  <header class="top">
    <div class="meta">
      <a class="terug" href="{terug_href}">&larr; {terug_tekst}</a>
      <span><a href="/welkom.html">Dreamverse</a></span>
      <span class="dim" id="taalknoppen">{taalknoppen}</span>
    </div>
"""

VOET = """  </div>

  <footer class="end">
    <p class="gegevens-voet">{voorbehoud}</p>
    <p><a href="{basis}">{alle}</a> &nbsp;&middot;&nbsp;
      <a href="/welkom.html">Dreamverse</a> &nbsp;&middot;&nbsp;
      <a href="/privacy.html">{privacy}</a></p>
  </footer>
</div>

<script src="/gids.js"></script>
</body>
</html>
"""

# Het voorbehoud is geen formaliteit. Bij zoekverkeer komen mensen binnen die
# zich ergens zorgen over maken, en dan hoort er te staan dat dit associaties
# zijn en geen feiten.
VOET_TEKST = {
    "en": {
        "voorbehoud": ("Dream meanings on this page are general associations from "
                       "psychology and from various traditions. They are not facts, "
                       "not a diagnosis and not advice. What a dream means depends on "
                       "what happened in it and on the person who dreamt it."),
        "alle": "All dream meanings",
        "privacy": "Privacy statement",
    },
    "nl": {
        "voorbehoud": ("Wat hier over dromen staat zijn algemene associaties uit de "
                       "psychologie en uit verschillende tradities. Het zijn geen "
                       "feiten, geen diagnose en geen advies. Wat een droom betekent "
                       "hangt af van wat erin gebeurde en van wie hem droomde."),
        "alle": "Alle droombetekenissen",
        "privacy": "Privacyverklaring",
    },
}

CTA_TEKST = {
    "en": ("Your dream is more than one symbol.", "Tell Vera your dream",
           "Interpret my dream"),
    "nl": ("Je droom is meer dan één teken.", "Vertel Vera je droom",
           "Duid mijn droom"),
}


def _ogbeeld(pad=None):
    """De beeldtags voor een gedeelde link.

    De maten staan er alleen bij het vaste beeld: die kennen we (1200 x 630), en
    Facebook en LinkedIn tonen het kaartje daarmee meteen groot in plaats van
    eerst klein en dan verspringend. Van een eigen beeld per onderwerp weten we
    de maat hier niet, dus dan laten we ze weg.
    """
    if pad:
        return ('<meta property="og:image" content="{}{}">\n'
                '<meta name="twitter:card" content="summary_large_image">'
                .format(SITE, _e(pad)))
    return ('<meta property="og:image" content="{}{}">\n'
            '<meta property="og:image:type" content="image/jpeg">\n'
            '<meta property="og:image:width" content="1200">\n'
            '<meta property="og:image:height" content="630">\n'
            '<meta name="twitter:card" content="summary_large_image">'
            .format(SITE, OG_STANDAARD))


def _taalstukken(taal, slug, talen):
    """De hreflang-regels en de EN/NL-knoppen.

    hreflang vertelt Google dat dit vertalingen van elkaar zijn en geen
    dubbele tekst; zonder dat concurreren twee pagina's om dezelfde plek.
    """
    regels, knoppen = [], []
    for code in TALEN:
        if code not in talen:
            continue
        adres = SITE + pad_voor(code, slug)
        regels.append('<link rel="alternate" hreflang="{}" href="{}">'.format(code, adres))
        naam = "English" if code == "en" else "Nederlands"
        if code == taal:
            knoppen.append('<b>{}</b>'.format(naam))
        else:
            knoppen.append('<a href="{}">{}</a>'.format(pad_voor(code, slug), naam))
    if len(talen) > 1:
        regels.append('<link rel="alternate" hreflang="x-default" href="{}">'.format(
            SITE + pad_voor("en", slug)))
    return "\n".join(regels), " &middot; ".join(knoppen)


def _uitnodiging(regel, taal="en", tweede=False):
    """Het blok dat naar de app leidt. Overal hetzelfde, want het is de conversie."""
    kop, knop1, knop2 = CTA_TEKST.get(taal, CTA_TEKST["en"])
    return """
    <div class="gids-cta">
      <p class="gids-cta-kop">{kop}</p>
      <p>{regel}</p>
      <a class="knop-als-link" href="/app">{knop} &rarr;</a>
    </div>
""".format(kop=_e(kop), regel=_e(regel), knop=_e(knop2 if tweede else knop1))


# --------------------------------------------------------------------------- #
# De overzichtspagina
# --------------------------------------------------------------------------- #

OVERZICHT_TEKST = {
    "en": {
        "kop": "Vera's Dream Guide",
        "sub": "The growing library of the things we dream about. What did you dream about?",
        "zoek": "Search…",
        "leeg": ("Nothing here yet for that word. Tell Vera about it instead — "
                 "she reads the dream, not the keyword."),
        "cta": ("A dream dictionary explains the symbol. Vera interprets the dream "
                "around it — and everything you dreamt before it."),
        "titel": "Dream Meanings &mdash; Vera's Dream Guide",
        "meta": ("What do snakes, teeth, water or an ex mean in a dream? Explore the "
                 "symbols, people and places that appear in our dreams — and get your "
                 "own dream read by Vera."),
        "terug": "Dreamverse",
    },
    "nl": {
        "kop": "Vera's Dream Guide",
        "sub": "De groeiende bibliotheek van waar we over dromen. Waar droomde jij over?",
        "zoek": "Zoeken…",
        "leeg": ("Daar staat nog niets over. Vertel het aan Vera — zij leest de droom, "
                 "niet het zoekwoord."),
        "cta": ("Een droomwoordenboek verklaart het teken. Vera duidt de droom "
                "eromheen — en alles wat je eerder droomde."),
        "titel": "Wat betekent je droom? &mdash; Vera's Dream Guide",
        "meta": ("Wat betekenen slangen, tanden, water of een ex in een droom? Ontdek de "
                 "tekens, mensen en plaatsen die in onze dromen opduiken — en laat je "
                 "eigen droom lezen door Vera."),
        "terug": "Dreamverse",
    },
}


def overzicht(taal="en"):
    lijst = [d for d in onderwerpen() if heeft_taal(d, taal)]
    w = OVERZICHT_TEKST.get(taal, OVERZICHT_TEKST["en"])
    def kaart(d):
        zoekwoorden = " ".join(
            [veld(d, "title", taal), d.get("title", ""), d.get("search", "")]
            + list(d.get("also", []))).lower()
        return ('      <a class="gids-kaart" href="{href}" data-zoek="{zoek}">\n'
                '        {beeld}\n'
                '        <span class="gids-kaart-titel">{titel}</span>\n'
                '        <span class="gids-kaart-regel">{regel}</span>\n'
                '      </a>'.format(
                    href=_e(pad_voor(taal, d["slug"])), zoek=_e(zoekwoorden),
                    beeld=('<img src="{}" alt="" loading="lazy">'.format(_e(d["image"]))
                           if d.get("image") else ""),
                    titel=_e(veld(d, "title", taal)),
                    regel=_e(veld(d, "card", taal))))

    # Per categorie een kop met zijn kaarten eronder. Zolang er maar een handvol
    # onderwerpen is voegen koppen niets toe en staat alles op één hoop; vanaf
    # een stuk of acht wordt de lijst een lijst en helpen ze wel.
    namen = GROEPNAAM.get(taal, GROEPNAAM["en"])
    def raster(rijen, kop=None):
        uit = ""
        if kop:
            uit += '    <h2 class="gids-groep">{}</h2>\n'.format(_e(kop))
        return (uit + '    <div class="gids-kaarten">\n'
                + "\n".join(rijen) + "\n    </div>\n")

    # Elke groep zijn eigen raster met de kop erbóven, en niet één raster waar
    # de koppen in vallen - dan worden het zelf roostervakjes en staan ze naast
    # de kaarten in plaats van erboven.
    if len(lijst) < 8:
        kaarten = raster([kaart(d) for d in lijst])
    else:
        stukken = []
        for groep in GROEPEN:
            hier = [d for d in lijst if (d.get("category") or "other") == groep]
            if hier:
                stukken.append(raster([kaart(d) for d in hier], namen[groep]))
        kaarten = "".join(stukken)

    body = """    <h1 id="title">{kop}</h1>
    <p class="sub">{sub}</p>
    <div class="gids-zoek">
      <input type="search" id="gids-zoek" placeholder="{zoek}"
             autocomplete="off" aria-label="{zoek}">
    </div>
  </header>

  <section>
    <div id="gids-kaarten">
{kaarten}    </div>
    <p class="gids-leeg" id="gids-leeg" hidden>{leeg}</p>
{cta}
  </section>
""".format(kop=_e(w["kop"]), sub=_e(w["sub"]), zoek=_e(w["zoek"]),
           leeg=_e(w["leeg"]), kaarten=kaarten,
           cta=_uitnodiging(w["cta"], taal))

    alternatief, knoppen = _taalstukken(taal, "", TALEN)
    return (KOP.format(
        titel=w["titel"], beschrijving=_e(w["meta"]),
        canoniek=SITE + pad_voor(taal), alternatief=alternatief,
        ogbeeld=_ogbeeld(), schema=_schema_lijst(lijst, taal),
        taalknoppen=knoppen, taal=taal,
        terug_href="/welkom.html", terug_tekst=_e(w["terug"]))
        + body + VOET.format(basis=pad_voor(taal), taal=taal, **VOET_TEKST[taal]))


# --------------------------------------------------------------------------- #
# Eén onderwerp
# --------------------------------------------------------------------------- #

BRILLEN = ("psychological", "symbolic", "spiritual")

# De drie brillen heten in de app hetzelfde; dat is met opzet, zodat iemand die
# van de gids naar de app loopt dezelfde woorden terugziet.
KOPPEN = {
    "en": {"psychological": "Psychological perspective",
           "symbolic": "Symbolic perspective",
           "spiritual": "Spiritual perspective",
           "punt": "What it can point to",
           "details": "The details change everything",
           "faq": "Frequently asked questions",
           "verwant": "Related dreams",
           "sub": "What could it mean?",
           "cta": "Tell Vera what actually happened.",
           "terug": "All dream meanings"},
    "nl": {"psychological": "Psychologisch bekeken",
           "symbolic": "Symbolisch bekeken",
           "spiritual": "Spiritueel bekeken",
           "punt": "Waar het op kan wijzen",
           "details": "De details veranderen alles",
           "faq": "Veelgestelde vragen",
           "verwant": "Verwante dromen",
           "sub": "Wat kan het betekenen?",
           "cta": "Vertel Vera wat er werkelijk gebeurde.",
           "terug": "Alle droombetekenissen"},
}


def artikel(slug, taal="en"):
    d = onderwerp(slug)
    if d is None or not heeft_taal(d, taal):
        return None
    k = KOPPEN.get(taal, KOPPEN["en"])

    brillen = (veld(d, "perspectives", taal) or {})
    blokken = []
    for sleutel in BRILLEN:
        tekst = brillen.get(sleutel)
        if not tekst:
            continue
        blokken.append(
            '      <div class="block">\n'
            '        <span class="lbl">{kop}</span>\n'
            '        <p>{tekst}</p>\n'
            '      </div>'.format(kop=_e(k[sleutel]), tekst=_e(tekst)))

    vragen = "".join(
        "        <li>{}</li>\n".format(_e(v))
        for v in (veld(d, "details", taal) or []))

    faq = "".join(
        '      <div class="gids-faq-paar">\n'
        '        <p class="gids-faq-v">{v}</p>\n'
        '        <p>{a}</p>\n'
        '      </div>\n'.format(v=_e(x.get("q")), a=_e(x.get("a")))
        for x in (veld(d, "faq", taal) or []))

    verwant = ""
    if d.get("related"):
        namen = []
        for s in d["related"]:
            ander = onderwerp(s)
            if ander and heeft_taal(ander, taal):
                namen.append('<a href="{h}">{t}</a>'.format(
                    h=_e(pad_voor(taal, s)), t=_e(veld(ander, "title", taal))))
        if namen:
            verwant = ('  <section>\n    <div class="head-rule">'
                       '<h2>{kop}</h2></div>\n'
                       '    <p class="gids-verwant">{namen}</p>\n  </section>\n'
                       .format(kop=_e(k["verwant"]), namen=" &middot; ".join(namen)))

    body = """    <h1 id="title">{titel}</h1>
    <p class="sub">{ondertitel}</p>
  </header>

{hero}
  <section>
    <blockquote class="gids-vera">
      <p>{vera}</p>
      <cite>&mdash; Vera</cite>
    </blockquote>
    <p class="lead">{intro}</p>
  </section>

  <section>
    <div class="head-rule"><h2>{kop_punt}</h2></div>
    <div class="reading">
{blokken}
    </div>
  </section>

  <section>
    <div class="head-rule"><h2>{kop_details}</h2></div>
    <ul class="gids-vragen">
{vragen}    </ul>
{cta}  </section>

{faqblok}{verwant}""".format(
        titel=_e(veld(d, "title", taal)),
        ondertitel=_e(veld(d, "subtitle", taal, k["sub"])),
        hero=('  <img class="gids-hero" src="{}" alt="{}">\n'.format(
                  _e(d["image"]), _e(veld(d, "title", taal)))
              if d.get("image") else ""),
        vera=_e(veld(d, "vera", taal)),
        intro=_e(veld(d, "intro", taal)),
        kop_punt=_e(k["punt"]), kop_details=_e(k["details"]),
        blokken="\n".join(blokken),
        vragen=vragen,
        cta=_uitnodiging(veld(d, "cta", taal, k["cta"]), taal, tweede=True),
        faqblok=('  <section>\n    <div class="head-rule">'
                 '<h2>{kop}</h2></div>\n'
                 '    <div class="gids-faq">\n{faq}    </div>\n  </section>\n'.format(
                     kop=_e(k["faq"]), faq=faq)
                 if faq else ""),
        verwant=verwant)

    talen = [c for c in TALEN if heeft_taal(d, c)]
    alternatief, knoppen = _taalstukken(taal, d["slug"], talen)
    return (KOP.format(
        titel=_e(veld(d, "seo_title", taal, veld(d, "title", taal) + " | Vera Dreamverse")),
        beschrijving=_e(veld(d, "meta", taal)),
        canoniek=SITE + pad_voor(taal, d["slug"]),
        alternatief=alternatief,
        ogbeeld=_ogbeeld(d.get("image")),
        schema=_schema_artikel(d, taal),
        taalknoppen=knoppen, taal=taal,
        terug_href=pad_voor(taal), terug_tekst=_e(k["terug"]))
        + body + VOET.format(basis=pad_voor(taal), **VOET_TEKST[taal]))


# --------------------------------------------------------------------------- #
# Wat Google eruit leest
# --------------------------------------------------------------------------- #

def _json_ld(data):
    # </script> in een tekst zou het blok afbreken; json.dumps ontsnapt dat niet.
    ruw = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return '<script type="application/ld+json">{}</script>'.format(ruw)


def _schema_artikel(d, taal="en"):
    """Article plus FAQPage. De FAQ is wat Google uitklapt in de zoekresultaten."""
    stukken = [{
        "@context": "https://schema.org",
        "@type": "Article",
        "inLanguage": taal,
        "headline": veld(d, "seo_title", taal) or veld(d, "title", taal),
        "description": veld(d, "meta", taal),
        "mainEntityOfPage": SITE + pad_voor(taal, d["slug"]),
        "author": {"@type": "Organization", "name": "Vera Dreamverse"},
        "publisher": {"@type": "Organization", "name": "Vera Dreamverse"},
    }]
    if d.get("image"):
        stukken[0]["image"] = SITE + d["image"]
    vragen = veld(d, "faq", taal)
    if vragen:
        stukken.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "inLanguage": taal,
            "mainEntity": [
                {"@type": "Question", "name": x.get("q", ""),
                 "acceptedAnswer": {"@type": "Answer", "text": x.get("a", "")}}
                for x in vragen],
        })
    return "\n".join(_json_ld(s) for s in stukken)


def _schema_lijst(lijst, taal="en"):
    return _json_ld({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "inLanguage": taal,
        "name": "Vera's Dream Guide",
        "url": SITE + pad_voor(taal),
        "hasPart": [{"@type": "Article", "headline": veld(d, "title", taal),
                     "url": SITE + pad_voor(taal, d["slug"])} for d in lijst],
    })


def sitemap():
    """Alle adressen die Google mag kennen, in beide talen."""
    adressen = [SITE + "/", SITE + "/welkom.html", SITE + "/privacy.html"]
    for taal in TALEN:
        lijst = [d for d in onderwerpen() if heeft_taal(d, taal)]
        if not lijst and taal != "en":
            continue
        adressen.append(SITE + pad_voor(taal))
        adressen += [SITE + pad_voor(taal, d["slug"]) for d in lijst]
    regels = "".join("  <url><loc>{}</loc></url>\n".format(_e(a)) for a in adressen)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + regels + "</urlset>\n")


def robots():
    return "User-agent: *\nAllow: /\nSitemap: {}/sitemap.xml\n".format(SITE)
