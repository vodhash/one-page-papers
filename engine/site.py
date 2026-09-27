#!/usr/bin/env python3
"""The showcase site of the collection, for GitHub Pages: static pages written from the
meta.yaml of every paper, with previews rasterized from its A PDFs in dist/ (built by build.py, not
kept in git: the PDFs are served from FILES_URL, where the CI uploads them), and a reading page
for each paper (<slug>/read/), its text rendered by markdown.py and KaTeX as for its poster, and a
page for each series of series.yaml (series/<slug>/), with a wall planner (planner.js), and a guide
to having a poster printed (print/).

A paper may also have an annotations.yaml, margin notes shown on its reading page, and a
teaching.yaml, a teaching kit printable on A4 (<slug>/teach/). Both are checked (each anchor occurs
exactly once in text.md, each source is a key of references), but they go on the site only when
they say `published: true`, or with --drafts, for review.

    python3 engine/site.py                # write site/, after checking it
    python3 engine/site.py --check        # write it into a temporary directory and check it, as CI does
    python3 engine/site.py --only-built   # leave out the papers whose PDFs are not all in dist/ yet
    python3 engine/site.py --drafts       # also show the notes and teaching kits not yet published
    python3 engine/site.py --contrast     # print the contrast of every text colour of the site

The check fails on a dead internal link (page, image, font, stylesheet, script, anchor), on a
resource loaded from another site but the analytics script (ANALYTICS) and the PDFs that site.js
fetches to draw a wallpaper (WALL_PDF_URL), on a PDF link whose file is not in dist/, and on a link
to a generated file through the repository (GENERATED_IN_REPO), which git does not keep. Links inside
the site are relative, so that it works at https://onepagepapers.com/ (GitHub Pages) as well as at
the root of `make serve`. Previews need pdftoppm (poppler-utils); they are cached in
build/site-previews/, keyed on the content of each PDF, so an unchanged collection builds fast.
"""
import argparse, concurrent.futures, datetime, hashlib, html, io, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time
from html.parser import HTMLParser
from typing import NamedTuple
from urllib.parse import unquote, urljoin, urlsplit

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import markdown
from build import MIN_BODY, PRINT_SIZES, BuildError, katex, load_figures, load_meta, substitute, themes_of
from papers import CATEGORIES, FILES_URL, GENERATED_IN_REPO, ROOT, SHOWCASE, SITE_URL, Paper, discover
from readme import pending, year_key, year_text
from themes import FORMATS, THEMES, US_FORMATS, colour, dark as theme_is_dark

REPO = "https://github.com/vodhash/one-page-papers"
BASE_URL = SITE_URL  # only for canonical, Open Graph and sitemap URLs
# Where the PDF buttons point: the bucket where the CI uploads the PDFs of dist/ before it deploys
# the site, so that a link works as soon as its page is online
PDF_URL = FILES_URL + "{category}/{file}"
# The same files for the wallpapers, which the browser fetches: the bucket answers with the
# Access-Control-Allow-Origin header of the site (its CORS rule, see CONTRIBUTING.md)
WALL_PDF_URL = PDF_URL

# The wallpapers that a poster page draws in the browser: name, width and height in pixels
WALLPAPERS = (("Phone", 1170, 2532), ("Desktop", 2560, 1440), ("4K", 3840, 2160))
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
SERIES_FILE = ROOT / "series.yaml"
SERIES_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*$")
MIN_SERIES = 3  # posters in a series, at least
# the sizes at which the A file prints (PRINT_SIZES), in mm, for the wall planner
A_SIZES = {"A3": (297, 420), "A2": (420, 594), "A1": (594, 841), "A0": (841, 1189)}
US_NAMES = {"letter": "Letter", "tabloid": "Tabloid", "18x24": "18\u00a0×\u00a024\u00a0in", "24x36": "24\u00a0×\u00a036\u00a0in"}
A_W, A_H = FORMATS["A"]
THUMB_H = round(600 * A_H / A_W)  # height of the 600 px preview, the size stated in the pages
# family: the @fontsource package, its CSS files that declare the faces, and the characters it
# draws (None: any text of the site); a face is kept in every subset that covers one of them
FONTS = {
    "EB Garamond": ("eb-garamond", ("400", "400-italic", "500", "500-italic", "600", "600-italic"), None),
    "JetBrains Mono": ("jetbrains-mono", ("400", "700"), None),  # the hash of the footer, and the code of the texts
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
    return PDF_DIRS[fmt in US_FORMATS] / p.category / f"{p.slug}-{fmt}-{theme}.pdf"

def download_event(slug, fmt, theme):
    """The attributes of a PDF link: it opens in a new tab, and Umami counts a click on it as the
    event download, with its poster, format and theme."""
    return (f'data-umami-event="download" data-umami-event-slug="{slug}" data-umami-event-format="{fmt}" '
            f'data-umami-event-theme="{theme}" target="_blank" rel="noopener"')

def pdf_url(p, fmt, theme):
    f = pdf_file(p, fmt, theme)
    return PDF_URL.format(category=f.parent.name, file=f.name)

def wall_pdf_url(p, theme):
    f = pdf_file(p, "A", theme)
    return WALL_PDF_URL.format(category=f.parent.name, file=f.name)

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
        missing_us = [f.name for f in (pdf_file(p, fmt, t) for fmt in US_FORMATS for t in themes) if not f.exists()]
        if missing or missing_us:
            files, where_to, run = ((missing, f"dist/{p.category}/", f"make {p.slug}") if missing else
                                    (missing_us, f"release/us/{p.category}/", f"engine/build.py {p.slug} --us"))
            total = len(FORMATS if missing else US_FORMATS) * len(themes)
            (skipped if only_built else errors).append(
                f"{where}: {len(files)} of its {total} PDFs are not in {where_to} "
                f"({', '.join(files[:2])}{', ...' if len(files) > 2 else ''}), run `{run}`")
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

class Series(NamedTuple):
    slug: str
    title: str
    intro: str
    posters: list  # in the order they hang

def load_series(posters, only_built):
    """The series of series.yaml, with their posters, and the series left out. An unknown paper,
    a series slug used twice or a series of fewer than MIN_SERIES papers is an error; with
    only_built, a paper left out of the site is left out of its series, and a series left with
    fewer than MIN_SERIES posters is left out."""
    where = SERIES_FILE.name
    if not SERIES_FILE.exists():
        raise SiteError(f"{where} is missing: it lists the series of the site")
    try:
        data = yaml.safe_load(SERIES_FILE.read_text())
    except yaml.YAMLError as e:
        raise SiteError(f"{where}: {' '.join(str(e).split())}") from None
    if not isinstance(data, list) or not data:
        raise SiteError(f"{where}: expected a list of series, each with slug, title, intro and papers")
    try:
        known = {p.slug: p for p in discover()}
    except ValueError as e:
        raise SiteError(e) from None
    for folder in ("series", "print", "about", "assets", "previews", *CATEGORIES):
        if folder in known:
            raise SiteError(f"papers/{known[folder].category}/{folder}: the slug {folder} is a folder of the site")
    by_slug = {p.slug: p for p in posters}
    errors, series, skipped, seen = [], [], [], set()
    for i, s in enumerate(data, 1):
        if not isinstance(s, dict):
            errors.append(f"{where}: series {i} is not a mapping of slug, title, intro and papers")
            continue
        name = s.get("slug")
        at = f"{where}: series {name!r}" if name else f"{where}: series {i}"
        if set(s) != {"slug", "title", "intro", "papers"}:
            extra, missing = sorted(set(s) - {"slug", "title", "intro", "papers"}), \
                sorted({"slug", "title", "intro", "papers"} - set(s))
            errors.append(at + "".join([f": missing {', '.join(missing)}" if missing else "",
                                        f": unknown key {', '.join(map(str, extra))}" if extra else ""]))
            continue
        if not isinstance(name, str) or not SERIES_SLUG.match(name):
            errors.append(f"{at}: the slug must be lowercase letters, digits and hyphens")
            continue
        if name in seen:
            errors.append(f"{at}: slug used by another series")
            continue
        seen.add(name)
        for key in ("title", "intro"):
            if not isinstance(s[key], str) or not s[key].strip():
                errors.append(f"{at}: {key} must be a text")
        papers = s["papers"]
        if not isinstance(papers, list) or not all(isinstance(x, str) for x in papers):
            errors.append(f"{at}: papers must be a list of paper slugs")
            continue
        unknown = [x for x in papers if x not in known]
        if unknown:
            errors.append(f"{at}: unknown paper{'s' * (len(unknown) > 1)} {', '.join(unknown)} "
                          "(no folder papers/<category>/<slug>/ has this name)")
        twice = sorted({x for x in papers if papers.count(x) > 1})
        if twice:
            errors.append(f"{at}: {', '.join(twice)} listed twice")
        if len(set(papers)) < MIN_SERIES:
            errors.append(f"{at}: {len(set(papers))} paper{'s' * (len(set(papers)) != 1)}, "
                          f"a series needs at least {MIN_SERIES}")
        if unknown or twice or len(set(papers)) < MIN_SERIES:
            continue
        missing = [x for x in papers if x not in by_slug]
        if missing and not only_built:  # collect() has failed already on such a paper
            errors.append(f"{at}: {', '.join(missing)} not on the site")
            continue
        if len(papers) - len(missing) < MIN_SERIES:
            skipped.append(f"{at}: only {len(papers) - len(missing)} of its posters are built")
            continue
        if missing:
            skipped.append(f"{at}: without {', '.join(missing)}, not built")
        series.append(Series(name, s["title"].strip(), " ".join(s["intro"].split()),
                             [by_slug[x] for x in papers if x in by_slug]))
    if errors:
        raise SiteError("\nerror: ".join(errors))
    return series, skipped

# ---------------------------------------------------------------- notes and teaching kits

ANNOTATIONS, TEACHING = "annotations.yaml", "teaching.yaml"
REF_KEYS = {"title", "publisher", "author", "url", "original_url", "note", "retrieved"}
# required keys, optional keys; published: true puts the file on the site, else only --drafts does
ANNOTATION_KEYS = ({"license", "paper", "notes", "references"}, {"authors", "lang", "published"})
TEACHING_KEYS = ({"license", "paper", "level", "subject", "duration", "context", "glossary", "questions", "references"},
                 {"authors", "lang", "prerequisites", "activity", "published"})
QUESTION_KINDS = ("locate", "understand", "analyse", "calculate", "reflect")
LICENSE_URLS = {"CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/"}

class Extras(NamedTuple):
    """The content written for One Page Papers around a text: margin notes and a teaching kit."""
    annotations: dict | None
    teaching: dict | None

def is_text(v):
    return isinstance(v, str) and bool(v.strip())

def check_keys(where, data, keys, errors):
    required, optional = keys
    missing, extra = sorted(required - set(data)), sorted(set(data) - required - optional)
    if missing:
        errors.append(f"{where}: missing {', '.join(missing)}")
    if extra:
        errors.append(f"{where}: unknown key{'s' * (len(extra) > 1)} {', '.join(map(str, extra))} "
                      f"(expected {', '.join(sorted(required | optional))})")
    return not missing

def check_references(where, refs, errors):
    """The references map of a content file: {key: {title, publisher, url, ...}}."""
    if not isinstance(refs, dict) or not refs:
        errors.append(f"{where}: references must be a mapping of keys to sources, each with a title")
        return {}
    for k, r in refs.items():
        at = f"{where}: reference {k!r}"
        if not isinstance(r, dict):
            errors.append(f"{at}: expected a mapping with title, and publisher, url, retrieved...")
            continue
        extra = sorted(set(r) - REF_KEYS)
        if extra:
            errors.append(f"{at}: unknown key{'s' * (len(extra) > 1)} {', '.join(map(str, extra))} "
                          f"(expected {', '.join(sorted(REF_KEYS))})")
        if not is_text(r.get("title")):
            errors.append(f"{at}: title must be a text")
        for u in ("url", "original_url"):
            if u in r and not (isinstance(r[u], str) and re.match(r"https?://\S+$", r[u])):
                errors.append(f"{at}: {u} must be an http(s) URL")
        for t in ("publisher", "author", "note"):
            if t in r and not is_text(r[t]):
                errors.append(f"{at}: {t} must be a text")
    return refs

def check_sources(at, item, refs, errors, required=True):
    """The sources of a note, a point, a question: a list of keys of references."""
    src = item.get("sources")
    if src is None and not required:
        return
    if not isinstance(src, list) or not src or not all(isinstance(s, str) for s in src):
        errors.append(f"{at}: sources must be a list of keys of references")
        return
    unknown = [s for s in src if s not in refs]
    if unknown:
        errors.append(f"{at}: unknown source{'s' * (len(unknown) > 1)} {', '.join(unknown)} "
                      "(not a key of references)")

def short(s, n=48):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 3].rstrip() + "..."

def load_file(p, name, keys, errors):
    """A content file of a paper, read and checked for its common keys, or None."""
    path = p.paper.dir / name
    if not path.exists():
        return None
    where = f"papers/{p.category}/{p.slug}/{name}"
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        errors.append(f"{where}: {' '.join(str(e).split())}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{where}: expected a mapping")
        return None
    if not check_keys(where, data, keys, errors):
        return None
    if data["paper"] != p.slug:
        errors.append(f"{where}: paper is {data['paper']!r}, but the file is in the folder of {p.slug}")
    if not is_text(data["license"]):
        errors.append(f"{where}: license must be a text")
    if "authors" in data and not (isinstance(data["authors"], list) and all(is_text(a) for a in data["authors"])):
        errors.append(f"{where}: authors must be a list of names")
    if "published" in data and not isinstance(data["published"], bool):
        errors.append(f"{where}: published must be true or false")
    if "lang" in data and data["lang"] not in LANGUAGES:
        errors.append(f"{where}: lang must be one of {', '.join(LANGUAGES)}")
    data["_where"] = where
    data["references"] = check_references(where, data["references"], errors)
    return data

def load_annotations(p, errors):
    """annotations.yaml: margin notes, each anchored on a phrase that occurs exactly once in text.md."""
    data = load_file(p, ANNOTATIONS, ANNOTATION_KEYS, errors)
    if data is None:
        return None
    where, refs = data["_where"], data["references"]
    notes = data["notes"]
    if not isinstance(notes, list) or not notes:
        errors.append(f"{where}: notes must be a list of notes, each with anchor, note and sources")
        return None
    text = " ".join((p.paper.dir / "text.md").read_text().split())
    for i, n in enumerate(notes, 1):
        at = f"{where}: note {i}"
        if not isinstance(n, dict):
            errors.append(f"{at}: expected a mapping of anchor, note and sources")
            continue
        extra = sorted(set(n) - {"anchor", "note", "sources"})
        if extra:
            errors.append(f"{at}: unknown key{'s' * (len(extra) > 1)} {', '.join(map(str, extra))} "
                          "(expected anchor, note, sources)")
        if not is_text(n.get("anchor")) or not is_text(n.get("note")):
            errors.append(f"{at}: anchor and note must be texts")
            continue
        at = f"{where}: note {i} (anchor “{short(n['anchor'])}”)"
        count = text.count(" ".join(n["anchor"].split()))
        if count != 1:
            errors.append(f"{at}: the anchor occurs {count} times in text.md, it must occur exactly once"
                          + (" (copy it from text.md, spaces and apostrophes included)" if not count
                             else " (make it longer, so that it is unique)"))
        check_sources(at, n, refs, errors)
    return data

def load_teaching(p, errors):
    """teaching.yaml: a teaching kit, with context, glossary, questions and answers, activity."""
    data = load_file(p, TEACHING, TEACHING_KEYS, errors)
    if data is None:
        return None
    where, refs = data["_where"], data["references"]
    for k in ("level", "subject"):
        if not is_text(data[k]):
            errors.append(f"{where}: {k} must be a text")
    if not isinstance(data["duration"], int) or data["duration"] <= 0:
        errors.append(f"{where}: duration must be a number of minutes")
    if "prerequisites" in data and not is_text(data["prerequisites"]):
        errors.append(f"{where}: prerequisites must be a text")
    def items(key, fields, name, optional=()):
        lst = data[key]
        if not isinstance(lst, list) or not lst:
            errors.append(f"{where}: {key} must be a list, each item with {', '.join(fields)}")
            return
        for i, it in enumerate(lst, 1):
            at = f"{where}: {name} {i}"
            if not isinstance(it, dict):
                errors.append(f"{at}: expected a mapping with {', '.join(fields)}")
                continue
            extra = sorted(set(it) - set(fields) - set(optional) - {"sources"})
            if extra:
                errors.append(f"{at}: unknown key{'s' * (len(extra) > 1)} {', '.join(map(str, extra))}")
            bad = [f for f in fields if not is_text(it.get(f))]
            if bad:
                errors.append(f"{at}: {', '.join(bad)} must be text{'s' * (len(bad) > 1)}")
            if "kind" in it and it["kind"] not in QUESTION_KINDS:
                errors.append(f"{at}: kind must be one of {', '.join(QUESTION_KINDS)}")
            if name != "term":
                check_sources(at, it, refs, errors, required=name != "question")
    items("context", ("point",), "context point")
    items("glossary", ("term", "definition"), "term")
    items("questions", ("question", "answer"), "question", ("kind",))
    act = data.get("activity")
    if act is not None:
        at = f"{where}: activity"
        if not isinstance(act, dict) or not all(is_text(act.get(k)) for k in ("title", "instructions")):
            errors.append(f"{at}: expected a mapping with title, instructions, and duration and sources")
        else:
            extra = sorted(set(act) - {"title", "instructions", "duration", "sources"})
            if extra:
                errors.append(f"{at}: unknown key{'s' * (len(extra) > 1)} {', '.join(map(str, extra))}")
            if "duration" in act and (not isinstance(act["duration"], int) or act["duration"] <= 0):
                errors.append(f"{at}: duration must be a number of minutes")
            check_sources(at, act, refs, errors, required=False)
    return data

def load_extras(posters, drafts=False):
    """{slug: Extras} for the posters that have an annotations.yaml or a teaching.yaml. Every file is
    checked, but only those that say published: true go on the site, or all of them with drafts:
    without it, the site is the same as if the others did not exist."""
    errors, out, held = [], {}, []
    for p in posters:
        a, t = load_annotations(p, errors), load_teaching(p, errors)
        for d in (a, t):
            if d is not None and d.get("published") is not True:
                held.append(d["_where"])
        if not drafts:
            a, t = (d if d is not None and d.get("published") is True else None for d in (a, t))
        if a or t:
            out[p.slug] = Extras(a, t)
    if errors:
        raise SiteError("\nerror: ".join(errors))
    return out, held

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

def mark_image(k, bold=False):
    """The logo of mark_svg as an RGBA image, k px per unit of its 60 x 84 grid, drawn at 4x then
    reduced. bold thickens it and keeps four lines of text, for the small icons."""
    ink, acc, paper, mute = (TOKENS[t][0] for t in ("ink", "acc", "bg", "mute"))
    K = 4 * k
    im = Image.new("RGBA", (round(60 * K), round(84 * K)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = lambda x, y, w, h: (x * K, y * K, (x + w) * K, (y + h) * K)
    d.rectangle(box(2.5, 2.5, 55, 79), fill=paper, outline=ink, width=round((4.5 if bold else 3) * K))
    if not bold:
        d.rectangle(box(7, 7, 46, 70), outline=ink, width=round(1.2 * K))
    for x in (13, 37):
        d.line((x * K, 21 * K, (x + 10) * K, 21 * K), fill=ink, width=round((3 if bold else 1.6) * K))
    d.ellipse(box(24.5, 15.5, 11, 11) if bold else box(25.4, 16.4, 9.2, 9.2), fill=acc)
    rows = [(36, 47), (46, 47), (56, 47), (66, 35)] if bold else \
           [(y, 47 if i % 4 != 3 else 35) for i, y in enumerate(range(36, 74, 5))]
    for y, end in rows:
        d.line((13 * K, y * K, end * K, y * K), fill=mute, width=round((3.2 if bold else 1.6) * K))
    return im.resize((round(60 * k), round(84 * k)), Image.LANCZOS)

def matted(im, height, pad):
    """A preview reduced to a height, in its passe-partout (light frame colour)."""
    im = im.resize((round(height * im.width / im.height), height), Image.LANCZOS)
    mat = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), TOKENS["frame"][0])
    mat.paste(im, (pad, pad))
    return mat

def share_image(sources, brand=False):
    """The Open Graph image, 1200 x 630: the posters side by side on the wall, each in its
    passe-partout with a soft shadow, as on the site. sources are 1200 px WebP previews. With
    brand, the logo and the name of the site sit under the posters."""
    key = hashlib.sha256(b"".join(s.read_bytes() for s in sources) + f"v{PREVIEW_VERSION}{brand}".encode()).hexdigest()[:24]
    path = CACHE / f"share-{key}.jpg"
    if path.exists():
        return path
    W, H = 1200, 630
    height = 500 if len(sources) == 1 else 380 if brand else 430
    mats = [matted(Image.open(s).convert("RGB"), height, 14) for s in sources]
    gap = 56
    x = (W - sum(m.width for m in mats) - gap * (len(mats) - 1)) // 2
    canvas = Image.new("RGB", (W, H), TOKENS["wall"][0])
    shadow = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(shadow)
    boxes = []
    for m in mats:
        y = (H - m.height) // 2 - (38 if brand else 0)
        boxes.append((x, y))
        draw.rectangle((x + 6, y + 16, x + m.width - 6, y + m.height + 10), fill=120)
        x += m.width + gap
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.paste(Image.new("RGB", (W, H), "#3a3226"), (0, 0), shadow)
    for m, (x, y) in zip(mats, boxes):
        canvas.paste(m, (x, y))
    if brand:
        fonts = ROOT / "node_modules/@fontsource/eb-garamond/files"
        roman = ImageFont.truetype(str(fonts / "eb-garamond-latin-500-normal.woff2"), 40)
        italic = ImageFont.truetype(str(fonts / "eb-garamond-latin-400-italic.woff2"), 40)
        mark = mark_image(0.62)
        d = ImageDraw.Draw(canvas)
        w1, w2 = d.textlength("One Page ", font=roman), d.textlength("Papers", font=italic)
        x = (W - mark.width - 18 - w1 - w2) / 2
        y = H - 78
        canvas.paste(mark, (round(x), y - mark.height // 2), mark)
        x += mark.width + 18
        d.text((x, y), "One Page ", font=roman, fill=TOKENS["ink"][0], anchor="lm")
        d.text((x + w1, y), "Papers", font=italic, fill=TOKENS["ink"][0], anchor="lm")
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

SMALL_H = round(SMALL_W * A_H / A_W)

def make_thumbs(out, series, cached):
    """Writes out/previews/<slug>-<theme>-<SMALL_W>.webp, the small previews of the series cards,
    for the light and dark theme of every poster of a series, reduced from the cached 600 px
    previews. Returns ({(slug, theme): path in the site}, the files of the cache it used)."""
    thumbs, used = {}, set()
    for p in {p.slug: p for s in series for p in s.posters}.values():
        for t in dict.fromkeys((p.light, p.dark)):
            src = cached[p.slug, t][600]
            path = CACHE / f"{src.stem.removesuffix('-600')}-{SMALL_W}.webp"
            if not path.exists():
                with Image.open(src) as im:
                    save_atomic(path, webp(im.convert("RGB").resize((SMALL_W, SMALL_H), Image.LANCZOS)))
            dst = f"previews/{p.slug}-{t}-{SMALL_W}.webp"
            shutil.copyfile(path, out / dst)
            thumbs[p.slug, t] = dst
            used.add(path)
    return thumbs, used

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

# ---------------------------------------------------------------- pages

def last_changes():
    """The day of the last commit of each paper, by slug, and of the repository: the lastmod of the
    sitemap. Empty without git or its history (the pages workflow fetches the history, not its files)."""
    try:
        run = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True,
                                        check=True).stdout
        log, head = run("log", "--format=%x00%cs", "--name-only", "--", "papers"), run("log", "-1", "--format=%cs")
    except (OSError, subprocess.CalledProcessError):
        return {}, None
    dates = {}
    for block in log.split("\x00")[1:]:  # newest first
        date, *files = block.strip().split("\n")
        for f in files:
            if f.count("/") >= 3:
                dates.setdefault(f.split("/")[2], date)
    return dates, head.strip() or None

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

def category_page(c, posters, previews):
    """The page of a category, under /<category>/: its posters, and links to the other categories."""
    mine = [p for p in posters if p.category == c]
    cats = [k for k in CATEGORIES if any(p.category == k for p in posters)]
    years = sorted((p.meta["year"] for p in mine), key=year_key)
    span = (year_text(years[0]) if year_text(years[0]) == year_text(years[-1])
            else f"{year_text(years[0])} to {year_text(years[-1])}")
    def link(k):
        current = ' aria-current="page"' if k == c else ""
        return (f'<li><a class="pill" href="../{k}/"{current}>{esc(CATEGORIES[k])} '
                f'<span class="count">{sum(p.category == k for p in posters)}</span></a></li>')
    main = substitute((WEB / "category.html").read_text(), {
        "TITLE": esc(CATEGORIES[c]), "COUNT": esc(f"{len(mine)} posters · {span}"), "LEDE": esc(CATEGORY_LEDES[c]),
        "CARDS": "\n".join(card(previews, p, "../") for p in mine), "OTHERS": "\n".join(link(k) for k in cats)})
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

def home_page(posters, previews, series, thumbs):
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
                f'<a href="{show.slug}/"><i>{title(m["title"])}</i></a>\n'
                f'<span class="meta">{esc(year_text(m["year"]))} · {esc(CATEGORIES[show.category])} · '
                f'Print from {m["min_print"]}</span></figcaption>')
    main = substitute((WEB / "home.html").read_text(), {
        "RELEASE": RELEASE_URL, "FORMATS": esc(formats), "FEATURED": featured,
        "INTRO": esc(f"{len(posters)} posters in {len(cats)} categories, from {year_text(years[0])} to "
                     f"{year_text(years[-1])}, each a free PDF to print and frame."),
        "FILTERS": "\n".join(filters), "CARDS": "\n".join(card(previews, p, "") for p in posters),
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
    host = urlsplit(src["url"]).netloc.removeprefix("www.")
    facts = [("Print from", m["min_print"]), ("License", esc(lic["text"])),
             ("Source", f'<a href="{html.escape(src["url"])}">{esc(host)}</a>'),
             ("Retrieved", date_text(src["retrieved"])),
             ("Language", LANGUAGES.get(m.get("lang", "en"), m.get("lang", "en")))]
    if lic.get("holder"):
        facts.append(("Rights holder", esc(lic["holder"])))
    if m.get("contributors"):
        facts.append(("Proposed by", ", ".join(f'<a href="https://github.com/{h}">@{h}</a>' for h in m["contributors"])))
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
    sizes = [f'<label class="pill"><input type="radio" name="wp-size" value="{n.lower()}" data-w="{w}" data-h="{h}"'
             f'{" checked" if i == 0 else ""}>{n} <span class="count">{w}\u00a0×\u00a0{h}</span></label>'
             for i, (n, w, h) in enumerate(WALLPAPERS)]
    wthemes = [f'<label class="pill"><input type="radio" name="wp-theme" value="{t}"{" checked" if t == p.light else ""} '
               f'data-paper="{hexcolour(t, "paper")}" data-pdf="{wall_pdf_url(p.paper, t)}"><span class="swatch" '
               f'style="--sw:{hexcolour(t, "paper")};--sa:{hexcolour(t, "acc")}" aria-hidden="true"></span>{t}</label>'
               for t in p.themes]
    main = substitute((WEB / "poster.html").read_text(), {
        "SLUG": p.slug, "WP_SIZES": "\n".join(sizes), "WP_THEMES": "\n".join(wthemes),
        "CATEGORY": p.category, "CATEGORY_TITLE": esc(CATEGORIES[p.category]), "TITLE": esc(m["title"]),
        "TITLE_H1": title(m["title"]),
        "YEAR": esc(year_text(m["year"])), "AUTHORS": esc(", ".join(m["authors"])),
        "SUBTITLE": f'<p class="subtitle">{m["kicker"]}</p>' if m.get("kicker") else "",
        "READ_NOTE": "The whole poster as a web page" + (", with notes in the margin"
                                                          if extras and extras.annotations else ""),
        "TEACH": ('<p class="read-link"><a class="btn btn-line" href="teach/">Teaching kit</a> '
                  '<span>Context, glossary, questions and answers, on A4</span></p>\n'
                  if extras and extras.teaching else ""),
        "SUMMARY": esc(m["summary"]), "LIGHT": p.light, "DARK": p.dark, "SERIES": series_links(p, series, root),
        "PICTURE": picture(previews, p, root, "(min-width: 1200px) 480px, (min-width: 768px) 52vw, 86vw", eager=True),
        "SHOWN": shown, "FACTS": "\n".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts),
        "PILLS": "\n".join(pills), "ROWS": "\n".join(rows), "US_ROWS": "\n".join(us_rows),
        "ZIP": ZIP_URL.format(category=p.category),
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

# ---------------------------------------------------------------- series

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
                  (f, US_NAMES[f], *US_FORMATS[f], f, "") for f in US_FORMATS])]
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
    # the posters, with every PDF of dist/ (site.js shows those of the format and theme chosen)
    rows = []
    for i, p in enumerate(s.posters, 1):
        m = p.meta
        links = []
        for fmt in FORMATS:
            for t in p.themes:
                cls = " d0" if t == p.light else ""
                links.append(f'<a class="btn btn-line{cls}" data-f="{fmt}" data-t="{t}" href="{pdf_url(p.paper, fmt, t)}" '
                             f'type="application/pdf" {download_event(p.slug, fmt, t)}>{format_name(fmt)} · {t} '
                             '<span class="size">'
                             f'{size_text(pdf_file(p.paper, fmt, t))}</span></a>')
        srcs = "".join(f' data-src-{t}="{root}{previews[p.slug, t][600]}"' for t in p.themes)
        us_zip = US_ZIP_URL.format(category=p.category)
        rows.append(
            f'<li data-slug="{p.slug}" data-min="{m["min_print"]}" data-light="{p.light}" '
            f'data-title="{esc(m["title"])}"{srcs}>\n'
            f'<div class="mat">{small_picture(thumbs, p, root, "")}</div>\n'
            f'<div class="sdl-what">\n<p class="eyebrow">{i} · {esc(CATEGORIES[p.category])}</p>\n'
            f'<h3 class="card-title"><a href="{root}{p.slug}/">{title(m["title"])}</a></h3>\n'
            f'<p class="by">{by_line(m)}</p>\n<p class="print">Print from {m["min_print"]}</p>\n'
            f'<p class="sdl-warn" hidden></p>\n</div>\n'
            f'<div class="dl-links">{"".join(links)}'
            f'<p class="sdl-in-us" hidden>In <a href="{us_zip}">{p.category}-us.zip</a>, below</p></div>\n</li>')
    cats = list(dict.fromkeys(p.category for p in s.posters))
    us_zips = []
    for c in cats:
        names = ", ".join(esc(p.meta["title"]) for p in s.posters if p.category == c)
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

# ---------------------------------------------------------------- reading edition

READ_IMAGE_W = 2000  # px: the raster images of a reading page are reduced to this width at most
READ_VERSION = 1  # part of the cache key of the images of the reading pages
KATEX_CSS = ROOT / "node_modules" / "katex" / "dist" / "katex.min.css"
PDFJS = ROOT / "node_modules" / "pdfjs-dist"
PDFJS_FILES = ("build/pdf.min.mjs", "build/pdf.worker.min.mjs", "LICENSE")  # into assets/pdfjs/

class RawText(NamedTuple):
    """The text of a poster, rendered as build.py renders it, before KaTeX."""
    body: str
    math: list

def texts(posters):
    """{slug: html of the text}, with its math set by one run of KaTeX for the whole collection.
    The text goes through markdown.render with the figures and the folder of the paper, as in
    build.py, but without the hero: its image stays in the flow of the text."""
    raw = {}
    for p in posters:
        path = p.paper.dir / "text.md"
        try:
            body, math, _ = markdown.render(path.read_text(), load_figures(p.paper.dir), p.meta.get("numbered", False),
                                            assets=p.paper.dir)
        except markdown.MarkdownError as e:
            raise SiteError(f"{path.relative_to(ROOT)}:{e.line}: {e.msg}") from None
        raw[p.slug] = RawText(body, math)
    try:
        done = iter(katex([x for t in raw.values() for x in t.math]))
    except BuildError as e:
        raise SiteError(e) from None
    out = {}
    for slug, t in raw.items():
        body = t.body
        for i in range(len(t.math)):
            body = body.replace(f"<!--MATH:{i}-->", next(done), 1)
        out[slug] = body
    return out

def plain(fragment):
    """The text of an HTML fragment, for an attribute."""
    return html.escape(" ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split()))

def web_image(path):
    """An image of a text for the web, in the cache: an SVG as it is, a raster image as WebP at
    most READ_IMAGE_W wide. Returns (path in the cache, width, height)."""
    data = path.read_bytes()
    key = f"read-{hashlib.sha256(data).hexdigest()[:24]}-v{READ_VERSION}"
    if path.suffix.lower() == ".svg":
        dst = CACHE / f"{key}.svg"
        if not dst.exists():
            save_atomic(dst, data)
        w, h = markdown.image_size(path, data)
        return dst, w, h
    dst = CACHE / f"{key}.webp"
    if dst.exists():
        with Image.open(dst) as im:
            return dst, *im.size
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info else "RGB")
    if im.width > READ_IMAGE_W:
        im = im.resize((READ_IMAGE_W, round(im.height * READ_IMAGE_W / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=84, method=6)
    save_atomic(dst, buf.getvalue())
    return dst, im.width, im.height

IMAGE_FIGURE = re.compile(r'<figure class="image" data-dark="(\w+)"( data-light="\w+")? data-file="([^"]+)"( style="[^"]*")?>'
                          r'<img src="data:[^"]+"(?: width="\d+" height="\d+")? alt="">(<figcaption>.*?</figcaption>)?</figure>', re.S)
SVG_FIGURE = re.compile(r'<figure><svg\b.*?</svg></figure>', re.S)
HEADING = re.compile(r'<h([234])((?:\s[^>]*)?)>(.*?)</h\1>', re.S)

def reading_body(p, body, files):
    """The text of a poster made for a web page: its images as files (added to files, {site
    path: path in the cache}) with their size and an alt taken from their caption, the ids of each
    SVG figure made its own, an anchor on every heading, and footnotes linked both ways."""
    folder = f"{p.slug}/read/"
    def image(k):
        src = p.paper.dir / html.unescape(k.group(3))
        cached, w, h = web_image(src)
        name = pathlib.PurePath(html.unescape(k.group(3))).with_suffix(cached.suffix).as_posix()
        files[folder + name] = cached
        cap = k.group(5) or ""
        text = plain(cap) or esc(f"Image from “{p.meta['title']}”")
        size = f' width="{w}" height="{h}"' if w else ""
        return (f'<figure class="image" data-dark="{k.group(1)}"{k.group(2) or ""}{k.group(4) or ""}>'
                f'<img src="{html.escape(name)}"{size} alt="{text}" loading="lazy" decoding="async">{cap}</figure>')
    body = IMAGE_FIGURE.sub(image, body)
    if "data:image/" in body:
        raise SiteError(f"papers/{p.category}/{p.slug}: an image of the text was left as a data URI")
    # the figures of svg.py all define the same markers: each figure gets ids of its own
    n = iter(range(1, 1000))
    def figure(k):
        i, svg = next(n), k.group(0)
        ids = re.findall(r'\bid="([^"]+)"', svg)
        for x in ids:
            svg = re.sub(rf'\bid="{re.escape(x)}"', f'id="fig{i}-{x}"', svg)
            svg = re.sub(rf'(url\(#|href="#){re.escape(x)}([)"])', rf'\g<1>fig{i}-{x}\2', svg)
        return svg.replace("<svg ", '<svg role="img" aria-label="Figure" ', 1).replace('<figure>', '<figure class="fig">', 1)
    body = SVG_FIGURE.sub(figure, body)
    # a Morse code drawn with empty elements (morse-phonetic-alphabet) is read out as its dots and dashes
    body = re.sub(r'(<span class="m" data-m="([.\-]+)")>', r'\1 role="img" aria-label="\2">', body)
    # numbered anchors: s1, s1-2, s1-2-3, from the place of each heading in the text
    nums = [0, 0, 0]
    def heading(k):
        level, attrs, inner = int(k.group(1)), k.group(2), k.group(3)
        nums[level - 2] += 1
        nums[level - 1:] = [0] * (4 - level)
        m = re.search(r'\bid="([^"]+)"', attrs)
        hid = m.group(1) if m else "s" + "-".join(str(x) for x in nums[:level - 1])
        if not m:
            attrs += f' id="{hid}"'
        return (f'<h{level}{attrs}>{inner}<a class="anchor" href="#{hid}" aria-label="Link to this section">#</a>'
                f'</h{level}>')
    body = HEADING.sub(heading, body)
    # footnotes: a call links to its note, the note back to its first call
    called = set()
    def call(k):
        num = k.group(1)
        back = "" if num in called else f' id="fnref-{num}"'
        called.add(num)
        return f'<sup class="fn"><a href="#fn-{num}"{back} aria-label="Note {num}">{num}</a></sup>'
    body = re.sub(r'<sup class="fn">(\d+)</sup>', call, body)
    def note(k):
        num = k.group(1)
        back = f' <a class="back" href="#fnref-{num}" aria-label="Back to the call of note {num}">↑</a>' if num in called else ""
        return f'<li id="fn-{num}"><span>{num}</span><div>{k.group(2)}{back}</div></li>'
    if '<div class="footnotes">' in body:
        head, notes = body.rsplit('<div class="footnotes">', 1)
        notes = re.sub(r'<li><span>(\d+)</span><div>(.*?)</div></li>', note, notes, flags=re.S)
        body = f'{head}<div class="footnotes">{notes}'
    return body

# the margin notes of a reading page: where their anchors are in the rendered text
NOTE_SKIP = {"svg", "math", "script", "style"}  # and the spans of KaTeX: their text is not the text's
NOTE_BLOCKS = {"p", "div", "li", "ol", "ul", "h2", "h3", "h4", "blockquote", "figure", "figcaption", "table", "tr",
               "td", "th", "dl", "dt", "dd", "pre", "br", "hr", "section", "caption"}
VOID = {"br", "hr", "img", "input", "wbr", "source", "meta", "link", "col", "area"}
QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', " ": " ", " ": " ", " ": " "})
TOKEN = re.compile(r"<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>|&(#?\w+);|[^<&]", re.S)

def text_positions(body):
    """The text of an HTML fragment as it reads, with straight quotes and single spaces, and for
    each of its characters the span of the source it comes from. Math and figures count as one
    character that no phrase matches, and a block boundary as another."""
    chars, spans, stack, skip = [], [], [], None
    def put(c, a, b):
        c = c.translate(QUOTES)
        if c.isspace():
            if chars and chars[-1] == " ":
                return
            c = " "
        chars.append(c)
        spans.append((a, b))
    for k in TOKEN.finditer(body):
        a, b = k.span()
        close, tag, attrs, selfclose, entity = k.groups()
        if tag:
            tag = tag.lower()
            if skip is not None:
                if close and len(stack) == skip and stack[-1] == tag:
                    stack.pop()
                    skip = None
                    put("\x00", a, a)
                elif close:
                    stack.pop() if stack else None
                elif not selfclose and tag not in VOID:
                    stack.append(tag)
                continue
            if tag in NOTE_BLOCKS:
                put("\x01", a, a)
            if close:
                if stack:
                    stack.pop()
            elif not selfclose and tag not in VOID:
                stack.append(tag)
                if tag in NOTE_SKIP or (tag == "span" and re.search(r'class="katex(?:-display)?"', attrs)):
                    skip = len(stack)
            continue
        if skip is not None:
            continue
        put(html.unescape(k.group()) if entity else k.group(), a, b)
    return "".join(chars), spans

def note_sources(keys, refs):
    parts = []
    for k in keys:
        r = refs[k]
        name = esc(r["title"])
        if r.get("url"):
            archived = " (archived copy)" if "web.archive.org/" in r["url"] else ""
            name = f'<a href="{html.escape(r["url"])}">{name}</a>{archived}'
        parts.append(name + (f', {esc(r["publisher"])}' if r.get("publisher") else ""))
    return f'<span class="sn-src"><span class="sn-label">Source{"s" * (len(keys) > 1)}:</span> {"; ".join(parts)}.</span>'

def annotate(p, text, data):
    """The text of a reading page with its margin notes: each anchor phrase in a <mark>, followed
    by the number of its note, a checkbox that opens the note in the text on small screens and
    without JavaScript, and the note itself, which site.js sets in the margin of a wide screen."""
    plain_text, spans = text_positions(text)
    refs, lang = data["references"], data.get("lang", "en")
    inserts = []  # (position in the source, order at that position: close, note, open, html)
    found = []
    for k, n in enumerate(data["notes"], 1):
        want = " ".join(n["anchor"].translate(QUOTES).split())
        count = plain_text.count(want)
        if count != 1:
            raise SiteError(f"{data['_where']}: note {k} (anchor “{short(n['anchor'])}”): found {count} times in the text "
                            "as the reading page renders it, where it must occur exactly once")
        found.append((plain_text.find(want), want, n))
    # the notes are numbered in the order of their phrases in the text, whatever their order in the file
    for i, (at, want, n) in enumerate(sorted(found, key=lambda f: f[0]), 1):
        pos = spans[at:at + len(want)]
        runs = [[pos[0][0], pos[0][1]]]
        for a, b in pos[1:]:
            if a == runs[-1][1]:
                runs[-1][1] = b
            else:
                runs.append([a, b])
        for j, (a, b) in enumerate(runs):
            ident = f' id="an-{i}"' if j == 0 else ""
            inserts.append((a, 2, f'<mark class="anno" data-note="{i}"{ident}>'))
            inserts.append((b, 0, "</mark>"))
        body = esc(" ".join(n["note"].split()))
        inserts.append((runs[-1][1], 1,
            f'<input type="checkbox" class="sn-toggle" id="sn-t{i}" aria-controls="sn-{i}">'
            f'<label class="sn-num" for="sn-t{i}"><span class="sr-only">Note </span>{i}</label>'
            f'<span class="sidenote" id="sn-{i}" lang="{lang}" data-note="{i}">'
            f'<span class="sn-n" aria-hidden="true">{i}</span>'
            f'<span class="sr-only">Note {i}, written for One Page Papers: </span>{body} '
            f'{note_sources(n["sources"], refs)}</span>'))
    for pos, _, frag in sorted(inserts, key=lambda x: (x[0], x[1]), reverse=True):
        text = text[:pos] + frag + text[pos:]
    return text

def written_by(data):
    """Who wrote a content file, for its credit line: nothing when it is the site itself."""
    who = [a for a in data.get("authors") or [] if a != NAME]
    return f" by {esc(', '.join(who))}" if who else ""

def license_html(lic):
    lic = lic.removesuffix(f", written for {NAME}")  # the credit line says it already
    for name, url in LICENSE_URLS.items():
        if lic.startswith(name):
            return f'<a href="{url}">{esc(name)}</a>{esc(lic[len(name):])}'
    return esc(lic)

def read_page(p, body, files, katex_head, extras=None):
    """The reading edition of a poster: its whole text as a web page, under /<slug>/read/, with its
    margin notes when the paper has an annotations.yaml."""
    m, root = p.meta, "../../"
    lic, src = m["license"], m["source"]
    lang = m.get("lang", "en")
    host = urlsplit(src["url"]).netloc.removeprefix("www.")
    text = reading_body(p, body, files)
    notes = extras.annotations if extras else None
    intro = ""
    if notes:
        text = annotate(p, text, notes)
        k = len(notes["notes"])
        intro = (f'<aside class="anno-intro" aria-label="About the margin notes" lang="en">\n'
                 f'<p class="eyebrow">Annotated edition</p>\n'
                 f'<p><b>{k} notes written for {NAME}</b> explain the phrases <mark class="anno">marked like this</mark>: '
                 'the number after a phrase opens its note, which a wide screen shows in the margin. They are not part '
                 f'of the original text. Written for {NAME}{written_by(notes)}; license: {license_html(notes["license"])}. '
                 'Each note gives its sources.</p>\n'
                 '<p class="anno-switch" hidden><button type="button" class="pill" aria-pressed="true" '
                 'data-notes-toggle>Show the notes</button></p>\n</aside>\n')
    teach = extras.teaching if extras else None
    facts = [("Source", f'<a href="{html.escape(src["url"])}">{esc(host)}</a>'),
             ("Retrieved", date_text(src["retrieved"])), ("License", esc(lic["text"]))]
    if lic.get("holder"):
        facts.append(("Rights holder", esc(lic["holder"])))
    if m.get("contributors"):
        facts.append(("Proposed by", ", ".join(f'<a href="https://github.com/{h}">@{h}</a>' for h in m["contributors"])))
    facts.append(("Language", LANGUAGES.get(lang, lang)))
    # what the license asks to carry with the text, in sight: its notice, and the footer of the
    # poster (attribution, license URI); why a text is free, and the notes, are in the details
    notices = []
    if lic.get("notice"):
        notices.append(f'<blockquote class="notice"><p>{esc(lic["notice"])}</p></blockquote>')
    footer = [c for c in (m.get("footer") or []) if c]
    if footer:
        notices.append('<ul class="read-footer" aria-label="The footer of the poster">'
                       + "".join(f"<li>{c}</li>" for c in footer) + "</ul>")
    rights = [f'<p>{esc(lic["basis"])}</p>'] if lic.get("basis") else []
    if lic.get("notice"):
        rights.append(f'<p>License notice: “{esc(lic["notice"])}”</p>')
    if lic.get("note"):
        rights.append(f'<p>{esc(lic["note"])}</p>')
    kicker = f'<p class="subtitle" lang="{lang}">{m["kicker"]}</p>\n' if m.get("kicker") else ""
    byline = f'<p class="byline">{m["byline"]}</p>\n' if m.get("byline") else ""
    abstract = ""
    if m.get("abstract"):
        label = m.get("abstract_label", "Abstract.")
        abstract = f'<p class="abstract"><b>{label}</b> {markdown.inline(m["abstract"])}</p>\n'
    main = substitute((WEB / "read.html").read_text(), {
        "CATEGORY": p.category, "CATEGORY_TITLE": esc(CATEGORIES[p.category]), "TITLE": esc(m["title"]),
        "TITLE_H1": title(m["title"]), "LANG": lang, "YEAR": esc(year_text(m["year"])),
        "AUTHORS": esc(", ".join(m["authors"])), "KICKER": kicker, "BYLINE": byline,
        "FACTS": "\n".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts),
        "EDITION": esc(src["edition"]), "RIGHTS": "\n".join(rights),
        "NOTICES": "".join(x + "\n" for x in notices),
        "ABSTRACT": abstract, "TEXT": text, "ROOT": root, "SLUG": p.slug, "NOTES_INTRO": intro,
        "READ_CLASS": " annotated" if notes else "",
        "TEACH": ' <a class="btn btn-line" href="../teach/">Teaching kit <span class="size">questions, glossary</span></a>'
                 if teach else ""})
    return Page(f"{p.slug}/read/index.html", f"{esc(m['title'])}, the text · {NAME}",
                esc(f"The full text of “{m['title']}” ({authors_short(m)}, {year_text(m['year'])}), "
                    "as set on its poster, to read on screen."),
                main, f"previews/{p.slug}-share.jpg", "", esc(alt(p)), katex_head if "katex" in text else "")

# ---------------------------------------------------------------- teaching kit

KIND_NAMES = {"locate": "Find", "understand": "Understand", "analyse": "Analyse", "calculate": "Calculate",
              "reflect": "Discuss"}

def minutes(n):
    return f"{n} minutes"

def cites(keys, numbers):
    """The sources of an item as the numbers of the references, linked to them."""
    if not keys:
        return ""
    links = ", ".join(f'<a href="#ref-{numbers[k]}">{numbers[k]}</a>' for k in keys)
    return f' <span class="cite"><span class="sr-only">Sources: </span>[{links}]</span>'

def reference_item(n, r):
    title_ = esc(r["title"])
    if r.get("url"):
        title_ = f'<a href="{html.escape(r["url"])}">{title_}</a>'
    parts = [title_] + [esc(r[k]) for k in ("author", "publisher") if r.get(k)]
    line = ", ".join(parts) + "."
    if r.get("url") and "web.archive.org/" in r["url"]:
        orig = r.get("original_url")
        line += " Archived copy" + (f' of <span class="url">{esc(urlsplit(orig).netloc + urlsplit(orig).path)}</span>'
                                    if orig else "") + "."
    if r.get("retrieved"):
        line += f" Retrieved {date_text(r['retrieved'])}."
    if r.get("note"):
        line += f' <span class="ref-note">{esc(" ".join(r["note"].split()))}</span>'
    return f'<li id="ref-{n}"><span class="ref-n">{n}</span><p>{line}</p></li>'

def teach_page(p, previews, data):
    """The teaching kit of a poster, under /<slug>/teach/: laid out for the screen, and printable
    on A4 with or without the answers, which start on a page of their own."""
    m, root = p.meta, "../../"
    refs = data["references"]
    numbers = {k: i for i, k in enumerate(refs, 1)}
    facts = [("Level", esc(data["level"])), ("Subject", esc(data["subject"])),
             ("Duration", minutes(data["duration"])), ("Print from", m["min_print"])]
    prereq = (f'<p class="teach-pre"><b>Prerequisites.</b> {esc(" ".join(data["prerequisites"].split()))}</p>\n'
              if data.get("prerequisites") else "")
    context = "\n".join(f'<li><p>{esc(" ".join(c["point"].split()))}{cites(c.get("sources"), numbers)}</p></li>'
                        for c in data["context"])
    glossary = "\n".join(f'<div><dt>{esc(g["term"])}</dt><dd>{esc(" ".join(g["definition"].split()))}</dd></div>'
                         for g in data["glossary"])
    def kind(q):
        return f'<span class="q-kind">{KIND_NAMES[q["kind"]]}</span> ' if q.get("kind") else ""
    questions = "\n".join(f'<li id="q-{i}"><span class="q-n">{i}</span><p>{kind(q)}{esc(" ".join(q["question"].split()))}</p></li>'
                          for i, q in enumerate(data["questions"], 1))
    answers = "\n".join(
        f'<li id="a-{i}"><span class="q-n">{i}</span><div><p class="a-q">{esc(" ".join(q["question"].split()))}</p>'
        f'<p>{esc(" ".join(q["answer"].split()))}{cites(q.get("sources"), numbers)}</p></div></li>'
        for i, q in enumerate(data["questions"], 1))
    act = data.get("activity")
    activity = ""
    if act:
        dur = f' <span class="act-dur">{minutes(act["duration"])}</span>' if act.get("duration") else ""
        activity = (f'<section class="teach-sec teach-act" aria-labelledby="t-activity">\n'
                    f'<h2 id="t-activity">Activity</h2>\n<h3>{esc(act["title"])}{dur}</h3>\n'
                    f'<p>{esc(" ".join(act["instructions"].split()))}{cites(act.get("sources"), numbers)}</p>\n</section>\n')
    wall = ("Since it prints from A3, its body text is at least 8 pt there, readable from up close."
            if m["min_print"] == "A3" else
            f"At A3 its body text is under 8 pt, to be read from very close; it prints for reading from "
            f"{m['min_print']}.")
    a_pdf = pdf_url(p.paper, "A", p.light)
    main = substitute((WEB / "teach.html").read_text(), {
        "SLUG": p.slug, "CATEGORY": p.category, "CATEGORY_TITLE": esc(CATEGORIES[p.category]), "TITLE": esc(m["title"]),
        "TITLE_H1": title(m["title"]), "LANG": m.get("lang", "en"), "YEAR": esc(year_text(m["year"])),
        "AUTHORS": esc(", ".join(m["authors"])), "SUBJECT": esc(data["subject"]),
        "FACTS": "\n".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts), "PREREQ": prereq,
        "WALL": (f'For the classroom wall, the <a href="{a_pdf}" type="application/pdf" '
                 f'{download_event(p.slug, "A", p.light)}>A PDF of the poster</a> '
                 f'prints at A3 (29.7 × 42 cm). {wall} '
                 f'<a href="{root}print/?poster={p.slug}">How to have it printed</a>.'),
        "BY": f'Written for {NAME}{written_by(data)}; license: {license_html(data["license"])}. '
              'Numbers in brackets refer to the references at the end.',
        "CONTEXT": context, "GLOSSARY": glossary, "QUESTIONS": questions, "ACTIVITY": activity,
        "ANSWERS": answers, "REFS": "\n".join(reference_item(numbers[k], r) for k, r in refs.items()),
        "PICTURE": picture(previews, p, root, "(min-width: 1200px) 300px, (min-width: 900px) 26vw, 60vw"),
        "COUNT": f"{len(data['questions'])} questions"})
    return Page(f"{p.slug}/teach/index.html", f"{esc(m['title'])}, teaching kit · {NAME}",
                esc(f"A teaching kit for “{m['title']}” ({authors_short(m)}, {year_text(m['year'])}): context, "
                    f"glossary, {len(data['questions'])} questions with answers for the teacher, and an activity, "
                    "printable on A4."),
                main, f"previews/{p.slug}-share.jpg", "", esc(alt(p)))

def katex_css(pages_html):
    """The stylesheet of KaTeX for the site, and the font files it needs: the families that the
    classes of the math of the pages use, in WOFF2 only."""
    if not KATEX_CSS.exists():
        raise SiteError(f"{KATEX_CSS.relative_to(ROOT)} is missing, run `make deps`")
    css = KATEX_CSS.read_text()
    classes = set()
    for h in pages_html:
        for attr in re.findall(r'class="([^"]*)"', h):
            classes.update(attr.split())
    used = {"KaTeX_Main"}
    for sel, decl in re.findall(r"([^{}@]+)\{([^{}]*font(?:-family)?:[^{}]*)\}", css):
        fam = re.findall(r"KaTeX_\w+", decl)
        if fam and any(all(c in classes for c in re.findall(r"\.([\w-]+)", one)) for one in sel.split(",")):
            used.update(fam)
    files = []
    def face(k):
        block = k.group(0)
        fam = re.search(r"font-family:\"?(KaTeX_\w+)", block).group(1)
        if fam not in used:
            return ""
        woff2 = re.search(r"url\((fonts/[^)]+\.woff2)\)", block).group(1)
        files.append(KATEX_CSS.parent / woff2)
        return re.sub(r"src:[^;}]+", f'src:url({woff2}) format("woff2")', block)
    css = re.sub(r"@font-face\{[^}]*\}", face, css)
    return css, files

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
    return Page("about/index.html", f"About · {NAME}",
                esc("Where one-page-papers comes from: the wish to frame the Bitcoin whitepaper, which became an "
                    "engine that typesets foundational texts on one page."),
                main, "previews/share.jpg", "about", "Three posters of the collection side by side on a wall")

def print_page(posters, previews):
    """The guide to having a poster printed, /print/. With ?poster=<slug> (the Print it button of a
    poster page), site.js adds a box for that poster, from the data of #print-data: its Print from,
    its themes and the links to its PDFs."""
    fmts = [("A", format_name("A").replace(" ", " "))] + [(f, format_name(f)) for f in FORMATS if f != "A"]
    fmts += [(f, format_name(f)) for f in US_FORMATS]  # in release/us/, served from FILES_URL too
    data = {
        "pdf": PDF_URL, "us": US_ZIP_URL, "sizes": list(PRINT_SIZES),
        "formats": [[f, n.replace(" ", " ")] for f, n in fmts],
        "themes": {t: [hexcolour(t, "paper"), hexcolour(t, "acc"), int(theme_is_dark(t))] for t in THEMES},
        # the previews of the box are previews/<slug>-<theme>-600.webp, which make_previews writes
        "posters": {p.slug: [markdown.smart(p.meta["title"]), p.category, p.meta["min_print"], p.themes]
                    for p in posters if all((p.slug, t) in previews for t in p.themes)}}
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    rows = [f'<tr><td>{k}</td><td>{cm_text(w)} × {cm_text(h)}</td><td>The A PDF</td></tr>'
            for k, (w, h) in A_SIZES.items()]
    rows += [f'<tr><td>{format_name(f)}</td><td>{cm_text(w)} × {cm_text(h)}</td><td>Its own PDF</td></tr>'
             for f, (w, h) in FORMATS.items() if f != "A"]
    rows += [f'<tr><td>{US_NAMES[f]}</td><td>{w / 10:.1f} × {h / 10:.1f}</td><td>In the US zip of the release</td></tr>'
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

def write(out, posters, series, extras=None):
    """Writes the whole site into the empty folder out, with the margin notes and teaching kits of
    extras ({slug: Extras}). Returns a summary."""
    extras = extras or {}
    previews, cached = make_previews(out, posters)
    thumbs, thumb_files = make_thumbs(out, series, cached)
    show = next(p for p in posters if p.slug == SHOWCASE)
    # the home page shows three posters: the showcase between the first ones of two other categories
    firsts = [next(q for q in posters if q.category == c) for c in dict.fromkeys(q.category for q in posters)]
    others = [q for q in firsts if q is not show][:2]
    trio = [others[0], show, others[1]] if len(others) == 2 else [show]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(16, os.cpu_count() or 2)) as ex:
        shares = list(ex.map(lambda p: share_image([cached[p.slug, p.light][1200]]), posters))
    for p, f in zip(posters, shares):
        shutil.copyfile(f, out / f"previews/{p.slug}-share.jpg")
    shares.append(share_image([cached[q.slug, q.light][1200] for q in trio], brand=True))
    shutil.copyfile(shares[-1], out / "previews/share.jpg")
    for s in series:  # a series: its first three posters
        shares.append(share_image([cached[q.slug, q.light][1200] for q in s.posters[:3]]))
        shutil.copyfile(shares[-1], out / f"previews/series-{s.slug}-share.jpg")
    cats = list(dict.fromkeys(q.category for q in sorted(posters, key=lambda q: list(CATEGORIES).index(q.category))))
    for c in cats:  # a category: its first three posters
        shares.append(share_image([cached[q.slug, q.light][1200] for q in posters if q.category == c][:3]))
        shutil.copyfile(shares[-1], out / f"previews/category-{c}-share.jpg")

    pages = [home_page(posters, previews, series, thumbs), about_page(posters, previews), not_found_page(),
             print_page(posters, previews)]
    pages += [poster_page(p, posters, previews, series, extras.get(p.slug)) for p in posters]
    teach = [teach_page(p, previews, extras[p.slug].teaching) for p in posters
             if p.slug in extras and extras[p.slug].teaching]
    pages += teach
    pages += [series_index_page(series, thumbs)] + [series_page(s, series, previews, thumbs) for s in series]
    pages += [category_page(c, posters, previews) for c in cats]
    # the reading pages, with their images and the stylesheet of KaTeX for those that have math
    bodies, images = texts(posters), {}
    katex_head = '<link rel="stylesheet" href="{{ROOT}}assets/katex.css?v={katex}">\n'
    reads = [read_page(p, bodies[p.slug], images, katex_head, extras.get(p.slug)) for p in posters]
    pages += reads
    for dst, src in images.items():
        (out / dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out / dst)
    prune({f for paths in cached.values() for f in paths.values()} | set(shares) | set(images.values()) | thumb_files)
    by_slug, by_series = {p.slug: p for p in posters}, {f"series/{s.slug}/index.html": s for s in series}
    def trail(pg):
        parts = pg.path.split("/")
        if parts[0] in by_slug and len(parts) == 3:  # a reading page or a teaching kit
            q = by_slug[parts[0]]
            last = "The text" if parts[1] == "read" else "Teaching kit"
            return (crumbs_ld(("Collection", ""), (CATEGORIES[q.category], f"{q.category}/"),
                              (q.meta["title"], f"{q.slug}/"), (last, f"{q.slug}/{parts[1]}/")),)
        if pg.path in by_series:
            return (crumbs_ld(("Collection", ""), ("Series", "series/"), (by_series[pg.path].title, pg.path[:-10])),)
        if pg.path != "index.html" and pg.path.endswith("/index.html") and pg.path.count("/") == 1:
            return (crumbs_ld(("Collection", ""), (html.unescape(pg.title).split(" · ")[0], pg.path[:-10])),)
        return ()
    pages = [pg if pg.ld or pg.path == "404.html" else pg._replace(ld=trail(pg)) for pg in pages]
    drafts = {pg.path: render(pg, "{css}", "{js}") for pg in pages}
    chars = set().union(*(text_of(h) for h in drafts.values())) | {chr(c) for c in range(0x20, 0x7f)}
    rules, files = font_faces(chars)
    (out / "assets" / "fonts").mkdir(parents=True)
    kcss, kfiles = katex_css([drafts[pg.path] for pg in reads if pg.head])
    for f in files + kfiles:
        shutil.copyfile(f, out / "assets" / "fonts" / f.name)
    (out / "assets" / "katex.css").write_text(kcss)
    (out / "assets" / "katex.LICENSE").write_text((KATEX_CSS.parent.parent / "LICENSE").read_text())
    # pdf.js, which a poster page loads to draw a wallpaper, only when it is asked for one
    (out / "assets" / "pdfjs").mkdir()
    for f in PDFJS_FILES:
        if not (PDFJS / f).exists():
            raise SiteError(f"{(PDFJS / f).relative_to(ROOT)} is missing, run `make deps`")
        shutil.copyfile(PDFJS / f, out / "assets" / "pdfjs" / pathlib.PurePath(f).name)
    css = "\n".join(["/* one-page-papers: written by engine/site.py from engine/web/site.css */",
                     mode_css(), *rules, (WEB / "site.css").read_text()])
    js, planner = (WEB / "site.js").read_text(), (WEB / "planner.js").read_text()
    (out / "assets" / "site.css").write_text(css)
    (out / "assets" / "site.js").write_text(js)
    (out / "assets" / "planner.js").write_text(planner)
    css_v, js_v, katex_v, planner_v = (hashlib.sha256(s.encode()).hexdigest()[:10] for s in (css, js, kcss, planner))
    for path, h in drafts.items():
        dst = out / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(h.replace("?v={css}", f"?v={css_v}").replace("?v={js}", f"?v={js_v}")
                        .replace("?v={katex}", f"?v={katex_v}").replace("?v={planner}", f"?v={planner_v}"))

    light_bg, acc = TOKENS["bg"][0], TOKENS["acc"][0]
    ink = TOKENS["ink"][0]
    (out / "favicon.svg").write_text(mark_svg(ink, acc, light_bg).replace(' aria-hidden="true"', "") + "\n")
    # the touch icon, and a 32 px icon for the browsers that do not take an SVG favicon
    icon = Image.new("RGB", (720, 720), light_bg)
    mark = mark_image(6.4)
    icon.paste(mark, ((720 - mark.width) // 2, (720 - mark.height) // 2), mark)
    icon.resize((180, 180), Image.LANCZOS).save(out / "apple-touch-icon.png", optimize=True)
    small = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    mark = mark_image(2.9, bold=True)
    small.paste(mark, ((256 - mark.width) // 2, (256 - mark.height) // 2), mark)
    small.resize((32, 32), Image.LANCZOS).save(out / "favicon-32.png", optimize=True)
    (out / "logo.svg").write_text(mark_svg(ink, acc, light_bg).replace(' aria-hidden="true"', "") + "\n")
    dates, head = last_changes()
    def entry(pg):
        # a poster and its pages date from their paper, a category from its latest poster, the other
        # pages from the repository; a poster page lists the previews of its themes
        top = pg.path.split("/")[0]
        if top in CATEGORIES:
            days = [dates[q.slug] for q in posters if q.category == top and q.slug in dates]
            day = max(days) if days else head
        else:
            day = dates.get(top) or (head if top not in slugs else None)
        mod = f"<lastmod>{day}</lastmod>" if day else ""
        pics = ""
        if top in slugs and pg.path == f"{top}/index.html":
            q = by_slug[top]
            pics = "".join(f"<image:image><image:loc>{BASE_URL}{previews[q.slug, t][1200]}</image:loc></image:image>"
                           for t in dict.fromkeys((q.light, q.dark)))
        return f"<url><loc>{BASE_URL + pg.path.removesuffix('index.html')}</loc>{mod}{pics}</url>\n"
    slugs = set(by_slug)
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "".join(entry(pg) for pg in pages if pg.path != "404.html") + "</urlset>\n")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}sitemap.xml\n")
    notes = sum(len(x.annotations["notes"]) for x in extras.values() if x.annotations)
    return (f"{len(pages)} pages ({len(reads)} to read, {len(series)} series, {len(teach)} teaching kits, "
            f"{notes} margin notes), "
            f"{sum(len(v) for v in previews.values())} previews, "
            f"{len(images)} images, {len(files) + len(kfiles)} font files")

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
            # data-pdf: the PDF that site.js fetches for a wallpaper; data-src-<theme>: the previews of the planner
            if k in ("href", "src", "data-src", "data-pdf") or k.startswith("data-src-"):
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

def pdf_pattern(template=PDF_URL):
    """PDF_URL, or WALL_PDF_URL, as a regular expression, which gives back the category and the file."""
    parts = re.split(r"(\{category\}|\{file\})", template)
    group = {"{category}": "(?P<category>[^/?#]+)", "{file}": r"(?P<file>[^/?#]+\.pdf)"}
    return re.compile("".join(group.get(s, re.escape(s)) for s in parts) + "$")

def check(out):
    """Every problem of the site written in out, as messages."""
    site = "https://site.invalid" + BASE_PATH  # where the check places the site to resolve its URLs
    pdf, wall = pdf_pattern(), pdf_pattern(WALL_PDF_URL)
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
        if GENERATED_IN_REPO.match(url):
            errors.append(f"{path}: {what} {url}: a generated file through the repository, which does not keep it")
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
        elif what.endswith("data-pdf"):  # the only other request: a PDF of dist/, for a wallpaper
            k = wall.match(target)
            if not k:
                errors.append(f"{path}: {what} {url}: not a PDF of dist/ at {WALL_PDF_URL}")
            elif not (ROOT / "dist" / k["category"] / k["file"]).is_file():
                errors.append(f"{path}: {what} {url}: no such file in dist/")
        elif loaded and target != ANALYTICS_SRC:
            errors.append(f"{path}: {what} {url}: loaded from another site")
        elif k := pdf.match(target):
            where = sorted(f for d in PDF_DIRS for f in d.glob(f"{k.groupdict().get('category', '*')}/{k['file']}"))
            if len(where) != 1:
                errors.append(f"{path}: {what} {url}: "
                              f"{'no such file' if not where else 'several files'} in dist/ or release/us/")
    errors += [f"contrast of {t} on {s} in the {m} mode: {r:.2f}, below {MIN_CONTRAST}"
               for m, t, s, r in contrasts() if r < MIN_CONTRAST]
    return errors, len(refs)

def main():
    ap = argparse.ArgumentParser(description="Write the showcase site into site/.")
    ap.add_argument("--check", action="store_true",
                    help="write the site into a temporary directory and check it, leaving site/ untouched")
    ap.add_argument("--only-built", action="store_true",
                    help="leave out the papers whose PDFs are not all in dist/, instead of failing")
    ap.add_argument("--drafts", action="store_true",
                    help="also put on the site the margin notes and teaching kits whose file does not say "
                         "published: true, for review")
    ap.add_argument("--contrast", action="store_true",
                    help="print the contrast ratio of every text colour on every surface, then exit")
    a = ap.parse_args()
    if a.contrast:
        for mode, t, s, r in contrasts():
            print(f"{mode:5}  {t:7} on {s:5}  {r:5.2f}:1  {'ok' if r >= MIN_CONTRAST else 'FAILS'}")
        return
    try:
        posters, skipped = collect(a.only_built)
        series, left = load_series(posters, a.only_built)
        skipped += left
        extras, held = load_extras(posters, a.drafts)
        for msg in skipped:
            print(f"left out: {msg}", file=sys.stderr)
        for w in held:  # a content file without published: true
            print(f"draft, on the site with --drafts only: {w}" if not a.drafts else f"draft, shown: {w}",
                  file=sys.stderr)
        (ROOT / "build").mkdir(exist_ok=True)
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="site-", dir=ROOT / "build"))
        try:
            summary = write(tmp, posters, series, extras)
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
