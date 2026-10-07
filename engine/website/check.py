"""The check of a written site: dead links and anchors, resources from another site, PDFs that
dist/ or release/us/ lack, titles, ids, alt texts and contrast."""
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit

from papers import GENERATED_IN_REPO, ROOT
from .common import ANALYTICS_SRC, BASE_URL, MIN_CONTRAST, PDF_DIRS, PDF_URL, WALL_PDF_URL
from .assets import contrasts
from .pages import BASE_PATH

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
