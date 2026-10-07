"""The pages of the site but the reading pages: the shell of every page (render), the home page,
the page of each poster, category and series, the about page and the print guide."""
import html, json, re
from typing import NamedTuple
from urllib.parse import urlsplit

import markdown
from build import substitute
from papers import CATEGORIES, MIN_BODY, PDF_URL, PRINT_SIZES, ROOT, SHOWCASE
from readme import pending, year_key, year_text
from themes import FORMATS, THEMES, US_FORMATS, dark as theme_is_dark
from .common import (ANALYTICS, A_SIZES, BASE_URL, GENESIS_HASH, NAME, PREVIEW_WIDTHS, RELEASE_URL, REPO, SMALL_W,
                     SiteError, THUMB_H, TOKENS, US_NAMES, US_ZIP_URL, WEB, ZIP_URL, alt, by_line, download_event, esc,
                     format_name, hexcolour, lang_of, mark_svg, number, pdf_file, pdf_url, pdf_version, poster_facts,
                     size_text, title, wall_pdf_url)
from .content import load_see_also
from .images import SMALL_H
from .assets import PRELOAD

# The wallpapers that a poster page draws in the browser: name, width and height in pixels
WALLPAPERS = (("Phone", 1170, 2532), ("Desktop", 2560, 1440), ("4K", 3840, 2160))

def srcset(previews, p, theme, root):
    return ", ".join(f"{root}{previews[p.slug, theme][w]} {w}w" for w in PREVIEW_WIDTHS)

def picture(previews, p, root, sizes, eager=False, alt_text=None):
    """A preview in the theme of the mode of the site: the <source> takes over in the dark mode,
    of the system or, with site.js, of the theme button. Its alt says what the poster looks like,
    unless alt_text is given ("" where the title that follows says it all)."""
    src = f"{root}{previews[p.slug, p.light][600]}"
    source = (f'<source data-dark media="(prefers-color-scheme: dark)" srcset="{srcset(previews, p, p.dark, root)}" '
              f'sizes="{sizes}">' if p.dark != p.light else "")
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<picture>{source}<img src="{src}" srcset="{srcset(previews, p, p.light, root)}" sizes="{sizes}" '
            f'width="600" height="{THUMB_H}" alt="{esc(alt(p)) if alt_text is None else alt_text}" {load}></picture>')

CARD_SIZES = "(min-width: 1200px) 260px, (min-width: 768px) 28vw, 44vw"
MINI_SIZES = "(min-width: 1200px) 200px, (min-width: 768px) 26vw, 44vw"

def card(previews, p, root, mini=False, extras=None, level=3):
    """A poster in a list of cards: its preview, whose alt is empty since its title follows, then its
    category, title, authors and year, and on a full card its summary, its Print from and what the
    site adds to it (extras: {slug: Extras}), which the search of the home page reads too."""
    m = p.meta
    x = (extras or {}).get(p.slug)
    adds = [name for name, there in (("Annotated text", x and x.annotations), ("Teaching kit", x and x.teaching))
            if there]
    extra = "" if mini else (f'<p class="sum">{esc(m["summary"])}</p>\n<p class="print">Print from {m["min_print"]}</p>\n'
                             + (f'<p class="adds">{" · ".join(adds)}</p>\n' if adds else ""))
    return (f'<li class="card" data-category="{p.category}">\n'
            f'<div class="mat">{picture(previews, p, root, MINI_SIZES if mini else CARD_SIZES, alt_text="")}</div>\n'
            f'<div class="cartel">\n<p class="eyebrow">{esc(CATEGORIES[p.category])}</p>\n'
            f'<h{level} class="card-title"><a href="{root}{p.slug}/"{lang_of(m)}>{title(m["title"])}</a></h{level}>\n'
            f'<p class="by">{by_line(m)}</p>\n{extra}</div>\n</li>')

def neighbours(p, posters, n=5):
    """The posters shown under a poster: first the others of its category, then one of each
    following category in turn."""
    same = [q for q in posters if q.category == p.category and q is not p]
    order = list(CATEGORIES)
    start = order.index(p.category)
    queues = [[q for q in posters if q.category == c] for c in order[start + 1:] + order[:start]]
    others = []
    while any(queues) and len(same) + len(others) < n:
        for q in queues:
            if q:
                others.append(q.pop(0))
    return (same + others)[:n]

def small_picture(thumbs, p, root, alt_text):
    """A small preview of a series card, in the theme of the mode of the site."""
    source = (f'<source data-dark media="(prefers-color-scheme: dark)" srcset="{root}{thumbs[p.slug, p.dark]}">'
              if p.dark != p.light else "")
    return (f'<picture>{source}<img src="{root}{thumbs[p.slug, p.light]}" width="{SMALL_W}" height="{SMALL_H}" '
            f'alt="{alt_text}" loading="lazy" decoding="async"></picture>')

def years_span(posters):
    years = sorted((p.meta["year"] for p in posters), key=year_key)
    first, last = year_text(years[0]), year_text(years[-1])
    return first if first == last else f"{first} to {last}"

def series_meta(s):
    return f"{len(s.posters)} posters · {esc(years_span(s.posters))}"

def series_strip(s, thumbs, root):
    """The posters of a series side by side, small, on a strip of wall."""
    return ('<div class="strip">' + "".join(
        f'<div class="mat">{small_picture(thumbs, p, root, esc(p.meta["title"]))}</div>' for p in s.posters)
        + "</div>")

def series_card(s, thumbs, root, intro=False, level=3):
    extra = f'<p class="scard-intro">{esc(s.intro)}</p>\n' if intro else ""
    return (f'<li class="scard">\n{series_strip(s, thumbs, root)}\n<div class="cartel">\n'
            f'<p class="eyebrow">{series_meta(s)}</p>\n'
            f'<h{level} class="card-title"><a href="{root}series/{s.slug}/">{title(s.title)}</a></h{level}>\n'
            f'{extra}</div>\n</li>')

def series_links(p, series, root):
    """The series of a poster, as the links of its page."""
    mine = [s for s in series if any(q.slug == p.slug for q in s.posters)]
    if not mine:
        return ""
    links = [f'<a href="{root}series/{s.slug}/">{title(s.title)}</a>' for s in mine]
    both = links[0] if len(links) == 1 else ", ".join(links[:-1]) + " and " + links[-1]
    return f'<p class="in-series">Part of the series {both}.</p>\n'

class Page(NamedTuple):
    path: str          # in the site, such as bitcoin/index.html
    title: str         # of the <title>, escaped
    description: str   # escaped
    main: str
    image: str = ""    # site path of the Open Graph image
    current: str = ""  # "collection", "series" or "about": the link of the menu marked as the current page
    image_alt: str = ""
    head: str = ""     # more elements for the <head>, such as the stylesheet of KaTeX
    ld: tuple = ()     # schema.org objects, written as JSON-LD for search engines

SUN = ('<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" '
       'r="4.2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M12 2.6v2.3M12 19.1v2.3M2.6 12h2.3M19.1 '
       '12h2.3M5.35 5.35 7 7M17 17l1.65 1.65M5.35 18.65 7 17M17 7l1.65-1.65" stroke="currentColor" stroke-width="1.5" '
       'stroke-linecap="round"/></svg>')
BURGER = ('<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path class="open" '
          'd="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path '
          'class="close" d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>')
# 404.html is served for every missing path of the site, at any depth: its links resolve against
# the root of the site on GitHub Pages, and against / when it is opened from `make serve`
BASE_PATH = urlsplit(BASE_URL).path
NOT_FOUND_BASE = (f'<base href="{BASE_PATH}">\n<script>if(location.pathname.indexOf("{BASE_PATH}")!==0)'
                  'document.querySelector("base").href="/"</script>\n')

def json_ld(o):
    data = json.dumps({"@context": "https://schema.org", **o}, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + data.replace("</", "<\\/") + "</script>"

def render(pg, css_v, js_v):
    tpl = (WEB / "page.html").read_text()
    not_found = pg.path == "404.html"
    root = "" if not_found else "../" * pg.path.count("/")
    home = root or "./"
    url = BASE_URL + pg.path.removesuffix("index.html")
    social = []
    if not not_found:
        social.append(f'<link rel="canonical" href="{url}">')
        social += [f'<meta property="og:{k}" content="{v}">' for k, v in
                   (("type", "website"), ("site_name", NAME), ("title", pg.title),
                    ("description", pg.description), ("url", url))]
        if pg.image:
            social += [f'<meta property="og:image" content="{BASE_URL}{pg.image}">',
                       '<meta property="og:image:width" content="1200">',
                       '<meta property="og:image:height" content="630">',
                       f'<meta property="og:image:alt" content="{pg.image_alt}">',
                       '<meta name="twitter:card" content="summary_large_image">']
        social += [json_ld(o) for o in pg.ld]
    else:
        social.append('<meta name="robots" content="noindex">')
    cur = {k: ' aria-current="page"' if pg.current == k else "" for k in ("collection", "series", "about")}
    return substitute(tpl, {
        "BASE": NOT_FOUND_BASE if not_found else "", "MARK": mark_svg(), "TITLE": pg.title, "DESCRIPTION": pg.description,
        "BG_LIGHT": TOKENS["bg"][0], "BG_DARK": TOKENS["bg"][1], "ROOT": root, "HOME": home,
        "PRELOAD": "\n".join(f'<link rel="preload" href="{root}assets/fonts/{f}" as="font" type="font/woff2" '
                             'crossorigin>' for f in PRELOAD),
        "CSS_V": css_v, "JS_V": js_v, "SOCIAL": "\n".join(social), "ANALYTICS": ANALYTICS,
        "SKIP": "" if not_found else '<a class="skip" href="#main">Skip to content</a>',
        "CUR_COLLECTION": cur["collection"], "CUR_SERIES": cur["series"], "CUR_ABOUT": cur["about"], "REPO": REPO,
        "SUN": SUN, "BURGER": BURGER, "MAIN": pg.main, "HASH": GENESIS_HASH,
        "HEAD": pg.head.replace("{{ROOT}}", root)})

# the lede of each category page, which is also the start of its description for search engines
CATEGORY_LEDES = {
    "crypto": "The papers, standards and proposals of modern cryptography and of Bitcoin: the white paper, "
              "the genesis block, SHA-256, AES and the BIPs that shaped wallets and signatures.",
    "computing": "The first texts of computing: Leibniz on binary arithmetic, Ada Lovelace's Note G on the "
                 "Analytical Engine, and the ASCII of RFC 20.",
    "internet": "The Requests for Comments that built the Internet, from RFC 1 to IP and TCP, and the April "
                "Fools' RFCs that made engineers laugh.",
    "software": "The texts that shape how software is written and shared: the GNU Manifesto, the GPL, the Open "
                "Source Definition, the Agile Manifesto, Semantic Versioning and more.",
    "manifestos": "Announcements and declarations of the digital age, such as the first post about the World Wide "
                  "Web and the Declaration of the Independence of Cyberspace.",
    "physics": "Landmark papers of physics and astronomy: Newton's laws of motion, Galileo's Moon, Einstein's "
               "papers of 1905, Planck, Röntgen, Curie, Michelson and Morley, Hubble.",
    "space": "Texts of the space age: Tsiolkovsky's rocket equation, the Apollo 11 landing as it was heard on "
             "the ground and the cover of the Voyager Golden Record.",
    "mathematics": "Founding texts of mathematics: Euclid's Elements, Euler's bridges of Königsberg, Pascal's "
                   "triangle, Fermat, Galois, Riemann, Cantor, Hilbert and Ramanujan.",
    "life-sciences": "Founding texts of biology and medicine: the Hippocratic Oath, Linnaeus, Jenner's vaccine, "
                     "Darwin and Wallace, Mendel's peas and Fleming's penicillin.",
    "data-viz": "The charts and maps that invented data visualization: Halley's winds, Playfair's charts, "
                "Snow's cholera map, Nightingale's rose, Minard's Russian campaign and Mendeleev's table.",
    "patents": "Patents of inventions that changed the world: Lincoln's, Bell's telephone, Edison's lamp, "
               "Tesla's motor, the Wright brothers' flying machine, the transistor and the mouse.",
    "history": "Charters, declarations and speeches that changed history: Magna Carta, the Declaration of "
               "Independence, the rights of man and of woman, Gettysburg, and texts of philosophy.",
    "reference": "Reference sheets to hang by a desk: the ASCII table, the HTTP status codes, the SI base units, "
                 "the phonetic alphabet and Morse code.",
}

# an author of these words is an organization, not a person
ORGANIZATION = re.compile(r"Assembl|Bureau|contributors|Administration|Congress|Convention|Foundation|IANA|Board|NASA|"
                          r"Institute|Council|Committee|Office|Society|Agency")

def agent(name):
    return {"@type": "Organization" if ORGANIZATION.search(name) else "Person", "name": name}

def crumbs_ld(*items):
    """A schema.org BreadcrumbList of (name, site path) items."""
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": name, "item": BASE_URL + path}
        for i, (name, path) in enumerate(items, 1)]}

def category_page(c, posters, previews, extras=None):
    """The page of a category, under /<category>/: its posters, and links to the other categories."""
    mine = [p for p in posters if p.category == c]
    cats = [k for k in CATEGORIES if any(p.category == k for p in posters)]
    span = years_span(mine)
    def link(k):
        current = ' aria-current="page"' if k == c else ""
        return (f'<li><a class="pill" href="../{k}/"{current}>{esc(CATEGORIES[k])} '
                f'<span class="count">{sum(p.category == k for p in posters)}</span></a></li>')
    main = substitute((WEB / "category.html").read_text(), {
        "TITLE": esc(CATEGORIES[c]), "COUNT": esc(f"{len(mine)} posters · {span}"), "LEDE": esc(CATEGORY_LEDES[c]),
        "CARDS": "\n".join(card(previews, p, "../", extras=extras, level=2) for p in mine),
        "OTHERS": "\n".join(link(k) for k in cats)})
    names = ", ".join(p.meta["title"] for p in mine[:3])
    ld = ({"@type": "CollectionPage", "name": f"{CATEGORIES[c]} posters", "url": f"{BASE_URL}{c}/",
           "description": CATEGORY_LEDES[c], "isPartOf": {"@type": "WebSite", "name": NAME, "url": BASE_URL},
           "mainEntity": {"@type": "ItemList", "numberOfItems": len(mine), "itemListElement": [
               {"@type": "ListItem", "position": i, "url": f"{BASE_URL}{p.slug}/", "name": p.meta["title"]}
               for i, p in enumerate(mine, 1)]}},
          crumbs_ld(("Collection", ""), (CATEGORIES[c], f"{c}/")))
    return Page(f"{c}/index.html", f"{esc(CATEGORIES[c])} posters · {NAME}",
                esc(f"{CATEGORY_LEDES[c]} {len(mine)} one-page posters, free vector PDFs to print and frame."),
                main, f"previews/category-{c}-share.jpg", "collection",
                esc(f"Three posters of {CATEGORIES[c]} side by side on a wall: {names}"), ld=ld)

def extras_section(posters, extras):
    """The annotated editions and the teaching kits of the collection, for the home page: empty
    when there are none."""
    notes = [p for p in posters if p.slug in extras and extras[p.slug].annotations]
    kits = [p for p in posters if p.slug in extras and extras[p.slug].teaching]
    if not notes and not kits:
        return ""
    def item(p, href, what):
        return (f'<li><a href="{href}"{lang_of(p.meta)}>{title(p.meta["title"])}</a>\n<span class="by">{by_line(p.meta)}</span>\n'
                f'<span class="what">{what}</span></li>')
    cols = []
    if notes:
        cols.append('<div class="extras-col">\n<h3 class="eyebrow">Annotated editions</h3>\n<ul role="list">\n' + "\n".join(
            item(p, f"{p.slug}/read/", f'{len(extras[p.slug].annotations["notes"])} notes in the margin')
            for p in notes) + "\n</ul>\n</div>")
    if kits:
        cols.append('<div class="extras-col">\n<h3 class="eyebrow">Teaching kits</h3>\n<ul role="list">\n' + "\n".join(
            item(p, f"{p.slug}/teach/", f'{esc(extras[p.slug].teaching["level"])} · '
                                        f'{len(extras[p.slug].teaching["questions"])} questions · A4')
            for p in kits) + "\n</ul>\n</div>")
    intro = (f"{number(len(notes)).capitalize()} texts with notes in the margin, and {number(len(kits))} teaching "
             "kits with their context, a glossary, questions and their answers.")
    return (f'<section id="read-and-teach" class="extras-home wrap" aria-labelledby="extras-title">\n'
            f'<div class="section-head">\n<h2 id="extras-title">Read and teach</h2>\n<p>{esc(intro)}</p>\n</div>\n'
            f'<div class="extras-cols">\n{chr(10).join(cols)}\n</div>\n</section>\n')

def home_page(posters, previews, series, thumbs, extras=None):
    show = next(p for p in posters if p.slug == SHOWCASE)
    m = show.meta
    years = sorted((p.meta["year"] for p in posters), key=year_key)
    cats = [c for c in CATEGORIES if any(p.category == c for p in posters)]
    formats = " · ".join(s.replace(" ", "\u00a0") for s in ["Vector PDF"] + [
        f"{PRINT_SIZES[-1]} to {PRINT_SIZES[0]}" if f == "A" else format_name(f) for f in FORMATS] + [f"{len(THEMES)} themes"])
    # links to the category pages, which site.js turns into filters of the collection
    filters = [f'<a class="pill" href="./#collection" data-filter="" aria-current="true">All '
               f'<span class="count">{len(posters)}</span></a>']
    filters += [f'<a class="pill" href="{c}/" data-filter="{c}">{esc(CATEGORIES[c])} '
                f'<span class="count">{sum(p.category == c for p in posters)}</span></a>' for c in cats]
    featured = (f'<div class="mat">{picture(previews, show, "", "(min-width: 1200px) 360px, (min-width: 768px) 34vw, 86vw", eager=True)}</div>\n'
                f'<figcaption class="cartel"><b>{esc(", ".join(m["authors"]))}</b>\n'
                f'<a href="{show.slug}/"><i{lang_of(m)}>{title(m["title"])}</i></a>\n'
                f'<span class="meta">{esc(year_text(m["year"]))} · {esc(CATEGORIES[show.category])} · '
                f'Print from {m["min_print"]}</span></figcaption>')
    main = substitute((WEB / "home.html").read_text(), {
        "RELEASE": RELEASE_URL, "FORMATS": esc(formats), "FEATURED": featured,
        "INTRO": esc(f"{len(posters)} posters in {len(cats)} categories, from {year_text(years[0])} to "
                     f"{year_text(years[-1])}, each a free PDF to print and frame."),
        "FILTERS": "\n".join(filters), "CARDS": "\n".join(card(previews, p, "", extras=extras) for p in posters),
        "EXTRAS": extras_section(posters, extras or {}),
        "SERIES_INTRO": esc(f"{number(len(series)).capitalize()} sets of posters that hang together, each with a "
                            "planner that draws them on a wall to scale."),
        "SERIES": "\n".join(series_card(s, thumbs, "") for s in series)})
    return Page("index.html", f"{NAME} · Foundational papers, one page each",
                esc("Foundational papers of science, computing and history, each typeset on a single poster. "
                    f"Free vector PDFs to print from {PRINT_SIZES[0]} to {PRINT_SIZES[-1]}, or at "
                    + " or ".join(format_name(f).replace("\u00a0", " ") for f in FORMATS if f != "A") + "."),
                main, "previews/share.jpg", "collection", "Three posters of the collection side by side on a wall",
                ld=({"@type": "WebSite", "name": NAME, "url": BASE_URL,
                     "description": "Foundational papers of science, computing and history, each typeset on a "
                                    "single poster, free to download as vector PDFs."},
                    {"@type": "Organization", "name": NAME, "url": BASE_URL, "logo": BASE_URL + "apple-touch-icon.png",
                     "sameAs": [REPO]}))

def poster_page(p, posters, previews, series, extras=None):
    m, root = p.meta, "../"
    lic, src = m["license"], m["source"]
    both = p.light != p.dark
    shown = (f'<span class="shown if-light">{p.light}</span><span class="shown if-dark">{p.dark}</span>' if both
             else f'<span class="shown">{p.light}</span>')
    pills = [f'<button type="button" class="pill" data-pick="{t}" aria-pressed="false" '
             f'data-srcset="{srcset(previews, p, t, root)}"><span class="swatch" style="--sw:{hexcolour(t, "paper")};'
             f'--sa:{hexcolour(t, "acc")}" aria-hidden="true"></span>{t}</button>' for t in p.themes]
    def row(fmt):
        if fmt == "A":
            note = f'<span class="dl-note">Prints at {", ".join(reversed(PRINT_SIZES[1:]))} or {PRINT_SIZES[0]}</span>'
        else:
            note = f'<span class="dl-note">{US_NAMES[fmt][1]}</span>' if fmt in US_NAMES and US_NAMES[fmt][1] else ""
        links = []
        for t in p.themes:
            cls = "".join((" d-light" if t == p.light else "", " d-dark" if t == p.dark else ""))
            links.append(f'<a class="btn btn-line{cls}" data-t="{t}" href="{pdf_url(p.paper, fmt, t)}" '
                         f'type="application/pdf" {download_event(p.slug, fmt, t)}>PDF · {t} '
                         f'<span class="size">{size_text(pdf_file(p.paper, fmt, t))}</span></a>')
        return (f'<li><div class="dl-what"><span class="dl-name">{format_name(fmt)}</span>{note}</div>'
                f'<div class="dl-links">{"".join(links)}</div></li>')
    rows, us_rows = [row(f) for f in FORMATS], [row(f) for f in US_FORMATS]
    rights = (f'<blockquote><p>{esc(lic["notice"])}</p></blockquote>' if lic.get("notice")
              else f'<p>{esc(lic["basis"])}</p>')
    if lic.get("note"):
        rights += f'\n<p>{esc(lic["note"])}</p>'
    # the size of the screen, which site.js measures and checks, then the common ones
    sizes = ['<label class="pill" hidden><input type="radio" name="wp-size" value="screen" data-screen>This screen '
             '<span class="count"></span></label>']
    sizes += [f'<label class="pill"><input type="radio" name="wp-size" value="{n.lower()}" data-w="{w}" data-h="{h}"'
              f'{" checked" if i == 0 else ""}>{n} <span class="count">{w}\u00a0×\u00a0{h}</span></label>'
              for i, (n, w, h) in enumerate(WALLPAPERS)]
    wthemes = [f'<label class="pill"><input type="radio" name="wp-theme" value="{t}"{" checked" if t == p.light else ""} '
               f'data-paper="{hexcolour(t, "paper")}" data-pdf="{wall_pdf_url(p.paper, t)}"><span class="swatch" '
               f'style="--sw:{hexcolour(t, "paper")};--sa:{hexcolour(t, "acc")}" aria-hidden="true"></span>{t}</label>'
               for t in p.themes]
    main = substitute((WEB / "poster.html").read_text(), {
        "SLUG": p.slug, "WP_SIZES": "\n".join(sizes), "WP_THEMES": "\n".join(wthemes),
        "CATEGORY": p.category, "CATEGORY_TITLE": esc(CATEGORIES[p.category]), "TITLE": esc(m["title"]),
        "TITLE_H1": title(m["title"]), "LANG": m.get("lang", "en"),
        "YEAR": esc(year_text(m["year"])), "AUTHORS": esc(", ".join(m["authors"])),
        "SUBTITLE": f'<p class="subtitle" lang="{m.get("lang", "en")}">{m["kicker"]}</p>' if m.get("kicker") else "",
        "READ_NOTE": "The whole poster as a web page" + (", with notes in the margin"
                                                          if extras and extras.annotations else ""),
        "TEACH": ('<p class="read-link"><a class="btn btn-line" href="teach/">Teaching kit</a> '
                  '<span>Context, glossary, questions and answers, on A4</span></p>\n'
                  if extras and extras.teaching else ""),
        "SUMMARY": esc(m["summary"]), "LIGHT": p.light, "DARK": p.dark, "SERIES": series_links(p, series, root) + "".join(load_see_also().get(p.slug, [])),
        "PICTURE": picture(previews, p, root, "(min-width: 1200px) 480px, (min-width: 768px) 52vw, 86vw", eager=True),
        "SHOWN": shown, "FACTS": poster_facts(m, ("Print from", "License", "Source", "Retrieved", "Language",
                                                    "Rights holder", "Proposed by")),
        "PILLS": "\n".join(pills), "ROWS": "\n".join(rows), "US_ROWS": "\n".join(us_rows),
        "ZIP": ZIP_URL.format(category=p.category), "US_ZIP": US_ZIP_URL.format(category=p.category),
        "PRINT_NOTE": esc(f"Print from {m['min_print']}: the smallest A size at which the body text is at least "
                          f"{MIN_BODY} pt."),
        "EDITION": esc(src["edition"]), "RIGHTS": rights,
        "MORE": "\n".join(card(previews, q, root, mini=True) for q in neighbours(p, posters))})
    return Page(f"{p.slug}/index.html", f"{esc(m['title'])} · {NAME}",
                f"{esc(m['summary'])} A one-page poster, free to download as a vector PDF.", main,
                f"previews/{p.slug}-share.jpg", "", esc(alt(p)),
                ld=({"@type": "CreativeWork", "name": m["title"], "url": f"{BASE_URL}{p.slug}/",
                     "description": m["summary"], "image": f"{BASE_URL}{previews[p.slug, p.light][1200]}",
                     "inLanguage": m.get("lang", "en"), "author": [agent(a) for a in m["authors"]],
                     "isPartOf": {"@type": "WebSite", "name": NAME, "url": BASE_URL}},
                    crumbs_ld(("Collection", ""), (CATEGORIES[p.category], f"{p.category}/"),
                              (m["title"], f"{p.slug}/"))))

HANG_CM = 145  # the centre of a composition, from the floor, as galleries hang

def layout_icon(rows, centred=False):
    """A small drawing of a layout: rows is the number of frames of each row."""
    cols = max(rows)
    w, h = 6 * cols + 2 * (cols - 1), 8 * len(rows) + 2 * (len(rows) - 1)
    rects = []
    for r, k in enumerate(rows):
        x0 = (w - (6 * k + 2 * (k - 1))) / 2 if centred else 0
        rects += [f'<rect x="{x0 + 8 * j:g}" y="{10 * r}" width="6" height="8" rx=".6"/>' for j in range(k)]
    return (f'<svg class="lay" width="{w * 1.4:g}" height="{h * 1.4:g}" viewBox="0 0 {w} {h}" aria-hidden="true" '
            f'focusable="false">{"".join(rects)}</svg>')

def layouts(n):
    """The layouts that the planner offers for n posters: (value, label, rows of the icon)."""
    out = [("row", "One row", [n])]
    out.append(("cols2", "2 columns", [2] * (n // 2) + [1] * (n % 2)))
    if n > 3:
        out.append(("cols3", "3 columns", [3] * (n // 3) + ([n % 3] if n % 3 else [])))
    if n == 5:
        out.append(("3over2", "3 over 2", [3, 2]))
    return out

def default_layout(n):
    return "3over2" if n == 5 else "cols3" if n == 6 else "row"

def radio(name, value, label, checked=False, attrs="", count=""):
    count = f' <span class="count">{count}</span>' if count else ""
    return (f'<label class="pill"><input type="radio" name="{name}" value="{value}"{" checked" if checked else ""}'
            f'{attrs}>{label}{count}</label>')

def cm_text(mm):
    return f"{mm / 10:g}"

def series_page(s, series, previews, thumbs):
    root = "../../"
    n = len(s.posters)
    # formats: the A sizes that the A file prints at, the other formats of dist/, the US formats
    groups = [("ISO A, from the A PDF", [
                  (k, k, w, h, "A", f"{cm_text(w)} × {cm_text(h)}") for k, (w, h) in A_SIZES.items()]),
              ("Frames in centimetres", [
                  (f, format_name(f), *FORMATS[f], f, "") for f in FORMATS if f != "A"]),
              ("US, in inches", [
                  (f, format_name(f), *US_FORMATS[f], f, "") for f in US_FORMATS])]
    fmts = []
    for name, items in groups:
        pills = [radio("pl-format", k, label, k == "A2",
                       f' data-w="{w:g}" data-h="{h:g}" data-file="{f}" data-label="{label}"'
                       f'{" data-us" if f in US_FORMATS else ""}', count)
                 for k, label, w, h, f, count in items]
        fmts.append(f'<div class="pl-group"><p class="pl-glabel">{name}</p><div class="pills">{"".join(pills)}</div></div>')
    lays = [radio("pl-layout", v, layout_icon(rows, v == "3over2") + label, v == default_layout(n))
            for v, label, rows in layouts(n)]
    common = [t for t in THEMES if all(t in p.themes for p in s.posters)]
    if common:
        themes = '<div class="pills">' + "".join(
            radio("pl-theme", t, f'<span class="swatch" style="--sw:{hexcolour(t, "paper")};--sa:{hexcolour(t, "acc")}" '
                  f'aria-hidden="true"></span>{t}', i == 0) for i, t in enumerate(common)) + "</div>"
    else:
        themes = ('<input type="hidden" name="pl-theme" value="">'
                  '<p class="pl-glabel">No theme is common to all these posters: each one is shown in its first theme.</p>')
    # the posters, with every PDF, US formats included (planner.js shows those of the format and
    # theme chosen; without it, those of dist/ in the first theme of each poster show)
    rows = []
    for i, p in enumerate(s.posters, 1):
        m = p.meta
        links = []
        for fmt in [*FORMATS, *US_FORMATS]:
            for t in p.themes:
                cls = " d0" if t == p.light and fmt in FORMATS else ""
                links.append(f'<a class="btn btn-line{cls}" data-f="{fmt}" data-t="{t}" href="{pdf_url(p.paper, fmt, t)}" '
                             f'type="application/pdf" {download_event(p.slug, fmt, t)}>{format_name(fmt)} · {t} '
                             '<span class="size">'
                             f'{size_text(pdf_file(p.paper, fmt, t))}</span></a>')
        srcs = "".join(f' data-src-{t}="{root}{previews[p.slug, t][600]}"' for t in p.themes)
        rows.append(
            f'<li data-slug="{p.slug}" data-min="{m["min_print"]}" data-light="{p.light}" '
            f'data-title="{esc(m["title"])}"{srcs}>\n'
            f'<div class="mat">{small_picture(thumbs, p, root, "")}</div>\n'
            f'<div class="sdl-what">\n<p class="eyebrow">{i} · {esc(CATEGORIES[p.category])}</p>\n'
            f'<h3 class="card-title"><a href="{root}{p.slug}/"{lang_of(m)}>{title(m["title"])}</a></h3>\n'
            f'<p class="by">{by_line(m)}</p>\n<p class="print">Print from {m["min_print"]}</p>\n'
            f'<p class="sdl-warn" hidden></p>\n</div>\n'
            f'<div class="dl-links">{"".join(links)}</div>\n</li>')
    cats = list(dict.fromkeys(p.category for p in s.posters))
    us_zips = []
    for c in cats:
        names = ", ".join(f'<span{lang_of(p.meta)}>{esc(p.meta["title"])}</span>' for p in s.posters if p.category == c)
        us_zips.append(f'<li><a href="{US_ZIP_URL.format(category=c)}">{esc(CATEGORIES[c])}, US formats</a> '
                       f'<span class="size">{c}-us.zip · {names}</span></li>')
    zips = ", ".join(f'<a href="{ZIP_URL.format(category=c)}">{esc(CATEGORIES[c])}</a>' for c in cats)
    others = [o for o in series if o.slug != s.slug]
    note = ("The previews show each poster as laid out for the A formats, stretched to the chosen format; "
            "the PDF of each format is laid out to fill its own page. The figure is 170 cm tall.")
    main = substitute((WEB / "series.html").read_text(), {
        "TITLE": esc(s.title), "TITLE_H1": title(s.title), "META": series_meta(s), "INTRO": esc(s.intro),
        "HANG": HANG_CM, "FORMATS": "\n".join(fmts), "LAYOUTS": "\n".join(lays), "THEMES": themes, "NOTE": esc(note),
        "ROWS": "\n".join(rows), "US_ZIPS": "\n".join(us_zips), "ZIPS": zips,
        "MORE": "\n".join(series_card(o, thumbs, root) for o in others)})
    names = ", ".join(p.meta["title"] for p in s.posters[:3]) + (", ..." if n > 3 else "")
    return Page(f"series/{s.slug}/index.html", f"{esc(s.title)} · Series · {NAME}",
                esc(f"{s.intro} A series of {n} one-page posters, with a planner to hang them together."),
                main, f"previews/series-{s.slug}-share.jpg", "series",
                esc(f"The posters of the series side by side on a wall: {names}"),
                '<script src="{{ROOT}}assets/planner.js?v={planner}" defer></script>\n')

def series_index_page(series, thumbs):
    main = substitute((WEB / "series-index.html").read_text(), {
        "COUNT": f"{len(series)} series",
        "CARDS": "\n".join(series_card(s, thumbs, "../", intro=True, level=2) for s in series)})
    return Page("series/index.html", f"Series · {NAME}",
                esc("Posters of the collection that hang together, each series with a wall planner that draws them "
                    "to scale in the format, layout and frames you choose."),
                main, "previews/share.jpg", "series", "Three posters of the collection side by side on a wall")

def origin():
    """The Origin section of README.md, in HTML. Links are made absolute: a relative one points
    into the repository."""
    text = (ROOT / "README.md").read_text()
    m = re.search(r"^## Origin\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        raise SiteError("README.md has no ## Origin section, which the About page shows")
    body = markdown.render(m.group(1).strip())[0]
    def link(k):
        url = k.group(2)
        if not re.match(r"[a-z]+:", url):
            url = f"{REPO}{url}" if url.startswith("#") else f"{REPO}/blob/master/{url}"
        return f'<a href="{html.escape(url)}">{k.group(1)}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, body)

def about_page(posters, previews):
    show = next(p for p in posters if p.slug == SHOWCASE)
    waiting = pending()
    pend = ""
    if waiting:
        pend = ('<h2>Coming soon</h2>\n<p>Texts that wait for a license allowing their redistribution; '
                f'<a href="{REPO}/blob/master/PENDING.md">PENDING.md</a> says what is missing.</p>\n<ul class="pending">'
                + "".join(f"<li>{esc(t)}</li>" for t in waiting) + "</ul>")
    figure = (f'<div class="mat">{picture(previews, show, "../", "(min-width: 1200px) 360px, 86vw")}</div>\n'
              f'<figcaption class="cartel"><b>{esc(", ".join(show.meta["authors"]))}</b>\n'
              f'<a href="../{show.slug}/"><i{lang_of(show.meta)}>{title(show.meta["title"])}</i></a>\n'
              f'<span class="meta">The poster that started the collection</span></figcaption>')
    main = substitute((WEB / "about.html").read_text(), {
        "ORIGIN": origin(), "REPO": REPO, "PENDING": pend, "FIGURE": figure})
    return Page("about/index.html", f"About · {NAME}",
                esc("Where one-page-papers comes from: the wish to frame the Bitcoin whitepaper, which became an "
                    "engine that typesets foundational texts on one page."),
                main, "previews/share.jpg", "about", "Three posters of the collection side by side on a wall")

def print_page(posters, previews):
    """The guide to having a poster printed, /print/. With ?poster=<slug> (the Print it button of a
    poster page), site.js adds a box for that poster, from the data of #print-data: its Print from,
    its themes and the links to its PDFs, which end with the version of its PDFs (pdf_version)."""
    fmts = [("A", format_name("A").replace(" ", " "))] + [(f, format_name(f)) for f in FORMATS if f != "A"]
    fmts += [(f, format_name(f)) for f in US_FORMATS]  # in release/us/, served from FILES_URL too
    data = {
        "pdf": PDF_URL, "us": US_ZIP_URL, "sizes": list(PRINT_SIZES),
        "formats": [[f, n.replace(" ", " ")] for f, n in fmts],
        "themes": {t: [hexcolour(t, "paper"), hexcolour(t, "acc"), int(theme_is_dark(t))] for t in THEMES},
        # the previews of the box are previews/<slug>-<theme>-600.webp, which make_previews writes
        "posters": {p.slug: [markdown.smart(p.meta["title"]), p.category, p.meta["min_print"], p.themes,
                             pdf_version(p.paper), p.meta.get("lang", "en")]
                    for p in posters if all((p.slug, t) in previews for t in p.themes)}}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    rows = [f'<tr><td>{k}</td><td>{cm_text(w)} × {cm_text(h)}</td><td>The A PDF</td></tr>'
            for k, (w, h) in A_SIZES.items()]
    rows += [f'<tr><td>{format_name(f)}</td><td>{cm_text(w)} × {cm_text(h)}</td><td>Its own PDF</td></tr>'
             for f, (w, h) in FORMATS.items() if f != "A"]
    rows += [f'<tr><td>{format_name(f)}</td><td>{w / 10:.1f} × {h / 10:.1f}</td><td>Its own PDF</td></tr>'
             for f, (w, h) in US_FORMATS.items()]
    main = substitute((WEB / "print.html").read_text(), {
        "NAME": NAME, "DATA": js, "SIZES": "\n".join(rows), "RELEASE": RELEASE_URL})
    return Page("print/index.html", f"Print a poster · {NAME}",
                esc("How to have a poster printed: the size to choose from its Print from and the reading distance, "
                    "paper or white aluminium, which PDF and theme to send, and where to order."),
                main, "previews/share.jpg", "", "Three posters of the collection side by side on a wall")

def not_found_page():
    return Page("404.html", f"Page not found · {NAME}", "This page does not exist.",
                (WEB / "404.html").read_text())
