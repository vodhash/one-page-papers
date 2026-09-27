#!/usr/bin/env python3
"""Build one-page posters from papers/<category>/<slug>/.

    python3 engine/build.py                 # every paper, format and theme
    python3 engine/build.py bitcoin         # one paper, by slug
    python3 engine/build.py internet        # every paper of a category
    python3 engine/build.py rfc-1925 --formats A --themes white genesis
    python3 engine/build.py --check         # fit every poster and compare it with dist/ and docs/, writing nothing
"""
import argparse, base64, functools, importlib.util, io, json, pathlib, re, subprocess, sys
import yaml
from html import unescape
from PIL import Image
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))
import markdown
from papers import SHOWCASE, discover
from themes import THEMES, FORMATS, colour, dark

DESIGN_W = 594  # every poster is laid out 594 mm wide, then scaled to the target format
MM = 72 / 25.4  # PDF points per mm
PX = 96 / 25.4  # CSS pixels per mm
# Without this flag Chromium lays text out with the hinting of the local fontconfig setup,
# so the fitted size and the line breaks would change from one machine to another.
CHROMIUM_ARGS = ["--font-render-hinting=none"]
BUNDLED_FONTS = ("EBGaramond", "JetBrainsMono", "KaTeX_")  # PostScript names of the node_modules fonts
META_KEYS = {"title", "title_html", "title_size", "kicker", "author", "byline", "emblem", "abstract",
             "abstract_label", "numbered", "columns", "header_scale", "font_range", "max_font", "layout",
             "footer", "lang", "license", "themes", "hero_height", "year", "authors", "min_print", "source",
             "summary"}
LICENSE_KEYS = {"text", "holder", "notice", "basis", "note"}
PRINT_SIZES = ("A3", "A2", "A1", "A0")  # the A file prints at each of them
MIN_BODY = 8  # pt: min_print is the smallest size at which the body prints at least this large
# centered: short texts, one column by default, vertically centered;
# hero: the first image of the text across the top of the page, the text in columns below
LAYOUTS = ("columns", "centered", "hero")
WARNINGS = []

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
    if m.get("summary") and not (isinstance(m["summary"], str) and len(m["summary"].split()) <= 20
                                 and m["summary"].rstrip().endswith(".") and "\n" not in m["summary"].strip()):
        errors.append("summary must be one sentence of 20 words at most")
    if m.get("authors") and not (isinstance(m["authors"], list) and all(isinstance(a, str) for a in m["authors"])):
        errors.append("authors must be a list of names")
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

LOAD_JS = """async () => {
    document.body.offsetHeight;  // lay out first, so that every font in use starts loading
    await document.fonts.ready;
    const faces = [...document.fonts];
    return {loaded: faces.filter(f => f.status === 'loaded').map(f => f.family),
            failed: faces.filter(f => f.status === 'error').map(f => f.family)};
}"""
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
    path.write_text(html)
    page.goto(path.as_uri())
    fonts = page.evaluate(LOAD_JS)
    if fonts["failed"] or not any("EB Garamond" in f for f in fonts["loaded"]):
        missing = ", ".join(sorted(set(fonts["failed"]))) or "EB Garamond"
        raise BuildError(f"fonts did not load ({missing}), run `make deps`")

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

def font_name(font):
    """PostScript name of a PDF font without its subset tag. Chromium embeds some glyphs
    (synthetic bold, for instance) as Type 3 fonts, whose name is only in the descriptor."""
    fd = font.get("/FontDescriptor")
    name = font.get("/BaseFont") or (fd.get_object().get("/FontName") if fd is not None else None)
    return str(name or "an unnamed font").lstrip("/").split("+")[-1]

def system_fonts(pdf):
    """Maps each font of the PDF that does not come from node_modules to the characters it draws."""
    found = {}
    def visit(text, cm, tm, font, size):
        if font is not None and text.strip():
            name = font_name(font)
            if not name.startswith(BUNDLED_FONTS):
                found.setdefault(name, set()).update(c for c in text if not c.isspace())
    PdfReader(pdf).pages[0].extract_text(visitor_text=visit)
    return found

def same_poster(old, new):
    """Whether two PDFs of a poster are the same, but for a jitter of Chromium: now and then, in
    about one print in twenty of a page full of formulas, it sets one run of glyphs of a KaTeX
    formula (in a fraction, or an equation number) on a baseline rounded to a whole pixel, less
    than a pixel away from where the other prints put it. So the text matrices (Tm) of the page
    may differ in their vertical offset by less than a pixel, and everything else must be the same
    byte for byte."""
    if old == new:
        return True
    try:
        a, b = PdfReader(io.BytesIO(old)), PdfReader(io.BytesIO(new))
        ca = a.pages[0].get_contents().get_data().split(b"\n")
        cb = b.pages[0].get_contents().get_data().split(b"\n")
    except Exception:
        return False
    if len(ca) != len(cb):
        return False
    for x, y in zip(ca, cb):
        if x != y:
            tx, ty = x.split(), y.split()
            if not (len(tx) == len(ty) == 7 and tx[6] == ty[6] == b"Tm" and tx[:5] == ty[:5]
                    and abs(float(tx[5]) - float(ty[5])) < 1):
                return False
    def objects(data, r):
        """Every object but the content stream of the page, as the file writes it."""
        skip = r.pages[0].raw_get("/Contents").idnum
        starts = sorted((offset, num) for num, offset in r.xref[0].items())
        ends = [offset for offset, _ in starts[1:]] + [data.rindex(b"\nxref\n")]
        return {num: data[start:end] for (start, num), end in zip(starts, ends) if num != skip}
    return objects(old, a) == objects(new, b)

def write_pdf(raw, dst, size, m):
    """Scales the PDF printed by Chromium to the target format (width, height in mm), into dst,
    a path or a binary stream."""
    w = PdfWriter()
    pg = w.add_page(PdfReader(raw).pages[0])
    pg.scale_to(size[0] * MM, size[1] * MM)
    pg.compress_content_streams()  # lossless; pypdf would store the rescaled stream uncompressed
    w.add_metadata({"/Title": m["title"], "/Author": m.get("author", ""), "/Creator": "one-page-papers"})
    w.write(dst)

def save_preview(page, png):
    png.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    im.thumbnail((600, 900))
    # at this size a 256-colour palette looks the same and makes the file 2.5 times smaller
    im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(png, optimize=True)

def min_print(fs):
    """Smallest ISO A size at which a body of fs pt at design size (A1) prints at MIN_BODY pt or more."""
    return next((a for a in PRINT_SIZES if fs * 2 ** ((1 - int(a[1])) / 2) >= MIN_BODY), None)

def printed(fmt, fs):
    """Body size once printed: the design is as wide as A1, every format is scaled from it."""
    if fmt == "A":
        return ", ".join(f"A{n} {fs * 2 ** ((1 - n) / 2):.1f}" for n in range(4)) + " pt printed"
    return f"{fs * FORMATS[fmt][0] / DESIGN_W:.1f} pt printed"

def themes_of(m):
    """The themes of a paper, in the order of THEMES: the first one makes its thumbnail."""
    return [t for t in THEMES if t in m.get("themes", THEMES)]

def strays(papers):
    """Files of dist/ and docs/ that no paper makes, such as the PDFs of a renamed paper."""
    made = set()
    for p in papers:
        try:
            allowed = themes_of(load_meta(p.dir))
        except BuildError:  # reported by build()
            allowed = THEMES
        made |= {ROOT / "dist" / p.category / f"{p.slug}-{fmt}-{th}.pdf" for fmt in FORMATS for th in allowed}
        made.add(ROOT / "docs" / p.category / f"{p.slug}.png")
        if p.slug == SHOWCASE:
            made |= {ROOT / "docs" / "themes" / f"{th}.png" for th in THEMES}
    found = {f for d in ("dist", "docs") for f in (ROOT / d).rglob("*") if f.is_file() and not f.name.startswith(".")}
    return sorted(found - made)

def build(paper, formats, themes, page, previews, check):
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
    tmp, raw = ROOT / "build" / f"{slug}.html", ROOT / "build" / f"{slug}.pdf"  # per paper, for make -j
    tmp.parent.mkdir(exist_ok=True)
    out = ROOT / "dist" / paper.category
    lo, hi = m.get("font_range", [8, 40])
    hi = m.get("max_font", hi)
    capped = "max_font" in m or m.get("layout") == "centered"
    for fmt in formats:
        W, H = FORMATS[fmt]
        height = DESIGN_W * H / W
        viewport = {"width": round(DESIGN_W * PX), "height": round(height * PX)}
        page.set_viewport_size(viewport)
        load(page, tmp, html(themes[0], height, lo))
        fs = best_font(page, lo, hi, f"{slug} {fmt}", capped)
        fs, fresh = settle(page.context.browser, viewport, tmp, lambda size: html(themes[0], height, size),
                           fs, hi, f"{slug} {fmt}")
        try:
            print_format(paper, m, fmt, fs, themes, allowed, fresh, html, tmp, raw, out, capped and fs == hi,
                         previews, check)
        finally:
            fresh.context.close()

def print_format(paper, m, fmt, fs, themes, allowed, page, html, tmp, raw, out, at_cap, previews, check):
    """Prints the PDFs of one format, and the previews, on the fresh page that settled its size."""
    slug, paper_dir = paper.slug, paper.dir
    W, H = FORMATS[fmt]
    height = DESIGN_W * H / W
    cap = ", the cap" if at_cap else ""
    print(f"{slug} {fmt}: body {fs:.2f} pt at design size{cap} ({printed(fmt, fs)})")
    if fmt == "A" and min_print(fs) != m["min_print"]:
        raise BuildError(f"{rel(paper_dir / 'meta.yaml')}: min_print must be {min_print(fs) or 'larger than A0'}, "
                         f"the smallest size at which the body of {fs:.2f} pt prints at {MIN_BODY} pt or more")
    for i, th in enumerate(themes):
        load(page, tmp, html(th, height, fs))
        if not fits(page, fs):
            raise BuildError(f"{slug} {fmt} {th}: the text overflows at {fs} pt")
        page.pdf(path=str(raw), width=f"{DESIGN_W}mm", height=f"{height:.2f}mm",
                 print_background=True, page_ranges="1")
        if i == 0:  # themes only change colours, every PDF uses the same fonts
            for font, chars in system_fonts(raw).items():
                warn(f"{slug} {fmt}: {''.join(sorted(chars))} drawn with {font}, a system font, so the "
                     "PDF depends on the machine; give these characters a bundled font in style.css")
        dst = out / f"{slug}-{fmt}-{th}.pdf"
        pdf = io.BytesIO()
        write_pdf(raw, pdf, (W, H), m)
        same = dst.exists() and same_poster(dst.read_bytes(), pdf.getvalue())
        if check and not same:
            if dst.exists():  # kept for a look at the difference; the CI uploads build/check/
                kept = ROOT / "build" / "check" / paper.category / dst.name
                kept.parent.mkdir(parents=True, exist_ok=True)
                kept.write_bytes(pdf.getvalue())
                raise BuildError(f"{rel(dst)}: out of date, run `make {slug}` (the new PDF is {rel(kept)})")
            raise BuildError(f"{rel(dst)}: missing, run `make {slug}`")
        if not check:
            if not same:  # an unchanged poster keeps its file, so that git sees no change
                out.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(pdf.getvalue())
            print("  ", rel(dst), "(unchanged)" if same else "")
        if previews and fmt == "A":
            # the thumbnail of the catalog, and the showcase of the themes above it
            pngs = [ROOT / "docs" / paper.category / f"{slug}.png"] if th == allowed[0] else []
            if slug == SHOWCASE:
                pngs.append(ROOT / "docs" / "themes" / f"{th}.png")
            for png in pngs:
                if not check:
                    save_preview(page, png)
                elif not png.exists():
                    raise BuildError(f"{rel(png)}: missing, run `make {slug}`")

def main():
    try:
        papers = discover()
    except ValueError as e:
        sys.exit(f"error: {e}")
    names = sorted({p.slug for p in papers} | {p.category for p in papers})
    ap = argparse.ArgumentParser(description="Build one-page posters into dist/ and docs/.")
    ap.add_argument("names", nargs="*", metavar="paper|category",
                    help=f"slugs or categories, default: every paper ({', '.join(names)})")
    ap.add_argument("--formats", nargs="+", choices=list(FORMATS), default=list(FORMATS))
    ap.add_argument("--themes", nargs="+", choices=list(THEMES), default=list(THEMES))
    ap.add_argument("--no-previews", action="store_true", help="leave docs/*.png untouched")
    ap.add_argument("--check", action="store_true",
                    help="fit every poster and report problems without touching dist/ or docs/: a PDF that "
                         "differs from a fresh build, a missing preview, a file that no paper makes; "
                         "warnings make it fail too")
    a = ap.parse_args()
    if unknown := sorted(set(a.names) - set(names)):
        ap.error(f"unknown paper or category {', '.join(unknown)} (choose from {', '.join(names)})")
    targets = [p for p in papers if not a.names or p.slug in a.names or p.category in a.names]
    if not (ROOT / "node_modules").is_dir():
        sys.exit("error: node_modules is missing, run `make deps`")
    failed = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=CHROMIUM_ARGS)
        page = browser.new_page()
        for paper in targets:
            try:
                build(paper, a.formats, a.themes, page, not a.no_previews, a.check)
            except BuildError as e:
                failed.append(paper.slug)
                print(f"error: {e}", file=sys.stderr)
        browser.close()
    stray = strays(papers) if a.check and not a.names else []
    for f in stray:
        print(f"error: {rel(f)}: made by no paper, remove it", file=sys.stderr)
    if failed or stray or (a.check and WARNINGS):
        sys.exit(f"{len(failed)} paper(s) failed, {len(stray)} stray file(s), {len(WARNINGS)} warning(s)")

if __name__ == "__main__":
    main()
