#!/usr/bin/env python3
"""The catalog of README.md, written from the meta.yaml of every paper and from PENDING.md.

    python3 engine/readme.py            # rewrite the catalog between the markers of README.md
    python3 engine/readme.py --check    # fail when README.md is not up to date
"""
import argparse, pathlib, re, sys
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from papers import CATEGORIES, ROOT, discover
from themes import THEMES

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

def pending():
    """Titles waiting in PENDING.md, one "## " heading each."""
    path = ROOT / "PENDING.md"
    return re.findall(r"^## (.+)$", path.read_text(), re.M) if path.exists() else []

def catalog():
    papers = discover()
    metas = {p: yaml.safe_load((p.dir / "meta.yaml").read_text()) for p in papers}
    out = [START, "",
           f"{len(papers)} posters in {len({p.category for p in papers})} categories. A click on a poster "
           "opens its PDF in the A format; *Print from* is the smallest A size at which its body text is "
           "at least 8 pt."]
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
            theme = next(t for t in THEMES if t in m.get("themes", THEMES))  # the theme of the thumbnail
            pdf = f"dist/{cat}/{p.slug}-A-{theme}.pdf"
            thumb = f'<a href="{pdf}"><img src="docs/{cat}/{p.slug}.png" width="90" alt=""></a>'
            out.append(f"| {thumb} | [{cell(m['title'])}]({pdf})<br>{cell(m['summary'])} | {cell(', '.join(m['authors']))} | "
                       f"{year_text(m['year'])} | {m['min_print']} | {cell(m['license']['text'])} |")
    if waiting := pending():
        out += ["", "## Coming soon", "",
                "Texts that wait for a license allowing their redistribution; [PENDING.md](PENDING.md) says what is missing.", ""]
        out += [f"- {cell(t)}" for t in waiting]
    return "\n".join(out + ["", END])

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
    elif new != text:
        readme.write_text(new)
        print("README.md: catalog updated")

if __name__ == "__main__":
    main()
