"""What every part of the site shares: its addresses, names and colours, the posters as the site
sees them, their PDFs, and the helpers that write text into HTML."""
import datetime, functools, hashlib, html, os, re
from typing import NamedTuple
from urllib.parse import urlsplit

import markdown
from papers import PDF_URL, ROOT, SITE_URL, Paper, pdf_name
from readme import year_text
from themes import FORMATS, THEMES, US_FORMATS, colour

REPO = "https://github.com/vodhash/one-page-papers"
BASE_URL = SITE_URL  # only for canonical, Open Graph and sitemap URLs
# The PDF buttons point to the bucket where the CI uploads the PDFs of dist/ before it deploys the
# site (PDF_URL), so that a link works as soon as its page is online.
# The same files for the wallpapers, which the browser fetches: the bucket answers with the
# Access-Control-Allow-Origin header of the site (its CORS rule, see CONTRIBUTING.md)
WALL_PDF_URL = PDF_URL

ZIP_URL = REPO + "/releases/latest/download/{category}.zip"  # the zips only exist in releases
US_ZIP_URL = REPO + "/releases/latest/download/{category}-us.zip"  # the US formats, which dist/ leaves out
RELEASE_URL = REPO + "/releases/latest"
# Umami, the analytics of the site: no cookie, no personal data. The only resource the site loads
# from another site; data-domains keeps make serve and other hosts out of the counts
ANALYTICS_SRC = "https://umami.onepagepapers.com/script.js"
ANALYTICS = (f'<script defer src="{ANALYTICS_SRC}" data-website-id="3adaa9da-4979-4ea1-931d-e55966529929" '
             'data-domains="onepagepapers.com"></script>')
NAME = "One Page Papers"
def mark_svg(ink="currentColor", acc="var(--acc)", paper="none", size=""):
    """The logo: a poster, as the A format frames it (594 by 841), with its double rule, the emblem
    of its header between two rules, and lines of text."""
    dim = f' width="{size * 60 // 84}" height="{size}"' if size else ""
    text = "".join(f'<path d="M13 {y}h{34 if i % 4 != 3 else 22}"/>' for i, y in enumerate(range(36, 74, 5)))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 84"{dim} aria-hidden="true" fill="none" '
            f'stroke="{ink}" stroke-linecap="round">'
            f'<rect x="2.5" y="2.5" width="55" height="79" rx="1.5" fill="{paper}" stroke-width="3"/>'
            f'<rect x="7" y="7" width="46" height="70" stroke-width="1.2"/>'
            f'<path d="M13 21h10M37 21h10" stroke-width="1.6"/><circle cx="30" cy="21" r="4.6" fill="{acc}" stroke="none"/>'
            f'<g stroke-width="1.6" opacity=".55">{text}</g></svg>')

GENESIS_HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"  # of the Bitcoin block 0

WEB = ROOT / "engine" / "web"
CACHE = ROOT / "build" / "site-previews"
PREVIEW_WIDTHS = (600, 1200)
PREVIEW_VERSION = 2  # part of the cache key: bump it when the rendering of the previews changes
SMALL_W = 160  # px: the small previews of the series cards, reduced from the 600 px ones

# the sizes at which the A file prints (PRINT_SIZES), in mm, for the wall planner
A_SIZES = {"A3": (297, 420), "A2": (420, 594), "A1": (594, 841), "A0": (841, 1189)}
A_W, A_H = FORMATS["A"]
THUMB_H = round(600 * A_H / A_W)  # height of the 600 px preview, the size stated in the pages

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
    "moulding": ("#1d1b17", "#0b0a09"),  # the frames that the wall planner draws around the posters
    # the accent boxes of the figures and the code blocks of the reading pages: those of the ivory
    # and genesis themes, whose colours the site takes
    "boxa": ("#f6dcb4", "#3d2a12"),
    "code": ("#ede5d5", "#1e1c19"),
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

# where build.py writes the PDFs: the formats of dist/, and the US formats in release/us/ (build.py --us)
PDF_DIRS = (ROOT / "dist", ROOT / "release" / "us")

def pdf_file(p, fmt, theme):
    return PDF_DIRS[fmt in US_FORMATS] / p.category / pdf_name(p.slug, fmt, theme)

@functools.cache
def pdf_version(p):
    """The version of the PDFs of a paper, as they are in dist/ and release/us/: the CI uploads them
    before it writes the site. It ends every link to one of them (?v=), which the bucket ignores, so
    that a corrected poster has new links: a browser keeps a PDF a week (upload.CACHE_CONTROL), and a
    purge of the Cloudflare cache does not reach it."""
    h = hashlib.sha256()
    for f in (pdf_file(p, fmt, t) for fmt in [*FORMATS, *US_FORMATS] for t in THEMES):
        if f.exists():
            h.update(f.name.encode() + b"\0" + hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()[:10]

def download_event(slug, fmt, theme):
    """The attributes of a PDF link: it opens in a new tab, and Umami counts a click on it as the
    event download, with its poster, format and theme."""
    return (f'data-umami-event="download" data-umami-event-slug="{slug}" data-umami-event-format="{fmt}" '
            f'data-umami-event-theme="{theme}" target="_blank" rel="noopener"')

def pdf_url(p, fmt, theme):
    f = pdf_file(p, fmt, theme)
    return PDF_URL.format(category=f.parent.name, file=f.name) + f"?v={pdf_version(p)}"

def wall_pdf_url(p, theme):
    f = pdf_file(p, "A", theme)
    return WALL_PDF_URL.format(category=f.parent.name, file=f.name) + f"?v={pdf_version(p)}"

def poster_facts(m, order):
    """The facts of a poster that its page and its reading page list, in the order given, as the
    items of a <dl>: those that the poster lacks (a rights holder, contributors) are left out."""
    lic, src, lang = m["license"], m["source"], m.get("lang", "en")
    host = urlsplit(src["url"]).netloc.removeprefix("www.")
    facts = {"Print from": m["min_print"], "License": esc(lic["text"]),
             "Source": f'<a href="{html.escape(src["url"])}">{esc(host)}</a>',
             "Retrieved": date_text(src["retrieved"]), "Language": LANGUAGES.get(lang, lang)}
    if lic.get("holder"):
        facts["Rights holder"] = esc(lic["holder"])
    if m.get("contributors"):
        facts["Proposed by"] = ", ".join(f'<a href="https://github.com/{h}">@{h}</a>' for h in m["contributors"])
    return "\n".join(f"<div><dt>{k}</dt><dd>{facts[k]}</dd></div>" for k in order if k in facts)

def short(s, n=48):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 3].rstrip() + "..."

def save_atomic(path, data):
    """Writes a file of the cache so that a concurrent run never reads it half written."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}")
    tmp.write_bytes(data)
    os.replace(tmp, path)

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

# the US formats by name, and their size in inches
US_NAMES = {"letter": ("Letter", "8.5 × 11 in"), "tabloid": ("Tabloid", "11 × 17 in"),
            "18x24": ("18 × 24 in", ""), "24x36": ("24 × 36 in", "")}

def format_name(fmt):
    if fmt in US_NAMES:
        return US_NAMES[fmt][0].replace(" ", "\u00a0")
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
