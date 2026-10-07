#!/usr/bin/env python3
"""The showcase site of the collection, for GitHub Pages: static pages written from the
meta.yaml of every paper, with previews rasterized from its A PDFs in dist/ (built by build.py, not
kept in git: the PDFs are served from FILES_URL, where the CI uploads them), and a reading page
for each paper (<slug>/read/), its text rendered by markdown.py and KaTeX as for its poster, and a
page for each series of series.yaml (series/<slug>/), with a wall planner (planner.js), and a guide
to having a poster printed (print/). see-also.yaml links some poster pages to a site that belongs
with them (plain links, without tracking).

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
fetches to draw a wallpaper (WALL_PDF_URL), on a PDF link whose file is not in dist/ or release/us/
or that lacks the version of its PDFs (?v=), and on a link to a generated file through the repository
(GENERATED_IN_REPO), which git does not keep. Links inside the site are relative, so that it works at
https://onepagepapers.com/ (GitHub Pages) as well as at the root of `make serve`. Previews need
pdftoppm (poppler-utils); they are cached in build/site-previews/, keyed on the content of each PDF,
so an unchanged collection builds fast.

The pages are written by the modules of engine/website/; this script reads the options, writes the
site into a temporary folder, checks it, then puts it in site/.
"""
import argparse, concurrent.futures, hashlib, html, os, pathlib, shutil, subprocess, sys, tempfile

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from papers import CATEGORIES, ROOT, SHOWCASE
from website.assets import KATEX_CSS, PDFJS, PDFJS_FILES, contrasts, font_faces, katex_css, mode_css, text_of
from website.check import check
from website.common import BASE_URL, MIN_CONTRAST, TOKENS, WEB, SiteError, mark_svg
from website.content import collect, load_extras, load_series
from website.images import make_previews, make_thumbs, mark_image, prune, share_image
from website.pages import (about_page, category_page, crumbs_ld, home_page, not_found_page, poster_page, print_page,
                           render, series_index_page, series_page)
from website.reading import read_page, teach_page, texts

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
