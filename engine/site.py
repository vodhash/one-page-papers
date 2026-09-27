#!/usr/bin/env python3
"""The showcase site of the collection, for GitHub Pages: static pages written from the
meta.yaml of every paper, with previews rasterized from its A PDFs in dist/.

    python3 engine/site.py                # write site/, after checking it
    python3 engine/site.py --check        # write it into a temporary directory and check it, as CI does
    python3 engine/site.py --only-built   # leave out the papers whose PDFs are not all in dist/ yet
    python3 engine/site.py --contrast     # print the contrast of every text colour of the site

The check fails on a dead internal link (page, image, font, stylesheet, script, anchor), on a
resource loaded from another site, and on a PDF link whose file is not in dist/. Links inside
the site are relative, so that it works under /one-page-papers/ on GitHub Pages as well as at
the root of `make serve`. Previews need pdftoppm (poppler-utils); they are cached in
build/site-previews/, keyed on the content of each PDF, so an unchanged collection builds fast.
"""
import argparse, concurrent.futures, datetime, hashlib, html, io, os, pathlib, re, shutil, subprocess, sys, tempfile, time
from html.parser import HTMLParser
from typing import NamedTuple
from urllib.parse import unquote, urljoin, urlsplit

import yaml
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import markdown
from build import MIN_BODY, PRINT_SIZES, BuildError, load_meta, substitute, themes_of
from papers import CATEGORIES, ROOT, SHOWCASE, Paper, discover
from readme import pending, year_key, year_text
from themes import FORMATS, THEMES, colour

REPO = "https://github.com/vodhash/one-page-papers"
BASE_URL = "https://vodhash.github.io/one-page-papers/"  # only for canonical, Open Graph and sitemap URLs
# Where the PDF buttons point: the files of dist/ on master, so that a link works as soon as a
# poster is pushed. For the assets of the latest release instead, which only has the posters
# of the last tag: REPO + "/releases/latest/download/{file}"
PDF_URL = REPO + "/raw/master/dist/{category}/{file}"
ZIP_URL = REPO + "/releases/latest/download/{category}.zip"  # the zips only exist in releases
RELEASE_URL = REPO + "/releases/latest"
GENESIS_HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"  # of the Bitcoin block 0

WEB = ROOT / "engine" / "web"
CACHE = ROOT / "build" / "site-previews"
PREVIEW_WIDTHS = (600, 1200)
PREVIEW_VERSION = 2  # part of the cache key: bump it when the rendering of the previews changes
A_W, A_H = FORMATS["A"]
THUMB_H = round(600 * A_H / A_W)  # height of the 600 px preview, the size stated in the pages
# family: the @fontsource package, its CSS files that declare the faces, and the characters it
# draws (None: any text of the site); a face is kept in every subset that covers one of them
FONTS = {
    "EB Garamond": ("eb-garamond", ("400", "400-italic", "500", "500-italic", "600", "600-italic"), None),
    "JetBrains Mono": ("jetbrains-mono", ("400",), GENESIS_HASH),
}
PRELOAD = ("eb-garamond-latin-400-normal.woff2", "eb-garamond-latin-500-normal.woff2")

# Colours of the site, light (the ivory theme) and dark (genesis). acc is only for decoration;
# every text colour keeps a contrast of 4.5:1 on every surface, which `--check` verifies.
TOKENS = {
    "bg":      ("#f6f1e6", "#121110"),  # background
    "ink":     ("#1d1b17", "#ece6d8"),  # main text
    "ink2":    ("#3b362f", "#cfc7b8"),  # secondary running text
    "mute":    ("#655e54", "#a39b8c"),  # captions, metadata
    "acc":     ("#e0800d", "#f7931a"),  # decoration only (dots)
    "accText": ("#9a5306", "#f7a445"),  # links, overlines
    "rule":    ("#d9cfbd", "#34302b"),  # rules
    "frame":   ("#fbf8f1", "#1c1a18"),  # passe-partout of the previews
    "wall":    ("#ebe3d2", "#2a2622"),  # panel of the poster page
}
TEXT_TOKENS, SURFACES, MIN_CONTRAST = ("ink", "ink2", "mute", "accText"), ("bg", "frame", "wall"), 4.5
EXTRA_TOKENS = {  # not colours of text or surfaces: the shadow of a passe-partout, the edge of a poster
    "shadow": ("0 1px 2px rgba(29,27,23,.08),0 14px 30px -14px rgba(29,27,23,.34)",
               "0 1px 2px rgba(0,0,0,.5),0 16px 34px -14px rgba(0,0,0,.8)"),
    "edge": ("rgba(29,27,23,.09)", "rgba(236,230,216,.07)"),
}
LANGUAGES = {"en": "English", "de": "German", "fr": "French", "la": "Latin", "el": "Greek",
             "it": "Italian", "es": "Spanish", "nl": "Dutch", "pt": "Portuguese", "ru": "Russian"}
NUMBERS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")

class SiteError(Exception):
    pass

class Poster(NamedTuple):
    paper: Paper
    meta: dict
    themes: list  # the themes of the paper, in the order of THEMES: the first one is its default
    light: str    # the theme of its previews when the site is light: its default
    dark: str     # when the site is dark: genesis when the paper has it, else ivory, else its default

    @property
    def slug(self):
        return self.paper.slug

    @property
    def category(self):
        return self.paper.category

def pdf_file(p, fmt, theme):
    return ROOT / "dist" / p.category / f"{p.slug}-{fmt}-{theme}.pdf"

def pdf_url(p, fmt, theme):
    f = pdf_file(p, fmt, theme)
    return PDF_URL.format(category=f.parent.name, file=f.name)

def collect(only_built):
    """The posters of the site, in the order of the catalog of the README, and the papers left
    out. A paper whose meta.yaml is invalid or whose PDFs are not all in dist/ is an error, or
    is left out with only_built."""
    try:
        papers = discover()
    except ValueError as e:
        raise SiteError(e) from None
    posters, errors, skipped = [], [], []
    for p in papers:
        where = f"papers/{p.category}/{p.slug}"
        try:
            m = load_meta(p.dir)
        except BuildError as e:
            (skipped if only_built else errors).append(str(e))
            continue
        except yaml.YAMLError as e:  # such as a meta.yaml being written
            (skipped if only_built else errors).append(f"{where}/meta.yaml: {' '.join(str(e).split())}")
            continue
        themes = themes_of(m)
        missing = [f.name for f in (pdf_file(p, fmt, t) for fmt in FORMATS for t in themes) if not f.exists()]
        if missing:
            (skipped if only_built else errors).append(
                f"{where}: {len(missing)} of its {len(FORMATS) * len(themes)} PDFs are not in dist/{p.category}/ "
                f"({', '.join(missing[:2])}{', ...' if len(missing) > 2 else ''}), run `make {p.slug}`")
            continue
        dark = next((t for t in ("genesis", "ivory") if t in themes), themes[0])
        posters.append(Poster(p, m, themes, themes[0], dark))
    if errors:
        raise SiteError("\nerror: ".join(errors) + "\n--only-built leaves these papers out of the site")
    if not any(p.slug == SHOWCASE for p in posters):
        raise SiteError(f"the paper {SHOWCASE}, shown at the top of the home page, is missing or left out")
    order = list(CATEGORIES)
    posters.sort(key=lambda p: (order.index(p.category), year_key(p.meta["year"]), p.meta["title"]))
    return posters, skipped

# ---------------------------------------------------------------- previews

def pdftoppm():
    path = shutil.which("pdftoppm")
    if not path:
        raise SiteError("pdftoppm is missing, install poppler-utils (apt install poppler-utils)")
    return path

def save_atomic(path, data):
    """Writes a file of the cache so that a concurrent run never reads it half written."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}")
    tmp.write_bytes(data)
    os.replace(tmp, path)

def webp(im):
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=72, method=6)  # the same to the eye as 80 on these pages of text, and 20% lighter
    return buf.getvalue()

def rasterize(pdf):
    """The WebP previews of the page of an A PDF, {width: path in the cache}: poppler draws it
    1200 px wide, Pillow reduces it to 600."""
    key = f"{hashlib.sha256(pdf.read_bytes()).hexdigest()[:24]}-v{PREVIEW_VERSION}"
    paths = {w: CACHE / f"{key}-{w}.webp" for w in PREVIEW_WIDTHS}
    if all(p.exists() for p in paths.values()):
        return paths
    r = subprocess.run([pdftoppm(), "-singlefile", "-scale-to-x", str(max(PREVIEW_WIDTHS)), "-scale-to-y", "-1",
                        str(pdf)], capture_output=True)
    if r.returncode:
        raise SiteError(f"{pdf.relative_to(ROOT)}: pdftoppm failed: {r.stderr.decode(errors='replace').strip()}")
    big = Image.open(io.BytesIO(r.stdout)).convert("RGB")
    for w, path in paths.items():
        im = big if w == big.width else big.resize((w, round(w * A_H / A_W)), Image.LANCZOS)
        save_atomic(path, webp(im))
    return paths

def matted(im, height, pad):
    """A preview reduced to a height, in its passe-partout (light frame colour)."""
    im = im.resize((round(height * im.width / im.height), height), Image.LANCZOS)
    mat = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), TOKENS["frame"][0])
    mat.paste(im, (pad, pad))
    return mat

def share_image(sources):
    """The Open Graph image, 1200 x 630: the posters side by side on the wall, each in its
    passe-partout with a soft shadow, as on the site. sources are 1200 px WebP previews."""
    key = hashlib.sha256(b"".join(s.read_bytes() for s in sources) + f"v{PREVIEW_VERSION}".encode()).hexdigest()[:24]
    path = CACHE / f"share-{key}.jpg"
    if path.exists():
        return path
    W, H = 1200, 630
    height = 500 if len(sources) == 1 else 430
    mats = [matted(Image.open(s).convert("RGB"), height, 14) for s in sources]
    gap = 56
    x = (W - sum(m.width for m in mats) - gap * (len(mats) - 1)) // 2
    canvas = Image.new("RGB", (W, H), TOKENS["wall"][0])
    shadow = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(shadow)
    boxes = []
    for m in mats:
        y = (H - m.height) // 2
        boxes.append((x, y))
        draw.rectangle((x + 6, y + 16, x + m.width - 6, y + m.height + 10), fill=120)
        x += m.width + gap
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.paste(Image.new("RGB", (W, H), "#3a3226"), (0, 0), shadow)
    for m, (x, y) in zip(mats, boxes):
        canvas.paste(m, (x, y))
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=86, optimize=True, progressive=True)
    save_atomic(path, buf.getvalue())
    return path

def prune(used):
    """Removes the files of the cache that this run did not use, such as the previews of a PDF
    since rebuilt, once they are a day old: a run that is going on at the same time keeps its own."""
    for f in CACHE.iterdir():
        if f not in used and time.time() - f.stat().st_mtime > 86400:
            f.unlink(missing_ok=True)

def make_previews(out, posters):
    """Writes out/previews/: <slug>-<theme>-<width>.webp for every theme of every poster, from
    the cache or rasterized in parallel. Returns {(slug, theme): {width: path in the site}}."""
    CACHE.mkdir(parents=True, exist_ok=True)
    (out / "previews").mkdir(parents=True)
    jobs = [(p, t) for p in posters for t in p.themes]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(16, os.cpu_count() or 2)) as ex:
        done = list(ex.map(lambda job: rasterize(pdf_file(job[0].paper, "A", job[1])), jobs))
    previews = {}
    for (p, t), paths in zip(jobs, done):
        previews[p.slug, t] = {}
        for w, src in paths.items():
            dst = f"previews/{p.slug}-{t}-{w}.webp"
            shutil.copyfile(src, out / dst)
            previews[p.slug, t][w] = dst
    return previews, {(q.slug, t): paths for (q, t), paths in zip(jobs, done)}

# ---------------------------------------------------------------- text helpers

def esc(s):
    """Plain text for HTML, text or attribute, with the typographic quotes of the posters."""
    return html.escape(markdown.smart(str(s)))

def title(s):
    """A title for HTML, whose hyphenated words (Peer-to-Peer) are not broken across lines."""
    return re.sub(r"\S*\w-\w\S*", lambda k: f'<span class="nw">{k.group()}</span>', esc(s))

def hexcolour(theme, name):
    return "#" + "".join(f"{round(c * 255):02x}" for c in colour(theme, name))

def date_text(d):
    if isinstance(d, str):
        d = datetime.date.fromisoformat(d)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"

def size_text(path):
    n = path.stat().st_size
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{max(1, round(n / 1e3))} KB"

def number(n):
    return NUMBERS[n] if n < len(NUMBERS) else str(n)

def authors_short(m):
    names = m["authors"]
    return ", ".join(names) if len(names) <= 3 else f"{names[0]} and {len(names) - 1} others"

def by_line(m):
    return f"{esc(authors_short(m))}, {esc(year_text(m['year']))}"

def format_name(fmt):
    w, h = FORMATS[fmt]
    return "A series" if fmt == "A" else f"{w / 10:g}\u00a0×\u00a0{h / 10:g}\u00a0cm"  # on one line

def alt(p):
    """What a preview shows: the title, and how the page is laid out (as build.py lays it out)."""
    m = p.meta
    layout = m.get("layout", "columns")
    cols = m.get("columns", 1 if layout == "centered" else 4)
    if layout == "hero":
        how = f"a large image at the top, the text in {number(cols)} columns below"
    elif cols == 1:
        how = "the text centered on the page"
    else:
        how = f"the text in {number(cols)} columns"
    return f"Poster of “{markdown.smart(m['title'])}”: {how}"

# ---------------------------------------------------------------- fragments

def srcset(previews, p, theme, root):
    return ", ".join(f"{root}{previews[p.slug, theme][w]} {w}w" for w in PREVIEW_WIDTHS)

def picture(previews, p, root, sizes, eager=False):
    """A preview in the theme of the mode of the site: the <source> takes over in the dark mode,
    of the system or, with site.js, of the theme button."""
    src = f"{root}{previews[p.slug, p.light][600]}"
    source = (f'<source data-dark media="(prefers-color-scheme: dark)" srcset="{srcset(previews, p, p.dark, root)}" '
              f'sizes="{sizes}">' if p.dark != p.light else "")
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<picture>{source}<img src="{src}" srcset="{srcset(previews, p, p.light, root)}" sizes="{sizes}" '
            f'width="600" height="{THUMB_H}" alt="{esc(alt(p))}" {load}></picture>')

CARD_SIZES = "(min-width: 1200px) 260px, (min-width: 768px) 28vw, 44vw"
MINI_SIZES = "(min-width: 1200px) 200px, (min-width: 768px) 26vw, 44vw"

def card(previews, p, root, mini=False):
    m = p.meta
    extra = "" if mini else f'<p class="sum">{esc(m["summary"])}</p>\n<p class="print">Print from {m["min_print"]}</p>\n'
    return (f'<li class="card" data-category="{p.category}">\n'
            f'<div class="mat">{picture(previews, p, root, MINI_SIZES if mini else CARD_SIZES)}</div>\n'
            f'<div class="cartel">\n<p class="eyebrow">{esc(CATEGORIES[p.category])}</p>\n'
            f'<h3 class="card-title"><a href="{root}{p.slug}/">{title(m["title"])}</a></h3>\n'
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

# ---------------------------------------------------------------- pages

class Page(NamedTuple):
    path: str          # in the site, such as bitcoin/index.html
    title: str         # of the <title>, escaped
    description: str   # escaped
    main: str
    image: str = ""    # site path of the Open Graph image
    current: str = ""  # "collection" or "about": the link of the menu marked as the current page
    image_alt: str = ""

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
                   (("type", "website"), ("site_name", "one-page-papers"), ("title", pg.title),
                    ("description", pg.description), ("url", url))]
        if pg.image:
            social += [f'<meta property="og:image" content="{BASE_URL}{pg.image}">',
                       '<meta property="og:image:width" content="1200">',
                       '<meta property="og:image:height" content="630">',
                       f'<meta property="og:image:alt" content="{pg.image_alt}">',
                       '<meta name="twitter:card" content="summary_large_image">']
    else:
        social.append('<meta name="robots" content="noindex">')
    cur = {k: ' aria-current="page"' if pg.current == k else "" for k in ("collection", "about")}
    return substitute(tpl, {
        "BASE": NOT_FOUND_BASE if not_found else "", "TITLE": pg.title, "DESCRIPTION": pg.description,
        "BG_LIGHT": TOKENS["bg"][0], "BG_DARK": TOKENS["bg"][1], "ROOT": root, "HOME": home,
        "PRELOAD": "\n".join(f'<link rel="preload" href="{root}assets/fonts/{f}" as="font" type="font/woff2" '
                             'crossorigin>' for f in PRELOAD),
        "CSS_V": css_v, "JS_V": js_v, "SOCIAL": "\n".join(social),
        "SKIP": "" if not_found else '<a class="skip" href="#main">Skip to content</a>',
        "CUR_COLLECTION": cur["collection"], "CUR_ABOUT": cur["about"], "REPO": REPO,
        "SUN": SUN, "BURGER": BURGER, "MAIN": pg.main, "HASH": GENESIS_HASH})

def home_page(posters, previews):
    show = next(p for p in posters if p.slug == SHOWCASE)
    m = show.meta
    years = sorted((p.meta["year"] for p in posters), key=year_key)
    cats = [c for c in CATEGORIES if any(p.category == c for p in posters)]
    formats = " · ".join(s.replace(" ", "\u00a0") for s in ["Vector PDF"] + [
        f"{PRINT_SIZES[-1]} to {PRINT_SIZES[0]}" if f == "A" else format_name(f) for f in FORMATS] + [f"{len(THEMES)} themes"])
    filters = [f'<button type="button" class="pill" data-filter="" aria-pressed="true">All '
               f'<span class="count">{len(posters)}</span></button>']
    filters += [f'<button type="button" class="pill" data-filter="{c}" aria-pressed="false">{esc(CATEGORIES[c])} '
                f'<span class="count">{sum(p.category == c for p in posters)}</span></button>' for c in cats]
    featured = (f'<div class="mat">{picture(previews, show, "", "(min-width: 1200px) 360px, (min-width: 768px) 34vw, 86vw", eager=True)}</div>\n'
                f'<figcaption class="cartel"><b>{esc(", ".join(m["authors"]))}</b>\n'
                f'<a href="{show.slug}/"><i>{title(m["title"])}</i></a>\n'
                f'<span class="meta">{esc(year_text(m["year"]))} · {esc(CATEGORIES[show.category])} · '
                f'Print from {m["min_print"]}</span></figcaption>')
    main = substitute((WEB / "home.html").read_text(), {
        "RELEASE": RELEASE_URL, "FORMATS": esc(formats), "FEATURED": featured,
        "INTRO": esc(f"{len(posters)} posters in {len(cats)} categories, from {year_text(years[0])} to "
                     f"{year_text(years[-1])}, each a free PDF to print and frame."),
        "FILTERS": "\n".join(filters), "CARDS": "\n".join(card(previews, p, "") for p in posters)})
    return Page("index.html", "one-page-papers: foundational papers, one page each",
                esc("Foundational papers of science, computing and history, each typeset on a single poster. "
                    f"Free vector PDFs to print from {PRINT_SIZES[0]} to {PRINT_SIZES[-1]}, or at "
                    + " or ".join(format_name(f).replace("\u00a0", " ") for f in FORMATS if f != "A") + "."),
                main, "previews/share.jpg", "collection", "Three posters of the collection side by side on a wall")

def poster_page(p, posters, previews):
    m, root = p.meta, "../"
    lic, src = m["license"], m["source"]
    host = urlsplit(src["url"]).netloc.removeprefix("www.")
    facts = [("Print from", m["min_print"]), ("License", esc(lic["text"])),
             ("Source", f'<a href="{html.escape(src["url"])}">{esc(host)}</a>'),
             ("Retrieved", date_text(src["retrieved"])),
             ("Language", LANGUAGES.get(m.get("lang", "en"), m.get("lang", "en")))]
    if lic.get("holder"):
        facts.append(("Rights holder", esc(lic["holder"])))
    both = p.light != p.dark
    shown = (f'<span class="shown if-light">{p.light}</span><span class="shown if-dark">{p.dark}</span>' if both
             else f'<span class="shown">{p.light}</span>')
    pills = [f'<button type="button" class="pill" data-pick="{t}" aria-pressed="false" '
             f'data-srcset="{srcset(previews, p, t, root)}"><span class="swatch" style="--sw:{hexcolour(t, "paper")};'
             f'--sa:{hexcolour(t, "acc")}" aria-hidden="true"></span>{t}</button>' for t in p.themes]
    rows = []
    for fmt in FORMATS:
        note = (f'<span class="dl-note">Prints at {", ".join(reversed(PRINT_SIZES[1:]))} or {PRINT_SIZES[0]}</span>'
                if fmt == "A" else "")
        links = []
        for t in p.themes:
            cls = "".join((" d-light" if t == p.light else "", " d-dark" if t == p.dark else ""))
            links.append(f'<a class="btn btn-line{cls}" data-t="{t}" href="{pdf_url(p.paper, fmt, t)}" '
                         f'type="application/pdf">PDF · {t} <span class="size">{size_text(pdf_file(p.paper, fmt, t))}'
                         '</span></a>')
        rows.append(f'<li><div class="dl-what"><span class="dl-name">{format_name(fmt)}</span>{note}</div>'
                    f'<div class="dl-links">{"".join(links)}</div></li>')
    rights = (f'<blockquote><p>{esc(lic["notice"])}</p></blockquote>' if lic.get("notice")
              else f'<p>{esc(lic["basis"])}</p>')
    if lic.get("note"):
        rights += f'\n<p>{esc(lic["note"])}</p>'
    main = substitute((WEB / "poster.html").read_text(), {
        "CATEGORY": p.category, "CATEGORY_TITLE": esc(CATEGORIES[p.category]), "TITLE": esc(m["title"]),
        "TITLE_H1": title(m["title"]),
        "YEAR": esc(year_text(m["year"])), "AUTHORS": esc(", ".join(m["authors"])),
        "SUBTITLE": f'<p class="subtitle">{m["kicker"]}</p>' if m.get("kicker") else "",
        "SUMMARY": esc(m["summary"]), "LIGHT": p.light, "DARK": p.dark,
        "PICTURE": picture(previews, p, root, "(min-width: 1200px) 480px, (min-width: 768px) 52vw, 86vw", eager=True),
        "SHOWN": shown, "FACTS": "\n".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts),
        "PILLS": "\n".join(pills), "ROWS": "\n".join(rows),
        "ZIP": ZIP_URL.format(category=p.category),
        "PRINT_NOTE": esc(f"Print from {m['min_print']}: the smallest A size at which the body text is at least "
                          f"{MIN_BODY} pt."),
        "EDITION": esc(src["edition"]), "RIGHTS": rights,
        "MORE": "\n".join(card(previews, q, root, mini=True) for q in neighbours(p, posters))})
    return Page(f"{p.slug}/index.html", f"{esc(m['title'])} · one-page-papers",
                f"{esc(m['summary'])} A one-page poster, free to download as a vector PDF.", main,
                f"previews/{p.slug}-share.jpg", "", esc(alt(p)))

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
              f'<a href="../{show.slug}/"><i>{title(show.meta["title"])}</i></a>\n'
              f'<span class="meta">The poster that started the collection</span></figcaption>')
    main = substitute((WEB / "about.html").read_text(), {
        "ORIGIN": origin(), "REPO": REPO, "PENDING": pend, "FIGURE": figure})
    return Page("about/index.html", "About · one-page-papers",
                esc("Where one-page-papers comes from: the wish to frame the Bitcoin whitepaper, which became an "
                    "engine that typesets foundational texts on one page."),
                main, "previews/share.jpg", "about", "Three posters of the collection side by side on a wall")

def not_found_page():
    return Page("404.html", "Page not found · one-page-papers", "This page does not exist.",
                (WEB / "404.html").read_text())

# ---------------------------------------------------------------- fonts and styles

def text_of(page_html):
    """The characters that a page draws with its fonts."""
    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.chars, self.skip = set(), 0
        def handle_starttag(self, tag, attrs):
            self.skip += tag in ("script", "style", "title")
        def handle_endtag(self, tag):
            self.skip -= tag in ("script", "style", "title")
        def handle_data(self, data):
            if not self.skip:
                self.chars.update(data)
    t = Text()
    t.feed(page_html)
    return t.chars

def unicode_ranges(spec):
    out = []
    for part in spec.split(","):
        lo, _, hi = part.strip().removeprefix("U+").partition("-")
        out.append((int(lo, 16), int(hi or lo, 16)))
    return out

def font_faces(chars):
    """@font-face rules of the site and the files they use: every face of FONTS in every
    subset of @fontsource that covers a character of the site."""
    rules, files = [], []
    for family, (package, sheets, only) in FONTS.items():
        drawn = set(only) if only else chars
        base = ROOT / "node_modules" / "@fontsource" / package
        for sheet in sheets:
            path = base / f"{sheet}.css"
            if not path.exists():
                raise SiteError(f"{path.relative_to(ROOT)} is missing, run `make deps`")
            for block in re.findall(r"@font-face\s*{([^}]*)}", path.read_text()):
                style = re.search(r"font-style:\s*(\w+)", block).group(1)
                weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
                woff2 = re.search(r"url\(\./files/([^)]+\.woff2)\)", block).group(1)
                spec = re.search(r"unicode-range:\s*([^;]+);", block).group(1)
                if not any(lo <= ord(c) <= hi for lo, hi in unicode_ranges(spec) for c in drawn):
                    continue
                files.append(base / "files" / woff2)
                rules.append(f"@font-face{{font-family:'{family}';font-style:{style};font-weight:{weight};"
                             f"font-display:swap;src:url(fonts/{woff2}) format('woff2');unicode-range:{spec}}}")
    return rules, files

def mode_css():
    """The colour tokens: light by default, dark when the system asks for it unless the theme
    button chose light, and dark when the theme button chose it."""
    def block(i):
        return ";".join(f"--{k}:{v[i]}" for k, v in {**TOKENS, **EXTRA_TOKENS}.items()) + \
            f";color-scheme:{('light', 'dark')[i]}"
    return (f":root{{{block(0)}}}\n@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{{block(1)}}}}}\n"
            f":root[data-theme=dark]{{{block(1)}}}")

def luminance(hexa):
    rgb = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)

def contrasts():
    """(mode, text token, surface token, ratio) for every text colour on every surface, and the
    filled buttons, whose text is the background on ink."""
    rows = []
    for i, name in enumerate(("light", "dark")):
        rows += [(name, t, s, contrast(TOKENS[t][i], TOKENS[s][i])) for t in TEXT_TOKENS for s in SURFACES]
        rows.append((name, "bg", "ink", contrast(TOKENS["bg"][i], TOKENS["ink"][i])))
    return rows

# ---------------------------------------------------------------- the site

def write(out, posters):
    """Writes the whole site into the empty folder out. Returns a summary."""
    previews, cached = make_previews(out, posters)
    show = next(p for p in posters if p.slug == SHOWCASE)
    # the home page shows three posters: the showcase between the first ones of two other categories
    firsts = [next(q for q in posters if q.category == c) for c in dict.fromkeys(q.category for q in posters)]
    others = [q for q in firsts if q is not show][:2]
    trio = [others[0], show, others[1]] if len(others) == 2 else [show]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(16, os.cpu_count() or 2)) as ex:
        shares = list(ex.map(lambda p: share_image([cached[p.slug, p.light][1200]]), posters))
    for p, f in zip(posters, shares):
        shutil.copyfile(f, out / f"previews/{p.slug}-share.jpg")
    shares.append(share_image([cached[q.slug, q.light][1200] for q in trio]))
    shutil.copyfile(shares[-1], out / "previews/share.jpg")
    prune({f for paths in cached.values() for f in paths.values()} | set(shares))

    pages = [home_page(posters, previews), about_page(posters, previews), not_found_page()]
    pages += [poster_page(p, posters, previews) for p in posters]
    drafts = {pg.path: render(pg, "{css}", "{js}") for pg in pages}
    chars = set().union(*(text_of(h) for h in drafts.values())) | {chr(c) for c in range(0x20, 0x7f)}
    rules, files = font_faces(chars)
    (out / "assets" / "fonts").mkdir(parents=True)
    for f in files:
        shutil.copyfile(f, out / "assets" / "fonts" / f.name)
    css = "\n".join(["/* one-page-papers: written by engine/site.py from engine/web/site.css */",
                     mode_css(), *rules, (WEB / "site.css").read_text()])
    js = (WEB / "site.js").read_text()
    (out / "assets" / "site.css").write_text(css)
    (out / "assets" / "site.js").write_text(js)
    css_v, js_v = (hashlib.sha256(s.encode()).hexdigest()[:10] for s in (css, js))
    for path, h in drafts.items():
        dst = out / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(h.replace("?v={css}", f"?v={css_v}").replace("?v={js}", f"?v={js_v}"))

    light_bg, acc = TOKENS["bg"][0], TOKENS["acc"][0]
    (out / "favicon.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" '
        f'fill="{light_bg}"/><circle cx="32" cy="32" r="13" fill="{acc}"/></svg>\n')
    icon = Image.new("RGB", (720, 720), light_bg)
    ImageDraw.Draw(icon).ellipse((360 - 150, 360 - 150, 360 + 150, 360 + 150), fill=acc)
    icon.resize((180, 180), Image.LANCZOS).save(out / "apple-touch-icon.png", optimize=True)
    urls = [BASE_URL + pg.path.removesuffix("index.html") for pg in pages if pg.path != "404.html"]
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}sitemap.xml\n")
    return f"{len(pages)} pages, {sum(len(v) for v in previews.values())} previews, {len(files)} font files"

# ---------------------------------------------------------------- the check

class Scan(HTMLParser):
    """What the check needs from a page: its ids, <base>, <title> and <h1> count, images
    without alt, and every URL it refers to, as (attribute, URL, whether the browser loads it)."""
    def __init__(self):
        super().__init__()
        self.ids, self.dup, self.refs, self.base = set(), set(), [], None
        self.titles = self.h1 = 0
        self.no_alt = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            (self.dup if a["id"] in self.ids else self.ids).add(a["id"])
        self.titles += tag == "title"
        self.h1 += tag == "h1"
        if tag == "img" and a.get("alt") is None:
            self.no_alt.append(a.get("src"))
        if tag == "base":
            self.base = a.get("href")
            return
        for k, v in attrs:
            if v is None:
                continue
            if k in ("href", "src", "data-src"):
                urls = [v]
            elif k.endswith("srcset"):  # also data-srcset, which site.js loads
                urls = [c.split()[0] for c in v.split(",") if c.strip()]
            elif k == "content" and (a.get("property") in ("og:image", "og:url") or a.get("name") == "twitter:image"):
                urls = [v]
            else:
                continue
            loaded = not (tag == "a" or k == "content" or (tag == "link" and a.get("rel") == "canonical"))
            self.refs += [(f"{tag} {k}", u, loaded) for u in urls]

    handle_startendtag = handle_starttag

def pdf_pattern():
    """PDF_URL as a regular expression, which gives back the category and the file."""
    parts = re.split(r"(\{category\}|\{file\})", PDF_URL)
    group = {"{category}": "(?P<category>[^/?#]+)", "{file}": r"(?P<file>[^/?#]+\.pdf)"}
    return re.compile("".join(group.get(s, re.escape(s)) for s in parts) + "$")

def check(out):
    """Every problem of the site written in out, as messages."""
    site = "https://site.invalid" + BASE_PATH  # where the check places the site to resolve its URLs
    pdf = pdf_pattern()
    pages, errors = {}, []
    for f in sorted(out.rglob("*.html")):
        scan = Scan()
        scan.feed(f.read_text())
        pages[f.relative_to(out).as_posix()] = scan
    refs = [(path, s.base, *r) for path, s in pages.items() for r in s.refs]
    for f in sorted(out.rglob("*.css")):
        rel = f.relative_to(out).as_posix()
        refs += [(rel, None, "url()", u, True) for u in re.findall(r"url\(\s*['\"]?([^'\")]+)", f.read_text())]
    for loc in re.findall(r"<loc>([^<]+)</loc>", (out / "sitemap.xml").read_text()):
        refs.append(("sitemap.xml", None, "loc", loc, False))
    for loc in re.findall(r"^Sitemap: (\S+)", (out / "robots.txt").read_text(), re.M):
        refs.append(("robots.txt", None, "Sitemap", loc, False))

    for path, s in pages.items():
        if s.titles != 1:
            errors.append(f"{path}: {s.titles} <title> elements")
        if s.h1 != 1:
            errors.append(f"{path}: {s.h1} <h1> elements")
        errors += [f"{path}: id {i} used twice" for i in sorted(s.dup)]
        errors += [f"{path}: <img src={src}> has no alt" for src in s.no_alt]
    for path, base, what, url, loaded in refs:
        if url.startswith("data:"):
            continue
        if url.startswith(BASE_URL):
            url = site + url[len(BASE_URL):]
        page_url = urljoin(site + path, base) if base else site + path
        target = urljoin(page_url, url)
        parts = urlsplit(target)
        if target.startswith(site):
            rel = unquote(parts.path)[len(BASE_PATH):]
            file = rel + "index.html" if rel == "" or rel.endswith("/") else rel
            if not (out / file).is_file():
                errors.append(f"{path}: {what} {url}: dead link" + (", add a final /" if (out / rel).is_dir() else ""))
            elif parts.fragment and file.endswith(".html") and parts.fragment not in pages[file].ids:
                errors.append(f"{path}: {what} {url}: no id {parts.fragment} in {file}")
        elif parts.netloc == "site.invalid":
            errors.append(f"{path}: {what} {url}: outside the site, which lives under {BASE_PATH}")
        elif loaded:
            errors.append(f"{path}: {what} {url}: loaded from another site")
        elif k := pdf.match(target):
            where = sorted((ROOT / "dist").glob(f"{k.groupdict().get('category', '*')}/{k['file']}"))
            if len(where) != 1:
                errors.append(f"{path}: {what} {url}: {'no such file' if not where else 'several files'} in dist/")
    errors += [f"contrast of {t} on {s} in the {m} mode: {r:.2f}, below {MIN_CONTRAST}"
               for m, t, s, r in contrasts() if r < MIN_CONTRAST]
    return errors, len(refs)

def main():
    ap = argparse.ArgumentParser(description="Write the showcase site into site/.")
    ap.add_argument("--check", action="store_true",
                    help="write the site into a temporary directory and check it, leaving site/ untouched")
    ap.add_argument("--only-built", action="store_true",
                    help="leave out the papers whose PDFs are not all in dist/, instead of failing")
    ap.add_argument("--contrast", action="store_true",
                    help="print the contrast ratio of every text colour on every surface, then exit")
    a = ap.parse_args()
    if a.contrast:
        for mode, t, s, r in contrasts():
            print(f"{mode:5}  {t:7} on {s:5}  {r:5.2f}:1  {'ok' if r >= MIN_CONTRAST else 'FAILS'}")
        return
    try:
        posters, skipped = collect(a.only_built)
        for msg in skipped:
            print(f"left out: {msg}", file=sys.stderr)
        (ROOT / "build").mkdir(exist_ok=True)
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="site-", dir=ROOT / "build"))
        try:
            summary = write(tmp, posters)
            errors, n = check(tmp)
            for e in errors:
                print(f"error: {e}", file=sys.stderr)
            if errors:
                sys.exit(f"{len(errors)} problem(s) in the site")
            if a.check:
                print(f"site: {summary}; {n} links checked, all good")
            else:
                out = ROOT / "site"
                if out.exists():
                    shutil.rmtree(out)
                tmp.chmod(0o755)  # mkdtemp makes it private
                os.replace(tmp, out)
                print(f"site/: {summary}; {n} links checked, all good")
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)
    except SiteError as e:
        sys.exit(f"error: {e}")

if __name__ == "__main__":
    main()
