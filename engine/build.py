#!/usr/bin/env python3
"""Build one-page posters from papers/<category>/<slug>/.

    python3 engine/build.py                 # every paper, format and theme
    python3 engine/build.py bitcoin         # one paper, by slug
    python3 engine/build.py internet        # every paper of a category
    python3 engine/build.py rfc-1925 --formats A --themes white genesis
    python3 engine/build.py --check         # build as CI does: fail on a warning or a missing preview, leave docs/ alone
    python3 engine/build.py --us            # the US formats into release/us/, which git ignores

dist/ and release/ are not in git: the CI builds them, uploads the PDFs of dist/ to the bucket
behind FILES_URL (engine/upload.py) and attaches both to each release. A build keeps what it makes
in a cache, build/cache/ by default (--cache), one entry per paper and format, keyed on the files of
the paper and on those of the engine (ENGINE_FILES): an unchanged poster is copied from there instead
of being laid out again.
"""
import argparse, base64, concurrent.futures, functools, hashlib, importlib.util, io, json, os, pathlib, re, shutil, subprocess, sys
import yaml
from html import unescape
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))
import markdown
from papers import SHOWCASE, discover
from themes import THEMES, FORMATS, US_FORMATS, colour, dark
from onepage_engine import FontLoadError, PX, chromium, design_height, print_pdf, system_fonts, to_format
from onepage_engine import load as load_url

DESIGN_W = 594  # every poster is laid out 594 mm wide, then scaled to the target format
BUNDLED_FONTS = ("EBGaramond", "JetBrainsMono", "KaTeX_")  # PostScript names of the node_modules fonts
META_KEYS = {"title", "title_html", "title_size", "kicker", "author", "byline", "emblem", "abstract",
             "abstract_label", "numbered", "columns", "header_scale", "font_range", "max_font", "layout",
             "footer", "lang", "license", "themes", "hero_height", "year", "authors", "min_print", "source",
             "summary", "contributors",
             "commercial", "commercial_basis"}
LICENSE_KEYS = {"text", "holder", "notice", "basis", "note"}
PRINT_SIZES = ("A3", "A2", "A1", "A0")  # the A file prints at each of them
MIN_BODY = 8  # pt: min_print is the smallest size at which the body prints at least this large
# font_range is tuned on the formats of dist/: a US format, whose ratio differs, may fit the text
# only below its minimum (Letter is squatter than A), or leave space above its maximum (Tabloid is
# taller); there the minimum falls to this size and the maximum is a ceiling, not a warning
US_MIN_FONT = 4
# centered: short texts, one column by default, vertically centered;
# hero: the first image of the text across the top of the page, the text in columns below
LAYOUTS = ("columns", "centered", "hero")
WARNINGS = []
SIZES = {**FORMATS, **US_FORMATS}  # every format the engine prints, (width, height) in mm

# the files of the engine that a poster depends on: a change to one of them builds every poster again
ENGINE_FILES = ("engine/build.py", "engine/markdown.py", "engine/svg.py", "engine/themes.py", "engine/papers.py",
                "engine/katex.js", "engine/template.html", "engine/pyproject.toml", "engine/onepage_engine/*.py",
                "package-lock.json", "requirements.txt")
CACHE_VERSION = "1"  # part of every cache key: raise it when what a cache entry holds changes

def out_dir(paper, fmt):
    """Where the PDFs of a format go: dist/ for the versioned formats, release/us/ for the others."""
    return ROOT / ("dist" if fmt in FORMATS else "release/us") / paper.category

class BuildError(Exception):
    pass

def warn(msg):
    WARNINGS.append(msg)
    print(f"warning: {msg}", file=sys.stderr)

def rel(path):
    return path.relative_to(ROOT)

def load_meta(paper_dir):
    path = paper_dir / "meta.yaml"
    m = yaml.safe_load(path.read_text()) or {}
    errors = [f"unknown key '{k}'" for k in sorted(set(m) - META_KEYS)]
    errors += [f"missing '{k}'" for k in ("title", "summary", "license", "year", "authors", "min_print", "source")
               if not m.get(k)]
    if not isinstance(m.get("commercial"), bool) or not isinstance(m.get("commercial_basis"), str) \
            or not m["commercial_basis"].strip():
        errors.append("commercial must be true or false, whether the licenses of the text and of every image "
                      "allow selling prints, with the reason in commercial_basis")
    if m.get("summary") and not (isinstance(m["summary"], str) and len(m["summary"].split()) <= 20
                                 and m["summary"].rstrip().endswith(".") and "\n" not in m["summary"].strip()):
        errors.append("summary must be one sentence of 20 words at most")
    if m.get("authors") and not (isinstance(m["authors"], list) and all(isinstance(a, str) for a in m["authors"])):
        errors.append("authors must be a list of names")
    handles = m.get("contributors", [])
    if not (isinstance(handles, list) and all(isinstance(h, str) and re.fullmatch(r"[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}", h)
                                             for h in handles)):
        errors.append("contributors must be a list of GitHub user names, without @")
    if m.get("year") and not isinstance(m["year"], (int, str)):
        errors.append("year must be a number, or a text such as \"c. 400 BC\"")
    if m.get("min_print") and m["min_print"] not in PRINT_SIZES:
        errors.append(f"min_print must be one of {', '.join(PRINT_SIZES)}")
    src = m.get("source")
    if src and not (isinstance(src, dict) and set(src) == {"url", "retrieved", "edition"} and all(src.values())):
        errors.append("source needs exactly url, retrieved (a date) and edition")
    lic = m.get("license")
    if lic and not (isinstance(lic, dict) and lic.get("text") and (lic.get("notice") or lic.get("basis"))
                    and set(lic) <= LICENSE_KEYS):
        errors.append("license needs text, and either notice (the license or permission, word for word) or "
                      f"basis (why the text is in the public domain); its keys are {', '.join(sorted(LICENSE_KEYS))}")
    if len(m.get("footer") or []) > 3:
        errors.append("footer takes at most 3 cells")
    fr = m.get("font_range", [8, 40])
    if not (isinstance(fr, list) and len(fr) == 2 and all(isinstance(v, (int, float)) for v in fr)
            and 0 < fr[0] < fr[1]):
        errors.append("font_range must be [min, max] in pt")
    elif not isinstance(m.get("max_font", fr[1]), (int, float)) or m.get("max_font", fr[1]) <= fr[0]:
        errors.append("max_font must be a size in pt above the minimum of font_range")
    if m.get("layout", "columns") not in LAYOUTS:
        errors.append(f"layout must be one of {', '.join(LAYOUTS)}")
    themes = m.get("themes", list(THEMES))
    if not (isinstance(themes, list) and themes and set(themes) <= set(THEMES)):
        errors.append(f"themes must be a list of some of {', '.join(THEMES)}")
    if not isinstance(m.get("hero_height", 50), (int, float)) or not 10 <= m.get("hero_height", 50) <= 90:
        errors.append("hero_height must be a percentage of the page height, from 10 to 90")
    if errors:
        raise BuildError(f"{rel(path)}: {'; '.join(errors)}")
    return m

def load_figures(paper_dir):
    f = paper_dir / "figures.py"
    if not f.exists():
        return {}
    spec = importlib.util.spec_from_file_location(f"figures_{paper_dir.name}", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.FIGS

def katex(exprs):
    if not exprs:
        return []
    try:
        r = subprocess.run(["node", str(ENGINE / "katex.js")], input=json.dumps(exprs),
                           capture_output=True, text=True, cwd=ROOT)
    except FileNotFoundError:
        raise BuildError("rendering math needs Node.js, which is not installed") from None
    if r.returncode:
        raise BuildError(f"KaTeX: {r.stderr.strip()}")
    return json.loads(r.stdout)

def header_html(m):
    h = ['<header>']
    if m.get("kicker"): h.append(f'<div class="kick">{m["kicker"]}</div>')
    h.append(f'<h1>{m.get("title_html", m["title"])}</h1>')
    if m.get("author"): h.append(f'<div class="auth">{m["author"]}</div>')
    if m.get("byline"): h.append(f'<div class="meta">{m["byline"].replace(" · ", " &nbsp;·&nbsp; ")}</div>')
    h.append(f'<div class="rule"><i></i><b>{m.get("emblem", "¶")}</b><i></i></div>')
    h.append('</header>')
    if m.get("abstract"):
        label = m.get("abstract_label", "Abstract.")
        h.append(f'<div class="abs"><b>{label}</b> {markdown.inline(m["abstract"])}</div>')
    return "\n".join(h)

def footer_html(m):
    cells = (m.get("footer") or []) + [""] * 3
    return "<footer>" + "".join(f"<div>{c}</div>" for c in cells[:3]) + "</footer>"

def substitute(tpl, values):
    """Fills every {{KEY}} in one pass, so text inserted in the page is never read as a placeholder."""
    return re.sub(r"\{\{(\w+)\}\}", lambda k: str(values[k.group(1)]), tpl)

def hero_html(img, height, share):
    """The hero block: a fixed share of the page height, so that fitting the body size only moves
    the text. Inside it, the image takes the room that its caption leaves (.hero in the template)."""
    if not img["w"]:
        raise BuildError("the hero image must state its size (an SVG needs a viewBox)")
    cap = f'<figcaption>{img["caption"]}</figcaption>' if img["caption"] else ""
    return (f'<div class="hero" style="height:{height * share / 100:.2f}mm"><figure {markdown.figure_attrs(img)}>'
            f'<div class="imgbox"><img src="{img["src"]}" width="{img["w"]}" height="{img["h"]}" alt="" '
            f'style="--ar:{img["w"] / img["h"]:.5f}"></div>{cap}</figure></div>')

@functools.lru_cache(maxsize=None)
def treated(path, mode, theme):
    """The image at path, as a data URI, with the treatment that the page gives it on a theme.
    Chromium drops mix-blend-mode from PDFs, so the result is computed over the flat paper colour:
    on a dark paper, invert takes the luminance of the image from the ink (black) to the paper
    (white); on a light one, multiply scales every channel by the paper colour. Doing it here
    rather than with an SVG filter keeps the image as it is in the PDF: Chromium rasterizes a
    filtered image losslessly at print resolution, 7 MB for the photograph of a plate. A JPEG
    stays a JPEG, other images become PNG, with a palette when they have 256 colours or fewer."""
    im = Image.open(path)
    alpha = None
    if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
        im = im.convert("RGBA")
        alpha = im.getchannel("A")
    rgb = im.convert("RGB")
    paper = colour(theme, "paper")
    if mode == "invert":
        lum = rgb.convert("L", (.2126, .7152, .0722, 0))
        bands = [lum.point([round(255 * i + (p - i) * v) for v in range(256)])
                 for p, i in zip(paper, colour(theme, "ink"))]
    else:
        bands = [band.point([round(v * p) for v in range(256)]) for band, p in zip(rgb.split(), paper)]
    out = Image.merge("RGB", bands)
    buf = io.BytesIO()
    if path.suffix.lower() in (".jpg", ".jpeg") and alpha is None:
        out.save(buf, "JPEG", quality=92)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    if alpha is not None:
        out.putalpha(alpha)
    elif colours := out.getcolors(256):  # an exact palette: every colour of the image is in it
        pal = Image.new("P", (1, 1))
        pal.putpalette([c for _, rgb3 in colours for c in rgb3])
        out = out.quantize(palette=pal, dither=Image.Dither.NONE)
    out.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

TREATABLE = re.compile(r'(<figure class="image" data-dark="(\w+)"(?: data-light="(\w+)")? data-file="([^"]+)"'
                       r'[^>]*>(?:<div class="imgbox">)?<img src=")[^"]+"')

def treat_images(page_html, paper_dir, theme):
    """page_html with the on_dark=invert and on_light=multiply images of the theme treated. SVG
    images keep the filters of image_filters, since they are not rasterized here."""
    def sub(mt):
        mode = ("invert" if mt.group(2) == "invert" else None) if dark(theme) else \
               ("multiply" if mt.group(3) == "multiply" and colour(theme, "paper") != (1, 1, 1) else None)
        path = paper_dir / unescape(mt.group(4))
        if mode is None or path.suffix.lower() == ".svg":
            return mt.group(0)
        return mt.group(1) + treated(path, mode, theme) + '"'
    return TREATABLE.sub(sub, page_html)

def image_filters(theme):
    """SVG filters for the on_dark and on_light treatments of SVG images, with the rules that use
    them; raster images are treated by treated() instead. On a dark paper, invert turns white into
    the paper and black into the ink; on a light one, multiply scales every channel by the paper
    colour, which leaves a white paper unchanged, so no filter at all is used there."""
    paper = colour(theme, "paper")
    if dark(theme):
        name, rows = "on-dark-invert", " ".join(
            f"{-(i - p) * .2126:.4f} {-(i - p) * .7152:.4f} {-(i - p) * .0722:.4f} 0 {i:.4f}"
            for p, i in zip(paper, colour(theme, "ink")))
        rule = f'figure[data-dark=invert] img[src^="data:image/svg"]{{filter:url(#{name})}}'
    elif paper != (1, 1, 1):
        name, rows = "on-light-multiply", " ".join(
            " ".join(f"{p:.4f}" if j == k else "0" for j in range(5)) for k, p in enumerate(paper))
        rule = f'figure[data-light=multiply] img[src^="data:image/svg"]{{filter:url(#{name})}}'
    else:
        return ""
    return (f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
            # the filter region stops at the image: by default it adds a transparent black margin,
            # which some PDF viewers blend into a dark hairline when they scale the image down
            f'<filter id="{name}" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB">'
            f'<feColorMatrix type="matrix" values="{rows} 0 0 0 1 0"/></filter></svg><style>{rule}</style>')

def poster(paper_dir, m):
    """Returns html(theme, page height in mm, body size in pt), the page of the poster."""
    text = paper_dir / "text.md"
    layout = m.get("layout", "columns")
    try:
        body, tex, hero = markdown.render(text.read_text(), load_figures(paper_dir), m.get("numbered", False),
                                          assets=paper_dir, hero=layout == "hero")
    except markdown.MarkdownError as e:
        raise BuildError(f"{rel(text)}:{e.line}: {e.msg}") from None
    if layout == "hero" and not hero:
        raise BuildError(f"{rel(text)}: layout: hero takes the first ::: image of the text, and there is none")
    for i, h in enumerate(katex(tex)):
        body = body.replace(f"<!--MATH:{i}-->", h)
    css = paper_dir / "style.css"
    tpl = (ENGINE / "template.html").read_text()
    values = {"HEADER": header_html(m), "FOOTER": footer_html(m), "LAYOUT": layout,
              "COLS": m.get("columns", 1 if layout == "centered" else 4), "HS": m.get("header_scale", 1),
              "TITLE_SIZE": m.get("title_size", "76pt"), "LANG": m.get("lang", "en"),
              "EXTRA_CSS": css.read_text() if css.exists() else "",
              "NM": (ROOT / "node_modules").as_uri()}
    def html(theme, height, fs):
        top = treat_images(hero_html(hero, height, m.get("hero_height", 50)), paper_dir, theme) if hero else ""
        if hero or '<figure class="image"' in body:
            top = image_filters(theme) + top
        return substitute(tpl, {**values, "BODY": treat_images(body, paper_dir, theme), "THEME": THEMES[theme],
                                "THEME_NAME": theme, "HERO": top,
                                "TONE": "dark" if dark(theme) else "light", "PH": f"{height:.2f}", "FS": f"{fs}pt"})
    return html

FITS_JS = """async fs => {
    document.documentElement.style.setProperty('--fs', fs + 'pt');
    document.body.offsetHeight;
    await document.fonts.ready;
    const m = document.querySelector('main');
    // code blocks clip their overflow, grid cells and the hero spill into their neighbours: all must fit too
    const spilt = [...document.querySelectorAll('pre, .cell')].some(e => e.scrollWidth > e.clientWidth + 1)
        || [...document.querySelectorAll('.hero')].some(e => e.scrollHeight > e.clientHeight + 1);
    return !spilt && m.scrollWidth <= m.clientWidth + 1 && m.scrollHeight <= m.clientHeight + 1;
}"""

def load(page, path, html):
    """Writes html to path and opens it in page, once its fonts, EB Garamond first, have loaded."""
    path.write_text(html)
    try:
        load_url(page, path.as_uri(), required_fonts=("EB Garamond",))
    except FontLoadError as e:
        raise BuildError(f"fonts did not load ({e.missing}), run `make deps`") from None

def fits(page, fs):
    """Whether the text fits on the loaded page at body size fs (pt)."""
    return page.evaluate(FITS_JS, fs)

def best_font(page, lo, hi, what, capped):
    """Largest body size at which the text still fits on the loaded page, in whole hundredths
    of a point. When capped, hi is a deliberate ceiling and reaching it is not a problem.
    Chromium lays a size out with the font of a previous size less than about 0.01 px away,
    so candidates that are not on a 0.01 pt grid can be measured with the wrong glyph widths."""
    lo, hi = round(lo * 100), round(hi * 100)
    if not fits(page, lo / 100):
        raise BuildError(f"{what}: the text overflows even at {lo / 100} pt, lower font_range in meta.yaml")
    if fits(page, hi / 100):
        if not capped:
            warn(f"{what}: the text still fits at {hi / 100} pt and leaves space, raise font_range in meta.yaml")
        return hi / 100
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if fits(page, mid / 100): lo = mid
        else: hi = mid
    return lo / 100

def settle(browser, viewport, tmp, html, fs, hi, what):
    """The largest size on the 0.01 pt grid, from fs up or down, at which the text fits a page
    that has laid out nothing else, and that page, in a browser context of its own: a new
    renderer process. On the search page a size can fit or not depending on the fonts that the
    sizes tried before it left in the cache, since Chromium reuses the font of a size less than
    0.01 px away, and the em-based sizes of KaTeX (subscripts at 0.7 em, for instance) come that
    close from one candidate to the next. Settled and printed on fresh pages, a poster no longer
    depends on the history of the renderer."""
    def trial(size):
        page = browser.new_context(viewport=viewport).new_page()
        load(page, tmp, html(size))
        if fits(page, size):
            return page
        page.context.close()
    if page := trial(fs):
        while fs < hi and (bigger := trial(round(fs + 0.01, 2))):
            page.context.close()
            page, fs = bigger, round(fs + 0.01, 2)
        return fs, page
    for _ in range(100):
        fs = round(fs - 0.01, 2)
        if page := trial(fs):
            return fs, page
    raise BuildError(f"{what}: no body size fits a freshly loaded page")

def preview(page):
    """The PNG of a preview of the loaded page."""
    im = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    im.thumbnail((600, 900))
    # at this size a 256-colour palette looks the same and makes the file 2.5 times smaller
    buf = io.BytesIO()
    im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(buf, "PNG", optimize=True)
    return buf.getvalue()

def save_preview(png, data):
    if not png.exists() or png.read_bytes() != data:  # an unchanged preview keeps its file
        png.parent.mkdir(parents=True, exist_ok=True)
        png.write_bytes(data)

def min_print(fs):
    """Smallest ISO A size at which a body of fs pt at design size (A1) prints at MIN_BODY pt or more."""
    return next((a for a in PRINT_SIZES if fs * 2 ** ((1 - int(a[1])) / 2) >= MIN_BODY), None)

def printed(fmt, fs):
    """Body size once printed: the design is as wide as A1, every format is scaled from it."""
    if fmt == "A":
        return ", ".join(f"A{n} {fs * 2 ** ((1 - n) / 2):.1f}" for n in range(4)) + " pt printed"
    return f"{fs * SIZES[fmt][0] / DESIGN_W:.1f} pt printed"

def themes_of(m):
    """The themes of a paper, in the order of THEMES: the first one makes its thumbnail."""
    return [t for t in THEMES if t in m.get("themes", THEMES)]

def strays(papers):
    """Previews of docs/ that no paper makes, such as the one of a renamed paper."""
    made = set()
    for p in papers:
        made.add(ROOT / "docs" / p.category / f"{p.slug}.png")
        if p.slug == SHOWCASE:
            made |= {ROOT / "docs" / "themes" / f"{th}.png" for th in THEMES}
    found = {f for f in (ROOT / "docs").rglob("*") if f.is_file() and not f.name.startswith(".")}
    return sorted(found - made)

@functools.cache
def engine_key():
    h = hashlib.sha256(CACHE_VERSION.encode())
    for pattern in ENGINE_FILES:
        for f in sorted(ROOT.glob(pattern)):
            h.update(f"{rel(f)}\0".encode() + f.read_bytes() + b"\0")
    return h.hexdigest()

def paper_key(paper_dir):
    """The key of the cache entries of a paper: its files and those of the engine."""
    h = hashlib.sha256(engine_key().encode())
    for f in sorted(f for f in paper_dir.rglob("*") if f.is_file() and "__pycache__" not in f.parts):
        h.update(f"{f.relative_to(paper_dir)}\0".encode() + f.read_bytes() + b"\0")
    return h.hexdigest()[:32]

class Cache:
    """What a build made for one paper and one format: its PDFs, its previews and the lines it
    printed, in <dir>/<slug>/<format>/<key>/. Storing an entry removes the older keys of that
    paper and format; files are written under a temporary name, then renamed."""
    def __init__(self, root, slug, fmt, key):
        self.dir = root / slug / fmt / key if root else None

    def get(self, names):
        """The path of each of names, or None when one of them is missing."""
        if not self.dir or not all((self.dir / n).is_file() for n in names):
            return None
        return {n: self.dir / n for n in names}

    def put(self, files):
        """Stores files, {name: bytes}."""
        if not self.dir:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            tmp = self.dir / f".{name}.{os.getpid()}"
            tmp.write_bytes(data)
            tmp.replace(self.dir / name)
        for old in self.dir.parent.iterdir():
            if old != self.dir:
                shutil.rmtree(old, ignore_errors=True)

def build(paper, formats, themes, page, previews, check, cache_root=None):
    """Writes the PDFs and the previews of a paper. With check, writes nothing and fails when a
    PDF of dist/ differs from the one it would write or when a preview is missing: previews
    are only checked for presence, since screenshots may differ from one machine to another."""
    paper_dir, slug = paper.dir, paper.slug
    m = load_meta(paper_dir)
    allowed = themes_of(m)
    if slug == SHOWCASE and allowed != list(THEMES):
        raise BuildError(f"{rel(paper_dir / 'meta.yaml')}: {slug} shows every theme in the README, "
                         "so it cannot restrict its themes")
    themes = [t for t in themes if t in allowed]
    if not themes:
        print(f"{slug}: skipped, its themes are {', '.join(allowed)}")
        return
    html = poster(paper_dir, m)
    key = paper_key(paper_dir) if cache_root else None
    # per paper and per process, so that two builds of the same paper at once cannot mix their files
    tmp, raw = (ROOT / "build" / f"{slug}-{os.getpid()}{ext}" for ext in (".html", ".pdf"))
    tmp.parent.mkdir(exist_ok=True)
    lo, hi = m.get("font_range", [8, 40])
    hi = m.get("max_font", hi)
    capped = "max_font" in m or m.get("layout") == "centered"
    try:
        for fmt in formats:
            cache = Cache(cache_root, slug, fmt, key)
            if not from_cache(paper, fmt, themes, allowed, previews, check, cache):
                build_format(paper, m, fmt, themes, allowed, page, html, tmp, raw, lo, hi, capped, previews, check,
                             cache)
    finally:
        tmp.unlink(missing_ok=True)
        raw.unlink(missing_ok=True)

def preview_names(paper, fmt, th, allowed, previews):
    """The previews that the PDF of a theme makes, as {name in the cache: path in docs/}: the
    thumbnail of the catalog, and the showcase of the themes above it."""
    if not previews or fmt != "A":
        return {}
    out = {"preview.png": ROOT / "docs" / paper.category / f"{paper.slug}.png"} if th == allowed[0] else {}
    if paper.slug == SHOWCASE:
        out[f"theme-{th}.png"] = ROOT / "docs" / "themes" / f"{th}.png"
    return out

def from_cache(paper, fmt, themes, allowed, previews, check, cache):
    """Copies the PDFs of a format from the cache, when it holds all of them. A preview is only
    written when docs/ lacks it, so that one made on another machine keeps its file."""
    slug = paper.slug
    pdfs = {f"{slug}-{fmt}-{th}.pdf": th for th in themes}
    pngs = {n: png for th in themes for n, png in preview_names(paper, fmt, th, allowed, previews).items()}
    hit = cache.get([*pdfs, *pngs, "log.json"])
    if not hit:
        return False
    log = json.loads(hit["log.json"].read_text())
    print(f"{log['line']} (cached)")
    for w in log["warnings"]:
        warn(w)
    out = out_dir(paper, fmt)
    out.mkdir(parents=True, exist_ok=True)
    for name in pdfs:
        shutil.copyfile(hit[name], out / name)
    for name, png in pngs.items():
        if check and not png.exists():
            raise BuildError(f"{rel(png)}: missing, run `make {slug}`")
        if not png.exists():
            png.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(hit[name], png)
    return True

def build_format(paper, m, fmt, themes, allowed, page, html, tmp, raw, lo, hi, capped, previews, check, cache):
    """Settles the body size of one format, then prints its PDFs (print_format) and keeps them in
    the cache."""
    slug = paper.slug
    W, H = SIZES[fmt]
    height = design_height(DESIGN_W, (W, H))
    viewport = {"width": round(DESIGN_W * PX), "height": round(height * PX)}
    page.set_viewport_size(viewport)
    us = fmt in US_FORMATS
    low = min(lo, US_MIN_FONT) if us else lo
    load(page, tmp, html(themes[0], height, low))
    fs = best_font(page, low, hi, f"{slug} {fmt}", capped or us)
    fs, fresh = settle(page.context.browser, viewport, tmp, lambda size: html(themes[0], height, size),
                       fs, hi, f"{slug} {fmt}")
    warned = len(WARNINGS)
    try:
        line, made = print_format(paper, m, fmt, fs, themes, allowed, fresh, html, tmp, raw, out_dir(paper, fmt),
                                  (capped or us) and fs == hi, previews, check)
    finally:
        fresh.context.close()
    cache.put({**made, "log.json": json.dumps({"line": line, "warnings": WARNINGS[warned:]}).encode()})

def print_format(paper, m, fmt, fs, themes, allowed, page, html, tmp, raw, out, at_cap, previews, check):
    """Prints the PDFs of one format, and the previews, on the fresh page that settled its size.
    With check, a missing preview is an error and docs/ is left alone. Returns the line printed
    about the format and what was made, {name in the cache: bytes}."""
    slug, paper_dir = paper.slug, paper.dir
    W, H = SIZES[fmt]
    height = design_height(DESIGN_W, (W, H))
    cap = ", the cap" if at_cap else ""
    line = f"{slug} {fmt}: body {fs:.2f} pt at design size{cap} ({printed(fmt, fs)})"
    print(line)
    made = {}
    if fmt == "A" and min_print(fs) != m["min_print"]:
        raise BuildError(f"{rel(paper_dir / 'meta.yaml')}: min_print must be {min_print(fs) or 'larger than A0'}, "
                         f"the smallest size at which the body of {fs:.2f} pt prints at {MIN_BODY} pt or more")
    for i, th in enumerate(themes):
        load(page, tmp, html(th, height, fs))
        if not fits(page, fs):
            raise BuildError(f"{slug} {fmt} {th}: the text overflows at {fs} pt")
        print_pdf(page, DESIGN_W, height, path=raw)
        if i == 0:  # themes only change colours, every PDF uses the same fonts
            for font, chars in system_fonts(raw, BUNDLED_FONTS).items():
                warn(f"{slug} {fmt}: {''.join(sorted(chars))} drawn with {font}, a system font, so the "
                     "PDF depends on the machine; give these characters a bundled font in style.css")
        dst = out / f"{slug}-{fmt}-{th}.pdf"
        pdf = to_format(raw, (W, H), title=m["title"], author=m.get("author", ""), creator="one-page-papers")
        out.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(pdf)
        made[dst.name] = pdf
        print("  ", rel(dst))
        for name, png in preview_names(paper, fmt, th, allowed, previews).items():
            if check and not png.exists():
                raise BuildError(f"{rel(png)}: missing, run `make {slug}`")
            made[name] = preview(page)
            if not check:
                save_preview(png, made[name])
    return line, made

def build_all(targets, a):
    """Builds the papers of targets in one browser. Returns the slugs that failed and the warnings."""
    failed = []
    with chromium() as browser:
        page = browser.new_page()
        for paper in targets:
            try:
                build(paper, a.formats, a.themes, page, not a.no_previews, a.check, a.cache)
            except BuildError as e:
                failed.append(paper.slug)
                print(f"error: {e}", file=sys.stderr, flush=True)
    return failed, list(WARNINGS)

def main():
    try:
        papers = discover()
    except ValueError as e:
        sys.exit(f"error: {e}")
    names = sorted({p.slug for p in papers} | {p.category for p in papers})
    ap = argparse.ArgumentParser(description="Build one-page posters into dist/, and their previews into docs/.")
    ap.add_argument("names", nargs="*", metavar="paper|category",
                    help=f"slugs or categories, default: every paper ({', '.join(names)})")
    ap.add_argument("--formats", nargs="+", choices=list(SIZES),
                    help=f"default: {' '.join(FORMATS)}, or {' '.join(US_FORMATS)} with --us")
    ap.add_argument("--us", action="store_true",
                    help=f"the US formats ({', '.join(US_FORMATS)}) instead, into release/us/<category>/, "
                         "which git ignores; no previews")
    ap.add_argument("--themes", nargs="+", choices=list(THEMES), default=list(THEMES))
    ap.add_argument("--no-previews", action="store_true", help="leave docs/*.png untouched")
    ap.add_argument("--jobs", "-j", type=int, default=1, metavar="N",
                    help="build N papers at a time, each in a browser of its own (default 1)")
    ap.add_argument("--check", action="store_true",
                    help="build as the CI does, leaving docs/ untouched: fail on a missing preview, on a preview "
                         "that no paper makes and on any warning")
    ap.add_argument("--cache", type=pathlib.Path, default=ROOT / "build" / "cache", metavar="DIR",
                    help="where to keep what each build makes, and to take the unchanged posters from "
                         "(default build/cache/)")
    ap.add_argument("--no-cache", action="store_true", help="lay out every poster, and keep nothing")
    a = ap.parse_args()
    a.cache = None if a.no_cache else a.cache.resolve()
    us = [f for f in a.formats or [] if f in US_FORMATS]
    if a.us and a.formats and len(us) < len(a.formats):
        ap.error(f"--us builds only the US formats ({', '.join(US_FORMATS)})")
    a.formats = a.formats or list(US_FORMATS if a.us else FORMATS)
    if unknown := sorted(set(a.names) - set(names)):
        ap.error(f"unknown paper or category {', '.join(unknown)} (choose from {', '.join(names)})")
    targets = [p for p in papers if not a.names or p.slug in a.names or p.category in a.names]
    if not (ROOT / "node_modules").is_dir():
        sys.exit("error: node_modules is missing, run `make deps`")
    jobs = max(1, min(a.jobs, len(targets)))
    if jobs == 1:
        failed, warnings = build_all(targets, a)
    else:  # every worker has a browser of its own and takes one paper in jobs, which keeps them all busy
        with concurrent.futures.ProcessPoolExecutor(jobs) as ex:
            done = list(ex.map(build_all, [targets[i::jobs] for i in range(jobs)], [a] * jobs))
        failed, warnings = [f for d in done for f in d[0]], [w for d in done for w in d[1]]
    WARNINGS[:] = warnings
    stray = strays(papers) if a.check and not a.names and not a.us else []
    for f in stray:
        print(f"error: {rel(f)}: made by no paper, remove it", file=sys.stderr)
    if failed or stray or (a.check and WARNINGS):
        sys.exit(f"{len(failed)} paper(s) failed, {len(stray)} stray file(s), {len(WARNINGS)} warning(s)")

if __name__ == "__main__":
    main()
