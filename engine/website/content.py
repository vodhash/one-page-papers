"""What the site is written from, read and checked: the posters (meta.yaml, and their PDFs in dist/
and release/us/), the series of series.yaml, the links of see-also.yaml, and the margin notes
and teaching kits of a paper (annotations.yaml, teaching.yaml)."""
import functools, re
from typing import NamedTuple

import yaml

from build import BuildError, load_meta, themes_of
from papers import CATEGORIES, ROOT, SHOWCASE, discover
from readme import year_key
from themes import FORMATS, US_FORMATS
from .common import LANGUAGES, Poster, SiteError, esc, pdf_file, short

SERIES_FILE = ROOT / "series.yaml"
SERIES_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*$")
MIN_SERIES = 3  # posters in a series, at least

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

SEE_ALSO_FILE = ROOT / "see-also.yaml"
SEE_ALSO_KEYS = {"papers", "text", "link", "url"}

@functools.cache
def load_see_also():
    """The links of see-also.yaml, as {paper slug: [paragraph]}: a site that belongs with some posters, linked from
    their pages (plain links, without tracking). An unknown paper, a text without {link} or a URL that is not https
    is an error; without the file, no link."""
    where = SEE_ALSO_FILE.name
    if not SEE_ALSO_FILE.exists():
        return {}
    try:
        data = yaml.safe_load(SEE_ALSO_FILE.read_text()) or []
    except yaml.YAMLError as e:
        raise SiteError(f"{where}: {' '.join(str(e).split())}") from None
    if not isinstance(data, list):
        raise SiteError(f"{where}: expected a list of links, each with papers, text, link and url")
    known = {p.slug for p in discover()}
    errors, links = [], {}
    for i, s in enumerate(data, 1):
        at = f"{where}: link {i}"
        if not isinstance(s, dict) or set(s) != SEE_ALSO_KEYS:
            errors.append(f"{at}: expected exactly {', '.join(sorted(SEE_ALSO_KEYS))}")
            continue
        if not (isinstance(s["text"], str) and s["text"].count("{link}") == 1):
            errors.append(f"{at}: text must be one sentence with {{link}} once")
            continue
        if not (isinstance(s["url"], str) and re.match(r"https://\S+$", s["url"])):
            errors.append(f"{at}: url must be an https URL")
            continue
        if not (isinstance(s["link"], str) and s["link"].strip()):
            errors.append(f"{at}: link must be a text")
            continue
        papers = s["papers"] if isinstance(s["papers"], list) else []
        unknown = [x for x in papers if x not in known]
        if not papers or unknown:
            errors.append(f"{at}: papers must list known paper slugs" + (f" (unknown: {', '.join(map(str, unknown))})"
                                                                          if unknown else ""))
            continue
        before, after = (esc(part) for part in s["text"].split("{link}"))
        paragraph = f'<p class="see-also">{before}<a href="{esc(s["url"])}">{esc(s["link"])}</a>{after}</p>\n'
        for x in papers:
            links.setdefault(x, []).append(paragraph)
    if errors:
        raise SiteError("\nerror: ".join(errors))
    return links

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
