#!/usr/bin/env python3
"""The catalog of README.md, written from the meta.yaml of every paper and from PENDING.md.

    python3 engine/readme.py            # rewrite the catalog between the markers of README.md
    python3 engine/readme.py --check    # fail when README.md is not up to date
"""
import argparse, pathlib, re, sys
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from papers import CATEGORIES, FILES_URL, GENERATED_IN_REPO, ROOT, SHOWCASE, SITE_URL, discover
from themes import FORMATS, THEMES

START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"

def year_key(year):
    """Sort key of a year given as 1858, -400 (400 BC) or a text such as "c. 400 BC"."""
    if isinstance(year, int):
        return year
    n = int(re.search(r"\d+", year).group())
    return -n if "BC" in year else n

def year_text(year):
    return f"{-year} BC" if isinstance(year, int) and year < 0 else str(year)

def cell(text):
    return str(text).replace("|", "\\|")

def pdf(paper, theme):
    """The A PDF of a theme, as the CI uploads it: git does not keep the PDFs."""
    return f"{FILES_URL}{paper.category}/{paper.slug}-A-{theme}.pdf"

def page(paper):
    """The page of a poster on the site, with every format and theme."""
    return f"{SITE_URL}{paper.slug}/"

def pending():
    """Titles waiting in PENDING.md, one "## " heading each."""
    path = ROOT / "PENDING.md"
    return re.findall(r"^## (.+)$", path.read_text(), re.M) if path.exists() else []

def catalog():
    papers = discover()
    metas = {p: yaml.safe_load((p.dir / "meta.yaml").read_text()) for p in papers}
    show = next((p for p in papers if p.slug == SHOWCASE), None)
    if not show:
        raise ValueError(f"the paper {SHOWCASE}, shown in every theme above the catalog, does not exist")
    out = [START, "",
           f"{len(papers)} posters in {len({p.category for p in papers})} categories. Each one comes in "
           f"{len(THEMES)} themes, shown here with *{metas[show]['title']}*, and in {len(FORMATS)} formats "
           "(see [Download](#download)).", "",
           "| " + " | ".join(THEMES) + " |", "|" + ":-:|" * len(THEMES),
           "| " + " | ".join(f'<a href="{pdf(show, t)}"><img src="docs/themes/{t}.png" width="160" '
                             f'alt="{t} theme"></a>' for t in THEMES) + " |", "",
           "A click on a poster opens its page on onepagepapers.com, with every format and theme, and the "
           "links under its summary open its PDF in the A format in each theme. *Print from* is the smallest "
           "A size at which its body text is at least 8 pt."]
    for cat, title in CATEGORIES.items():
        mine = sorted((p for p in papers if p.category == cat),
                      key=lambda p: (year_key(metas[p]["year"]), metas[p]["title"]))
        if not mine:
            continue
        # the no-break spaces keep the column as wide as the thumbnails: GitHub shrinks images
        # before text when a table is wider than the page, whatever their width attribute
        out += ["", f"### {title}", "", f"| {'&nbsp;' * 24} | Paper | Authors | Year | Print from | License |",
                "|---|---|---|---|---|---|"]
        for p in mine:
            m = metas[p]
            themes = [t for t in THEMES if t in m.get("themes", THEMES)]  # the first one makes the thumbnail
            thumb = f'<a href="{page(p)}"><img src="docs/{cat}/{p.slug}.png" width="90" alt=""></a>'
            year = year_text(m['year']).replace(' ', '&nbsp;')  # "c. 400 BC" on one line in its narrow column
            links = "&nbsp;·&nbsp;".join(f"[{t}]({pdf(p, t)})" for t in themes)  # on one line
            out.append(f"| {thumb} | [{cell(m['title'])}]({page(p)})<br>{cell(m['summary'])}<br>{links} | "
                       f"{cell(', '.join(m['authors']))} | {year} | {m['min_print']} | "
                       f"{cell(m['license']['text'])} |")
    if waiting := pending():
        out += ["", "## Coming soon", "",
                "Texts that wait for a license allowing their redistribution; [PENDING.md](PENDING.md) says what is missing.", ""]
        out += [f"- {cell(t)}" for t in waiting]
    return "\n".join(out + ["", END])

# the documents whose links go to files: none may lead to a file that git does not keep
DOCUMENTS = ("README.md", "CONTRIBUTING.md", "PENDING.md", "engine/README.md")

def generated_links():
    """The links of DOCUMENTS to a generated file that git does not keep, as messages."""
    out = []
    for name in DOCUMENTS:
        path = ROOT / name
        if not path.exists():
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for url in re.findall(r"\]\(([^)\s]+)\)|href=\"([^\"]+)\"|src=\"([^\"]+)\"", line):
                url = next(u for u in url if u)
                if GENERATED_IN_REPO.match(url):
                    out.append(f"{name}:{n}: {url}: a file that git does not keep, link to FILES_URL or to the site")
    return out

def main():
    ap = argparse.ArgumentParser(description="Write the catalog of README.md.")
    ap.add_argument("--check", action="store_true", help="only check that README.md is up to date")
    a = ap.parse_args()
    readme = ROOT / "README.md"
    text = readme.read_text()
    if text.count(START) != 1 or text.count(END) != 1:
        sys.exit(f"error: README.md needs one {START} and one {END}")
    try:
        new = text[:text.index(START)] + catalog() + text[text.index(END) + len(END):]
    except ValueError as e:
        sys.exit(f"error: {e}")
    if a.check:
        if new != text:
            sys.exit("error: the catalog of README.md is not up to date, run `make readme`")
        if dead := generated_links():
            sys.exit("error: " + "\nerror: ".join(dead))
    elif new != text:
        readme.write_text(new)
        print("README.md: catalog updated")

if __name__ == "__main__":
    main()
