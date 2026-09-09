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
<html lang="en">
<head>
<meta charset="utf-8">
<title>{titel}</title>
<meta name="description" content="{beschrijving}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="{canoniek}">
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
      <span><a href="/">Dreamverse</a></span>
      <span class="dim">dream guide</span>
    </div>
"""

VOET = """  </div>

  <footer class="end">
    <p class="gegevens-voet">Dream meanings on this page are general
      associations from psychology and from various traditions. They are not
      facts, not a diagnosis and not advice. What a dream means depends on what
      happened in it and on the person who dreamt it.</p>
    <p><a href="{basis}/">All dream meanings</a> &nbsp;&middot;&nbsp;
      <a href="/">Dreamverse</a> &nbsp;&middot;&nbsp;
      <a href="/privacy.html">Privacy statement</a></p>
  </footer>
</div>

<script src="/gids.js"></script>
</body>
</html>
"""


def _uitnodiging(regel, knop="Tell Vera your dream"):
    """Het blok dat naar de app leidt. Overal hetzelfde, want het is de conversie."""
    return """
    <div class="gids-cta">
      <p class="gids-cta-kop">Your dream is more than one symbol.</p>
      <p>{regel}</p>
      <a class="knop-als-link" href="/app">{knop} &rarr;</a>
    </div>
""".format(regel=_e(regel), knop=_e(knop))


# --------------------------------------------------------------------------- #
# De overzichtspagina
# --------------------------------------------------------------------------- #

def overzicht():
    lijst = onderwerpen()
    kaarten = []
    for d in lijst:
        kaarten.append(
            '      <a class="gids-kaart" href="{basis}/{slug}" data-zoek="{zoek}">\n'
            '        {beeld}\n'
            '        <span class="gids-kaart-titel">{titel}</span>\n'
            '        <span class="gids-kaart-regel">{regel}</span>\n'
            '      </a>'.format(
                basis=BASIS, slug=_e(d["slug"]),
                zoek=_e(" ".join([d.get("title", ""), d.get("search", "")]
                                 + list(d.get("also", []))).lower()),
                beeld=('<img src="{}" alt="" loading="lazy">'.format(_e(d["image"]))
                       if d.get("image") else ""),
                titel=_e(d["title"]), regel=_e(d.get("card", ""))))

    body = """    <h1 id="title">Vera's Dream Guide</h1>
    <p class="sub">The growing library of the things we dream about. What did
      you dream about?</p>
    <p class="gids-zoek">
      <input type="search" id="gids-zoek" placeholder="Search your dream…"
             autocomplete="off" aria-label="Search your dream">
    </p>
  </header>

  <section>
    <div class="gids-kaarten" id="gids-kaarten">
{kaarten}
    </div>
    <p class="gids-leeg" id="gids-leeg" hidden>Nothing here yet for that word.
      Tell Vera about it instead — she reads the dream, not the keyword.</p>
{cta}
  </section>
""".format(kaarten="\n".join(kaarten),
           cta=_uitnodiging("A dream dictionary gives you the average. Vera reads "
                            "what actually happened in yours, and everything you "
                            "dreamt before it."))

    schema = _schema_lijst(lijst)
    return (KOP.format(
        titel="Dream Meanings &mdash; Vera's Dream Guide | Dreamverse",
        beschrijving=("What do snakes, teeth, water or an ex mean in a dream? "
                      "Explore the symbols, people and places that appear in our "
                      "dreams — and get your own dream read by Vera."),
        canoniek=SITE + BASIS + "/",
        ogbeeld="",
        schema=schema,
        terug_href="/", terug_tekst="Dreamverse")
        + body + VOET.format(basis=BASIS))


# --------------------------------------------------------------------------- #
# Eén onderwerp
# --------------------------------------------------------------------------- #

BRILLEN = (("psychological", "Psychological perspective"),
           ("symbolic", "Symbolic perspective"),
           ("spiritual", "Spiritual perspective"))


def artikel(slug):
    d = onderwerp(slug)
    if d is None:
        return None

    blokken = []
    for sleutel, kop in BRILLEN:
        tekst = (d.get("perspectives") or {}).get(sleutel)
        if not tekst:
            continue
        blokken.append(
            '      <div class="block">\n'
            '        <span class="lbl">{kop}</span>\n'
            '        <p>{tekst}</p>\n'
            '      </div>'.format(kop=_e(kop), tekst=_e(tekst)))

    vragen = "".join(
        "        <li>{}</li>\n".format(_e(v)) for v in (d.get("details") or []))

    faq = "".join(
        '      <div class="gids-faq-paar">\n'
        '        <p class="gids-faq-v">{v}</p>\n'
        '        <p>{a}</p>\n'
        '      </div>\n'.format(v=_e(x.get("q")), a=_e(x.get("a")))
        for x in (d.get("faq") or []))

    verwant = ""
    if d.get("related"):
        namen = []
        for s in d["related"]:
            ander = onderwerp(s)
            if ander:
                namen.append('<a href="{b}/{s}">{t}</a>'.format(
                    b=BASIS, s=_e(s), t=_e(ander["title"])))
        if namen:
            verwant = ('  <section>\n    <div class="head-rule">'
                       '<h2>Related dreams</h2></div>\n'
                       '    <p class="gids-verwant">{}</p>\n  </section>\n'
                       .format(" &middot; ".join(namen)))

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
    <div class="head-rule"><h2>What it can point to</h2></div>
    <div class="reading">
{blokken}
    </div>
  </section>

  <section>
    <div class="head-rule"><h2>The details change everything</h2></div>
    <ul class="gids-vragen">
{vragen}    </ul>
{cta}  </section>

{faqblok}{verwant}""".format(
        titel=_e(d["title"]),
        ondertitel=_e(d.get("subtitle", "What could it mean?")),
        hero=('  <img class="gids-hero" src="{}" alt="{}">\n'.format(
                  _e(d["image"]), _e(d.get("alt", d["title"])))
              if d.get("image") else ""),
        vera=_e(d.get("vera", "")),
        intro=_e(d.get("intro", "")),
        blokken="\n".join(blokken),
        vragen=vragen,
        cta=_uitnodiging(d.get("cta", "Tell Vera what actually happened."),
                         "Interpret my dream"),
        faqblok=('  <section>\n    <div class="head-rule">'
                 '<h2>Frequently asked questions</h2></div>\n'
                 '    <div class="gids-faq">\n{}    </div>\n  </section>\n'.format(faq)
                 if faq else ""),
        verwant=verwant)

    return (KOP.format(
        titel=_e(d.get("seo_title", d["title"] + " — What Could It Mean? | Dreamverse")),
        beschrijving=_e(d.get("meta", "")),
        canoniek=SITE + BASIS + "/" + _e(d["slug"]),
        ogbeeld=('<meta property="og:image" content="{}{}">'.format(SITE, _e(d["image"]))
                 if d.get("image") else ""),
        schema=_schema_artikel(d),
        terug_href=BASIS + "/", terug_tekst="All dream meanings")
        + body + VOET.format(basis=BASIS))


# --------------------------------------------------------------------------- #
# Wat Google eruit leest
# --------------------------------------------------------------------------- #

def _json_ld(data):
    # </script> in een tekst zou het blok afbreken; json.dumps ontsnapt dat niet.
    ruw = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return '<script type="application/ld+json">{}</script>'.format(ruw)


def _schema_artikel(d):
    """Article plus FAQPage. De FAQ is wat Google uitklapt in de zoekresultaten."""
    stukken = [{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": d.get("seo_title") or d["title"],
        "description": d.get("meta", ""),
        "mainEntityOfPage": SITE + BASIS + "/" + d["slug"],
        "author": {"@type": "Organization", "name": "Dreamverse"},
        "publisher": {"@type": "Organization", "name": "Dreamverse"},
    }]
    if d.get("image"):
        stukken[0]["image"] = SITE + d["image"]
    if d.get("faq"):
        stukken.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": x.get("q", ""),
                 "acceptedAnswer": {"@type": "Answer", "text": x.get("a", "")}}
                for x in d["faq"]],
        })
    return "\n".join(_json_ld(s) for s in stukken)


def _schema_lijst(lijst):
    return _json_ld({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Vera's Dream Guide",
        "url": SITE + BASIS + "/",
        "hasPart": [{"@type": "Article", "headline": d["title"],
                     "url": SITE + BASIS + "/" + d["slug"]} for d in lijst],
    })


def sitemap():
    """Alle adressen die Google mag kennen, inclusief de vaste pagina's."""
    adressen = [SITE + "/", SITE + "/welkom.html", SITE + "/privacy.html",
                SITE + BASIS + "/"]
    adressen += [SITE + BASIS + "/" + d["slug"] for d in onderwerpen()]
    regels = "".join("  <url><loc>{}</loc></url>\n".format(_e(a)) for a in adressen)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + regels + "</urlset>\n")


def robots():
    return "User-agent: *\nAllow: /\nSitemap: {}/sitemap.xml\n".format(SITE)
