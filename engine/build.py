#!/usr/bin/env python3
"""Build one-page posters.

    python3 engine/build.py                 # every paper, format and theme
    python3 engine/build.py bitcoin         # one paper
    python3 engine/build.py rfc-1925 --formats A --themes white genesis
    python3 engine/build.py --check         # fit every poster and report problems, no output
"""
import argparse, importlib.util, io, json, pathlib, re, subprocess, sys
import yaml
from PIL import Image
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))
import markdown
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
             "footer", "lang", "license", "themes", "hero_height"}
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
    errors += [f"missing '{k}'" for k in ("title", "license") if not m.get(k)]
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
    return (f'<div class="hero" style="height:{height * share / 100:.2f}mm"><figure class="image {img["mode"]}">'
            f'<div class="imgbox"><img src="{img["src"]}" width="{img["w"]}" height="{img["h"]}" alt="" '
            f'style="--ar:{img["w"] / img["h"]:.5f}"></div>{cap}</figure></div>')

def image_filters(theme):
    """SVG filters for the on_dark modes of images. Chromium drops mix-blend-mode from PDFs, so
    instead of blending with the page they compute the result over its flat paper colour:
    invert turns white into the paper and black into the ink, multiply scales every channel
    by the paper colour."""
    paper, ink = colour(theme, "paper"), colour(theme, "ink")
    invert = " ".join(f"{-(i - p) * .2126:.4f} {-(i - p) * .7152:.4f} {-(i - p) * .0722:.4f} 0 {i:.4f}"
                      for p, i in zip(paper, ink))
    multiply = " ".join(" ".join(f"{p:.4f}" if j == k else "0" for j in range(5)) for k, p in enumerate(paper))
    matrix = lambda name, rows: (f'<filter id="on-dark-{name}" color-interpolation-filters="sRGB">'
                                 f'<feColorMatrix type="matrix" values="{rows} 0 0 0 1 0"/></filter>')
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
            + matrix("invert", invert) + matrix("multiply", multiply) + "</svg>")

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
    values = {"HEADER": header_html(m), "FOOTER": footer_html(m), "BODY": body, "LAYOUT": layout,
              "COLS": m.get("columns", 1 if layout == "centered" else 4), "HS": m.get("header_scale", 1),
              "TITLE_SIZE": m.get("title_size", "76pt"), "LANG": m.get("lang", "en"),
              "EXTRA_CSS": css.read_text() if css.exists() else "",
              "NM": (ROOT / "node_modules").as_uri()}
    def html(theme, height, fs):
        top = hero_html(hero, height, m.get("hero_height", 50)) if hero else ""
        if hero or '<figure class="image ' in body:
            top = image_filters(theme) + top
        return substitute(tpl, {**values, "THEME": THEMES[theme], "THEME_NAME": theme, "HERO": top,
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

def write_pdf(raw, dst, size, m):
    """Scales the PDF printed by Chromium to the target format (width, height in mm)."""
    w = PdfWriter()
    pg = w.add_page(PdfReader(raw).pages[0])
    pg.scale_to(size[0] * MM, size[1] * MM)
    pg.compress_content_streams()  # lossless; pypdf would store the rescaled stream uncompressed
    w.add_metadata({"/Title": m["title"], "/Author": m.get("author", ""), "/Creator": "one-page-papers"})
    w.write(dst)

def save_preview(page, png):
    png.parent.mkdir(exist_ok=True)
    im = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    im.thumbnail((600, 900))
    # at this size a 256-colour palette looks the same and makes the file 2.5 times smaller
    im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(png, optimize=True)

def printed(fmt, fs):
    """Body size once printed: the design is as wide as A1, every format is scaled from it."""
    if fmt == "A":
        return ", ".join(f"A{n} {fs * 2 ** ((1 - n) / 2):.1f}" for n in range(4)) + " pt printed"
    return f"{fs * FORMATS[fmt][0] / DESIGN_W:.1f} pt printed"

def build(paper, formats, themes, page, previews, check):
    paper_dir = ROOT / "papers" / paper
    m = load_meta(paper_dir)
    themes = [t for t in themes if t in m.get("themes", THEMES)]
    if not themes:
        print(f"{paper}: skipped, its themes are {', '.join(m['themes'])}")
        return
    html = poster(paper_dir, m)
    tmp, raw = ROOT / "build" / f"{paper}.html", ROOT / "build" / f"{paper}.pdf"  # per paper, for make -j
    tmp.parent.mkdir(exist_ok=True)
    out = ROOT / "dist" / paper
    lo, hi = m.get("font_range", [8, 40])
    hi = m.get("max_font", hi)
    capped = "max_font" in m or m.get("layout") == "centered"
    for fmt in formats:
        W, H = FORMATS[fmt]
        height = DESIGN_W * H / W
        page.set_viewport_size({"width": round(DESIGN_W * PX), "height": round(height * PX)})
        load(page, tmp, html(themes[0], height, lo))
        fs = best_font(page, lo, hi, f"{paper} {fmt}", capped)
        # the search page keeps the fonts of every size it tried: settle on a size that also
        # fits a freshly loaded page, like the ones that get printed
        for _ in range(100):
            load(page, tmp, html(themes[0], height, fs))
            if fits(page, fs):
                break
            fs = round(fs - 0.01, 2)
        else:
            raise BuildError(f"{paper} {fmt}: no body size fits a freshly loaded page")
        cap = ", the cap" if capped and fs == hi else ""
        print(f"{paper} {fmt}: body {fs:.2f} pt at design size{cap} ({printed(fmt, fs)})")
        for i, th in enumerate(themes):
            load(page, tmp, html(th, height, fs))
            if not fits(page, fs):
                raise BuildError(f"{paper} {fmt} {th}: the text overflows at {fs} pt")
            page.pdf(path=str(raw), width=f"{DESIGN_W}mm", height=f"{height:.2f}mm",
                     print_background=True, page_ranges="1")
            if i == 0:  # themes only change colours, every PDF uses the same fonts
                for font, chars in system_fonts(raw).items():
                    warn(f"{paper} {fmt}: {''.join(sorted(chars))} drawn with {font}, a system font, so the "
                         "PDF depends on the machine; give these characters a bundled font in style.css")
            if check:
                break
            out.mkdir(parents=True, exist_ok=True)
            dst = out / f"{paper}-{fmt}-{th}.pdf"
            write_pdf(raw, dst, (W, H), m)
            print("  ", rel(dst))
            if previews and fmt == "A":
                save_preview(page, ROOT / "docs" / f"{paper}-{th}.png")

def main():
    papers = sorted(p.name for p in (ROOT / "papers").iterdir() if (p / "meta.yaml").exists())
    ap = argparse.ArgumentParser(description="Build one-page posters into dist/ and docs/.")
    ap.add_argument("papers", nargs="*", metavar="paper", help=f"default: every paper ({', '.join(papers)})")
    ap.add_argument("--formats", nargs="+", choices=list(FORMATS), default=list(FORMATS))
    ap.add_argument("--themes", nargs="+", choices=list(THEMES), default=list(THEMES))
    ap.add_argument("--no-previews", action="store_true", help="leave docs/*.png untouched")
    ap.add_argument("--check", action="store_true",
                    help="fit every poster and report problems without touching dist/ or docs/; "
                         "warnings make it fail too")
    a = ap.parse_args()
    if unknown := sorted(set(a.papers) - set(papers)):
        ap.error(f"unknown paper {', '.join(unknown)} (choose from {', '.join(papers)})")
    if not (ROOT / "node_modules").is_dir():
        sys.exit("error: node_modules is missing, run `make deps`")
    failed = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=CHROMIUM_ARGS)
        page = browser.new_page()
        for paper in a.papers or papers:
            try:
                build(paper, a.formats, a.themes, page, not a.no_previews, a.check)
            except BuildError as e:
                failed.append(paper)
                print(f"error: {e}", file=sys.stderr)
        browser.close()
    if failed or (a.check and WARNINGS):
        sys.exit(f"{len(failed)} paper(s) failed, {len(WARNINGS)} warning(s)")

if __name__ == "__main__":
    main()
