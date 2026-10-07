"""Where the papers live, papers/<category>/<slug>/, the category coming from the folder; what the
meta.yaml of each one holds; and where its PDFs go. build.py, readme.py and the site share them."""
import pathlib, re
from typing import NamedTuple

import yaml

from themes import THEMES

ROOT = pathlib.Path(__file__).resolve().parent.parent
# folder name: title in the README, in the order of the README
CATEGORIES = {
    "crypto": "Cryptography & Bitcoin",
    "computing": "Computing pioneers",
    "internet": "Internet & networking",
    "software": "Software practice",
    "manifestos": "Manifestos & announcements",
    "physics": "Physics & astronomy",
    "space": "Space exploration",
    "mathematics": "Mathematics",
    "life-sciences": "Biology & medicine",
    "data-viz": "Historical data visualization",
    "patents": "Patents",
    "history": "History & philosophy",
    "reference": "Reference sheets",
}
SHOWCASE = "bitcoin"  # the paper that the catalog of the README shows in every theme
SITE_URL = "https://onepagepapers.com/"  # the site, on GitHub Pages
# the PDFs of dist/, which git does not keep: the CI builds them and uploads them to the bucket
# served here (engine/upload.py), as <category>/<paper>-<format>-<theme>.pdf (PDF_URL)
FILES_URL = "https://files.onepagepapers.com/"
PDF_URL = FILES_URL + "{category}/{file}"
# a link to a file that git does not keep (dist/, release/, site/, build/), through the repository:
# dead once pushed. The checks of site.py and readme.py fail on one.
GENERATED_IN_REPO = re.compile(r"^(?:https://(?:github\.com/vodhash/one-page-papers/(?:raw|blob)/[^/]+|"
                               r"raw\.githubusercontent\.com/vodhash/one-page-papers/[^/]+)/|\.?/?)"
                               r"(?:dist|release|site|build)(?:/|$)")

class Paper(NamedTuple):
    category: str
    slug: str
    dir: pathlib.Path

def discover():
    """Every paper, sorted by category then slug. Raises ValueError on an unknown category
    or on a slug used twice, since slugs name the PDFs and the make targets."""
    papers, seen = [], {}
    for cat in sorted(p for p in (ROOT / "papers").iterdir() if p.is_dir()):
        if cat.name not in CATEGORIES:
            raise ValueError(f"papers/{cat.name}: unknown category (choose from {', '.join(CATEGORIES)})")
        for d in sorted(p for p in cat.iterdir() if (p / "meta.yaml").exists()):
            if d.name in CATEGORIES:
                raise ValueError(f"papers/{cat.name}/{d.name}: a slug cannot be the name of a category")
            if d.name in seen:
                raise ValueError(f"papers/{cat.name}/{d.name}: slug already used by papers/{seen[d.name]}/{d.name}")
            seen[d.name] = cat.name
            papers.append(Paper(cat.name, d.name, d))
    return papers

def pdf_name(slug, fmt, theme):
    """The file name of the PDF of a paper in a format and a theme, in dist/ or release/us/ and in the
    bucket of FILES_URL alike."""
    return f"{slug}-{fmt}-{theme}.pdf"

def pdf_url(paper, fmt, theme):
    """Where the PDF of a paper is served (PDF_URL), as the CI uploads it: git does not keep the PDFs."""
    return PDF_URL.format(category=paper.category, file=pdf_name(paper.slug, fmt, theme))

# ---------------------------------------------------------------- meta.yaml

META_KEYS = {"title", "title_html", "title_size", "kicker", "author", "byline", "emblem", "abstract",
             "abstract_label", "numbered", "columns", "header_scale", "font_range", "max_font", "layout",
             "footer", "lang", "license", "themes", "hero_height", "year", "authors", "min_print", "source",
             "summary", "contributors",
             "commercial", "commercial_basis"}
LICENSE_KEYS = {"text", "holder", "notice", "basis", "note"}
PRINT_SIZES = ("A3", "A2", "A1", "A0")  # the A file prints at each of them
MIN_BODY = 8  # pt: min_print is the smallest size at which the body prints at least this large
# centered: short texts, one column by default, vertically centered;
# hero: the first image of the text across the top of the page, the text in columns below
LAYOUTS = ("columns", "centered", "hero")

class BuildError(Exception):
    """A paper that cannot be built as it is: the message names the file and what is wrong."""

def rel(path):
    """A path for a message: relative to the repository, when it is in it."""
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path

def load_meta(paper_dir):
    """The meta.yaml of a paper, checked: BuildError names every key that breaks the rules."""
    path = paper_dir / "meta.yaml"
    try:
        m = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise BuildError(f"{rel(path)}: {' '.join(str(e).split())}") from None
    if not isinstance(m, dict):
        raise BuildError(f"{rel(path)}: expected a mapping of keys")
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

def themes_of(m):
    """The themes of a paper, in the order of THEMES: the first one makes its thumbnail."""
    return [t for t in THEMES if t in m.get("themes", THEMES)]
