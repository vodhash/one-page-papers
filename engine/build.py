#!/usr/bin/env python3
"""Build one-page posters.

    python3 engine/build.py                 # every paper, format and theme
    python3 engine/build.py bitcoin         # one paper
    python3 engine/build.py rfc-1925 --formats A --themes blanc genesis
"""
import argparse, importlib.util, json, pathlib, subprocess, sys
import yaml
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENGINE = ROOT / "engine"
sys.path.insert(0, str(ENGINE))
import markdown
from themes import THEMES, FORMATS

DESIGN_W = 594  # every poster is laid out 594 mm wide, then scaled to the target format
MM = 72 / 25.4

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
    r = subprocess.run(["node", str(ENGINE / "katex.js")], input=json.dumps(exprs),
                       capture_output=True, text=True, cwd=ROOT, check=True)
    return json.loads(r.stdout)

def header_html(m):
    h = ['<header>']
    if m.get("kicker"): h.append(f'<div class="kick">{m["kicker"]}</div>')
    h.append(f'<h1>{m.get("title_html", m["title"])}</h1>')
    if m.get("author"): h.append(f'<div class="auth">{m["author"]}</div>')
    if m.get("byline"): h.append(f'<div class="meta">{m["byline"].replace(" · ", " &nbsp;·&nbsp; ")}</div>')
    h.append(f'<div class="rule"><i></i><b>{m.get("emblem", "✦")}</b><i></i></div>')
    h.append('</header>')
    if m.get("abstract"):
        label = m.get("abstract_label", "Abstract.")
        h.append(f'<div class="abs"><b>{label}</b> {markdown.inline(m["abstract"])}</div>')
    return "\n".join(h)

def footer_html(m):
    cells = (m.get("footer") or []) + [""] * 3
    return "<footer>" + "".join(f"<div>{c}</div>" for c in cells[:3]) + "</footer>"

def page_html(paper_dir):
    m = yaml.safe_load((paper_dir / "meta.yaml").read_text())
    body, math = markdown.render((paper_dir / "text.md").read_text(),
                                 load_figures(paper_dir), m.get("numbered", False))
    for i, h in enumerate(katex(math)):
        body = body.replace(f"<!--MATH:{i}-->", h)
    css = paper_dir / "style.css"
    tpl = (ENGINE / "template.html").read_text()
    tpl = (tpl.replace("{{HEADER}}", header_html(m)).replace("{{FOOTER}}", footer_html(m))
              .replace("{{BODY}}", body).replace("{{COLS}}", str(m.get("columns", 4)))
              .replace("{{HS}}", str(m.get("header_scale", 1)))
              .replace("{{TITLE_SIZE}}", m.get("title_size", "76pt"))
              .replace("{{EXTRA_CSS}}", css.read_text() if css.exists() else "")
              .replace("{{NM}}", (ROOT / "node_modules").as_uri()))
    return m, tpl

def fill(tpl, theme, height, fs):
    return (tpl.replace("{{THEME}}", THEMES[theme]).replace("{{PH}}", f"{height:.2f}")
               .replace("{{FS}}", f"{fs}pt"))

def fits(page, tmp, html):
    tmp.write_text(html)
    page.goto(tmp.as_uri()); page.wait_for_timeout(250)
    w, cw, h, ch = page.evaluate("""() => {const m=document.querySelector('main');
        return [m.scrollWidth,m.clientWidth,m.scrollHeight,m.clientHeight]}""")
    return w <= cw + 1 and h <= ch + 1

def best_font(page, tmp, tpl, height, lo, hi):
    """Largest body size (pt) at which the text still fits on the page."""
    for _ in range(10):
        mid = (lo + hi) / 2
        if fits(page, tmp, fill(tpl, "ivoire", height, mid)): lo = mid
        else: hi = mid
    return round(lo - 0.02, 2)

def build(paper, formats, themes, page, previews):
    paper_dir = ROOT / "papers" / paper
    m, tpl = page_html(paper_dir)
    out = ROOT / "dist" / paper; out.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / "build" / f"{paper}.html"; tmp.parent.mkdir(exist_ok=True)
    lo, hi = m.get("font_range", [8, 40])
    for fmt in formats:
        W, H = FORMATS[fmt]
        height = DESIGN_W * H / W
        page.set_viewport_size({"width": round(DESIGN_W / 25.4 * 96), "height": round(height / 25.4 * 96)})
        fs = best_font(page, tmp, tpl, height, lo, hi)
        print(f"{paper} {fmt}: body {fs} pt (design scale)")
        for th in themes:
            tmp.write_text(fill(tpl, th, height, fs))
            page.goto(tmp.as_uri()); page.wait_for_timeout(400)
            raw = ROOT / "build" / "raw.pdf"
            page.pdf(path=str(raw), width=f"{DESIGN_W}mm", height=f"{height:.2f}mm",
                     print_background=True, page_ranges="1")
            pg = PdfReader(raw).pages[0]; pg.scale_to(W * MM, H * MM)
            w = PdfWriter(); w.add_page(pg)
            w.add_metadata({"/Title": m["title"], "/Author": m.get("author", ""),
                            "/Creator": "one-page-papers"})
            dst = out / f"{paper}-{fmt}-{th}.pdf"; w.write(dst); print("  ", dst.relative_to(ROOT))
            if previews and fmt == "A":
                (ROOT / "docs").mkdir(exist_ok=True)
                png = ROOT / "docs" / f"{paper}-{th}.png"
                page.screenshot(path=str(png))
                from PIL import Image
                im = Image.open(png); im.thumbnail((600, 900)); im.save(png, optimize=True)

def main():
    papers = sorted(p.name for p in (ROOT / "papers").iterdir() if (p / "meta.yaml").exists())
    ap = argparse.ArgumentParser()
    ap.add_argument("papers", nargs="*", default=papers)
    ap.add_argument("--formats", nargs="+", default=list(FORMATS))
    ap.add_argument("--themes", nargs="+", default=list(THEMES))
    ap.add_argument("--no-previews", action="store_true")
    a = ap.parse_args()
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 2245, "height": 3179})
        for p in a.papers:
            build(p, a.formats, a.themes, page, not a.no_previews)
        b.close()

if __name__ == "__main__":
    main()
