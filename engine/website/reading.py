"""The reading edition of each poster (<slug>/read/), with its margin notes, and the teaching kits
(<slug>/teach/)."""
import html, pathlib, re
from typing import NamedTuple
from urllib.parse import urlsplit

import markdown
from build import BuildError, katex, load_figures, substitute
from papers import CATEGORIES, ROOT
from readme import year_text
from .common import (NAME, SiteError, WEB, alt, authors_short, date_text, download_event, esc, pdf_url, poster_facts,
                     short, title)
from .content import LICENSE_URLS
from .images import web_image
from .pages import Page, picture

class RawText(NamedTuple):
    """The text of a poster, rendered as build.py renders it, before KaTeX."""
    body: str
    math: list

def texts(posters):
    """{slug: html of the text}, with its math set by one run of KaTeX for the whole collection.
    The text goes through markdown.render with the figures and the folder of the paper, as in
    build.py, but without the hero: its image stays in the flow of the text."""
    raw = {}
    for p in posters:
        path = p.paper.dir / "text.md"
        try:
            body, math, _ = markdown.render(path.read_text(), load_figures(p.paper.dir), p.meta.get("numbered", False),
                                            assets=p.paper.dir)
        except markdown.MarkdownError as e:
            raise SiteError(f"{path.relative_to(ROOT)}:{e.line}: {e.msg}") from None
        raw[p.slug] = RawText(body, math)
    try:
        done = iter(katex([x for t in raw.values() for x in t.math]))
    except BuildError as e:
        raise SiteError(e) from None
    out = {}
    for slug, t in raw.items():
        body = t.body
        for i in range(len(t.math)):
            body = body.replace(f"<!--MATH:{i}-->", next(done), 1)
        out[slug] = body
    return out

def plain(fragment):
    """The text of an HTML fragment, for an attribute."""
    return html.escape(" ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split()))

IMAGE_FIGURE = re.compile(r'<figure class="image" data-dark="(\w+)"( data-light="\w+")? data-file="([^"]+)"( style="[^"]*")?>'
                          r'<img src="data:[^"]+"(?: width="\d+" height="\d+")? alt="">(<figcaption>.*?</figcaption>)?</figure>', re.S)
SVG_FIGURE = re.compile(r'<figure><svg\b.*?</svg></figure>', re.S)
HEADING = re.compile(r'<h([234])((?:\s[^>]*)?)>(.*?)</h\1>', re.S)

def figure_label(n, svg):
    """What a drawn figure says to a screen reader, which reads it as one image: its number and the
    words drawn in it, once each and in the order of the drawing."""
    words = []
    for t in re.findall(r"<text\b[^>]*>(.*?)</text>", svg, re.S):
        w = " ".join(html.unescape(re.sub(r"<[^>]+>", "", t)).split())
        if w and w not in words:
            words.append(w)
    return f"Figure {n}" + (f": {', '.join(words)}" if words else "")

def reading_body(p, body, files):
    """The text of a poster made for a web page: its images as files (added to files, {site
    path: path in the cache}) with their size and an alt taken from their caption, the ids of each
    SVG figure made its own, an anchor on every heading, and footnotes linked both ways."""
    folder = f"{p.slug}/read/"
    def image(k):
        src = p.paper.dir / html.unescape(k.group(3))
        cached, w, h = web_image(src)
        name = pathlib.PurePath(html.unescape(k.group(3))).with_suffix(cached.suffix).as_posix()
        files[folder + name] = cached
        cap = k.group(5) or ""
        text = plain(cap) or esc(f"Image from “{p.meta['title']}”")
        size = f' width="{w}" height="{h}"' if w else ""
        return (f'<figure class="image" data-dark="{k.group(1)}"{k.group(2) or ""}{k.group(4) or ""}>'
                f'<img src="{html.escape(name)}"{size} alt="{text}" loading="lazy" decoding="async">{cap}</figure>')
    body = IMAGE_FIGURE.sub(image, body)
    if "data:image/" in body:
        raise SiteError(f"papers/{p.category}/{p.slug}: an image of the text was left as a data URI")
    # the figures of svg.py all define the same markers: each figure gets ids of its own
    n = iter(range(1, 1000))
    def figure(k):
        i, svg = next(n), k.group(0)
        ids = re.findall(r'\bid="([^"]+)"', svg)
        for x in ids:
            svg = re.sub(rf'\bid="{re.escape(x)}"', f'id="fig{i}-{x}"', svg)
            svg = re.sub(rf'(url\(#|href="#){re.escape(x)}([)"])', rf'\g<1>fig{i}-{x}\2', svg)
        label = html.escape(figure_label(i, svg))
        return svg.replace("<svg ", f'<svg role="img" aria-label="{label}" ', 1).replace('<figure>', '<figure class="fig">', 1)
    body = SVG_FIGURE.sub(figure, body)
    # a Morse code drawn with empty elements (morse-phonetic-alphabet) is read out as its dots and dashes
    body = re.sub(r'(<span class="m" data-m="([.\-]+)")>', r'\1 role="img" aria-label="\2">', body)
    # numbered anchors: s1, s1-2, s1-2-3, from the place of each heading in the text
    nums = [0, 0, 0]
    def heading(k):
        level, attrs, inner = int(k.group(1)), k.group(2), k.group(3)
        nums[level - 2] += 1
        nums[level - 1:] = [0] * (4 - level)
        m = re.search(r'\bid="([^"]+)"', attrs)
        hid = m.group(1) if m else "s" + "-".join(str(x) for x in nums[:level - 1])
        if not m:
            attrs += f' id="{hid}"'
        return (f'<h{level}{attrs}>{inner}<a class="anchor" href="#{hid}" aria-label="Link to this section">#</a>'
                f'</h{level}>')
    body = HEADING.sub(heading, body)
    # footnotes: a call links to its note, the note back to its first call
    called = set()
    def call(k):
        num = k.group(1)
        back = "" if num in called else f' id="fnref-{num}"'
        called.add(num)
        return f'<sup class="fn"><a href="#fn-{num}"{back} aria-label="Note {num}">{num}</a></sup>'
    body = re.sub(r'<sup class="fn">(\d+)</sup>', call, body)
    def note(k):
        num = k.group(1)
        back = f' <a class="back" href="#fnref-{num}" aria-label="Back to the call of note {num}">↑</a>' if num in called else ""
        return f'<li id="fn-{num}"><span>{num}</span><div>{k.group(2)}{back}</div></li>'
    if '<div class="footnotes">' in body:
        head, notes = body.rsplit('<div class="footnotes">', 1)
        notes = re.sub(r'<li><span>(\d+)</span><div>(.*?)</div></li>', note, notes, flags=re.S)
        body = f'{head}<div class="footnotes">{notes}'
    return body

# the margin notes of a reading page: where their anchors are in the rendered text
NOTE_SKIP = {"svg", "math", "script", "style"}  # and the spans of KaTeX: their text is not the text's
NOTE_BLOCKS = {"p", "div", "li", "ol", "ul", "h2", "h3", "h4", "blockquote", "figure", "figcaption", "table", "tr",
               "td", "th", "dl", "dt", "dd", "pre", "br", "hr", "section", "caption"}
VOID = {"br", "hr", "img", "input", "wbr", "source", "meta", "link", "col", "area"}
QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', " ": " ", " ": " ", " ": " "})
TOKEN = re.compile(r"<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>|&(#?\w+);|[^<&]", re.S)

def text_positions(body):
    """The text of an HTML fragment as it reads, with straight quotes and single spaces, and for
    each of its characters the span of the source it comes from. Math and figures count as one
    character that no phrase matches, and a block boundary as another."""
    chars, spans, stack, skip = [], [], [], None
    def put(c, a, b):
        c = c.translate(QUOTES)
        if c.isspace():
            if chars and chars[-1] == " ":
                return
            c = " "
        chars.append(c)
        spans.append((a, b))
    for k in TOKEN.finditer(body):
        a, b = k.span()
        close, tag, attrs, selfclose, entity = k.groups()
        if tag:
            tag = tag.lower()
            if skip is not None:
                if close and len(stack) == skip and stack[-1] == tag:
                    stack.pop()
                    skip = None
                    put("\x00", a, a)
                elif close:
                    stack.pop() if stack else None
                elif not selfclose and tag not in VOID:
                    stack.append(tag)
                continue
            if tag in NOTE_BLOCKS:
                put("\x01", a, a)
            if close:
                if stack:
                    stack.pop()
            elif not selfclose and tag not in VOID:
                stack.append(tag)
                if tag in NOTE_SKIP or (tag == "span" and re.search(r'class="katex(?:-display)?"', attrs)):
                    skip = len(stack)
            continue
        if skip is not None:
            continue
        put(html.unescape(k.group()) if entity else k.group(), a, b)
    return "".join(chars), spans

def note_sources(keys, refs):
    parts = []
    for k in keys:
        r = refs[k]
        name = esc(r["title"])
        if r.get("url"):
            archived = " (archived copy)" if "web.archive.org/" in r["url"] else ""
            name = f'<a href="{html.escape(r["url"])}">{name}</a>{archived}'
        parts.append(name + (f', {esc(r["publisher"])}' if r.get("publisher") else ""))
    return f'<span class="sn-src"><span class="sn-label">Source{"s" * (len(keys) > 1)}:</span> {"; ".join(parts)}.</span>'

def annotate(p, text, data):
    """The text of a reading page with its margin notes: each anchor phrase in a <mark>, followed
    by the number of its note, a checkbox that opens the note in the text on small screens and
    without JavaScript, and the note itself, which site.js sets in the margin of a wide screen."""
    plain_text, spans = text_positions(text)
    refs, lang = data["references"], data.get("lang", "en")
    inserts = []  # (position in the source, order at that position: close, note, open, html)
    found = []
    for k, n in enumerate(data["notes"], 1):
        want = " ".join(n["anchor"].translate(QUOTES).split())
        count = plain_text.count(want)
        if count != 1:
            raise SiteError(f"{data['_where']}: note {k} (anchor “{short(n['anchor'])}”): found {count} times in the text "
                            "as the reading page renders it, where it must occur exactly once")
        found.append((plain_text.find(want), want, n))
    # the notes are numbered in the order of their phrases in the text, whatever their order in the file
    for i, (at, want, n) in enumerate(sorted(found, key=lambda f: f[0]), 1):
        pos = spans[at:at + len(want)]
        runs = [[pos[0][0], pos[0][1]]]
        for a, b in pos[1:]:
            if a == runs[-1][1]:
                runs[-1][1] = b
            else:
                runs.append([a, b])
        for j, (a, b) in enumerate(runs):
            ident = f' id="an-{i}"' if j == 0 else ""
            inserts.append((a, 2, f'<mark class="anno" data-note="{i}"{ident}>'))
            inserts.append((b, 0, "</mark>"))
        body = esc(" ".join(n["note"].split()))
        inserts.append((runs[-1][1], 1,
            f'<input type="checkbox" class="sn-toggle" id="sn-t{i}" aria-controls="sn-{i}">'
            f'<label class="sn-num" for="sn-t{i}"><span class="sr-only">Note </span>{i}</label>'
            f'<span class="sidenote" id="sn-{i}" lang="{lang}" data-note="{i}">'
            f'<span class="sn-n" aria-hidden="true">{i}</span>'
            f'<span class="sr-only">Note {i}, written for One Page Papers: </span>{body} '
            f'{note_sources(n["sources"], refs)}</span>'))
    for pos, _, frag in sorted(inserts, key=lambda x: (x[0], x[1]), reverse=True):
        text = text[:pos] + frag + text[pos:]
    return text

def written_by(data):
    """Who wrote a content file, for its credit line: nothing when it is the site itself."""
    who = [a for a in data.get("authors") or [] if a != NAME]
    return f" by {esc(', '.join(who))}" if who else ""

def license_html(lic):
    lic = lic.removesuffix(f", written for {NAME}")  # the credit line says it already
    for name, url in LICENSE_URLS.items():
        if lic.startswith(name):
            return f'<a href="{url}">{esc(name)}</a>{esc(lic[len(name):])}'
    return esc(lic)

def read_page(p, body, files, katex_head, extras=None):
    """The reading edition of a poster: its whole text as a web page, under /<slug>/read/, with its
    margin notes when the paper has an annotations.yaml."""
    m, root = p.meta, "../../"
    lic, src = m["license"], m["source"]
    lang = m.get("lang", "en")
    text = reading_body(p, body, files)
    notes = extras.annotations if extras else None
    intro = ""
    if notes:
        text = annotate(p, text, notes)
        k = len(notes["notes"])
        intro = (f'<aside class="anno-intro" aria-label="About the margin notes" lang="en">\n'
                 f'<p class="eyebrow">Annotated edition</p>\n'
                 f'<p><b>{k} notes written for {NAME}</b> explain the phrases <mark class="anno">marked like this</mark>: '
                 'the number after a phrase opens its note, which a wide screen shows in the margin. They are not part '
                 f'of the original text. Written for {NAME}{written_by(notes)}; license: {license_html(notes["license"])}. '
                 'Each note gives its sources.</p>\n'
                 '<p class="anno-switch" hidden><button type="button" class="pill" aria-pressed="true" '
                 'data-notes-toggle>Show the notes</button></p>\n</aside>\n')
    teach = extras.teaching if extras else None
    # what the license asks to carry with the text, in sight: its notice, and the footer of the
    # poster (attribution, license URI); why a text is free, and the notes, are in the details
    notices = []
    if lic.get("notice"):
        notices.append(f'<blockquote class="notice"><p>{esc(lic["notice"])}</p></blockquote>')
    footer = [c for c in (m.get("footer") or []) if c]
    if footer:
        notices.append('<ul class="read-footer" aria-label="The footer of the poster">'
                       + "".join(f"<li>{c}</li>" for c in footer) + "</ul>")
    rights = [f'<p>{esc(lic["basis"])}</p>'] if lic.get("basis") else []
    if lic.get("notice"):
        rights.append(f'<p>License notice: “{esc(lic["notice"])}”</p>')
    if lic.get("note"):
        rights.append(f'<p>{esc(lic["note"])}</p>')
    kicker = f'<p class="subtitle" lang="{lang}">{m["kicker"]}</p>\n' if m.get("kicker") else ""
    byline = f'<p class="byline">{m["byline"]}</p>\n' if m.get("byline") else ""
    abstract = ""
    if m.get("abstract"):
        label = m.get("abstract_label", "Abstract.")
        abstract = f'<p class="abstract"><b>{label}</b> {markdown.inline(m["abstract"])}</p>\n'
    main = substitute((WEB / "read.html").read_text(), {
        "CATEGORY": p.category, "CATEGORY_TITLE": esc(CATEGORIES[p.category]), "TITLE": esc(m["title"]),
        "TITLE_H1": title(m["title"]), "LANG": lang, "YEAR": esc(year_text(m["year"])),
        "AUTHORS": esc(", ".join(m["authors"])), "KICKER": kicker, "BYLINE": byline,
        "FACTS": poster_facts(m, ("Source", "Retrieved", "License", "Rights holder", "Proposed by", "Language")),
        "EDITION": esc(src["edition"]), "RIGHTS": "\n".join(rights),
        "NOTICES": "".join(x + "\n" for x in notices),
        "ABSTRACT": abstract, "TEXT": text, "ROOT": root, "SLUG": p.slug, "NOTES_INTRO": intro,
        "READ_CLASS": " annotated" if notes else "",
        "TEACH": ' <a class="btn btn-line" href="../teach/">Teaching kit <span class="size">questions, glossary</span></a>'
                 if teach else ""})
    return Page(f"{p.slug}/read/index.html", f"{esc(m['title'])}, the text · {NAME}",
                esc(f"The full text of “{m['title']}” ({authors_short(m)}, {year_text(m['year'])}), "
                    "as set on its poster, to read on screen."),
                main, f"previews/{p.slug}-share.jpg", "", esc(alt(p)), katex_head if "katex" in text else "")

KIND_NAMES = {"locate": "Find", "understand": "Understand", "analyse": "Analyse", "calculate": "Calculate",
              "reflect": "Discuss"}

def minutes(n):
    return f"{n} minutes"

def cites(keys, numbers):
    """The sources of an item as the numbers of the references, linked to them."""
    if not keys:
        return ""
    links = ", ".join(f'<a href="#ref-{numbers[k]}">{numbers[k]}</a>' for k in keys)
    return f' <span class="cite"><span class="sr-only">Sources: </span>[{links}]</span>'

def reference_item(n, r):
    title_ = esc(r["title"])
    if r.get("url"):
        title_ = f'<a href="{html.escape(r["url"])}">{title_}</a>'
    parts = [title_] + [esc(r[k]) for k in ("author", "publisher") if r.get(k)]
    line = ", ".join(parts) + "."
    if r.get("url") and "web.archive.org/" in r["url"]:
        orig = r.get("original_url")
        line += " Archived copy" + (f' of <span class="url">{esc(urlsplit(orig).netloc + urlsplit(orig).path)}</span>'
                                    if orig else "") + "."
    if r.get("retrieved"):
        line += f" Retrieved {date_text(r['retrieved'])}."
    if r.get("note"):
        line += f' <span class="ref-note">{esc(" ".join(r["note"].split()))}</span>'
    return f'<li id="ref-{n}"><span class="ref-n">{n}</span><p>{line}</p></li>'

def teach_page(p, previews, data):
    """The teaching kit of a poster, under /<slug>/teach/: laid out for the screen, and printable
    on A4 with or without the answers, which start on a page of their own."""
    m, root = p.meta, "../../"
    refs = data["references"]
    numbers = {k: i for i, k in enumerate(refs, 1)}
    facts = [("Level", esc(data["level"])), ("Subject", esc(data["subject"])),
             ("Duration", minutes(data["duration"])), ("Print from", m["min_print"])]
    prereq = (f'<p class="teach-pre"><b>Prerequisites.</b> {esc(" ".join(data["prerequisites"].split()))}</p>\n'
              if data.get("prerequisites") else "")
    context = "\n".join(f'<li><p>{esc(" ".join(c["point"].split()))}{cites(c.get("sources"), numbers)}</p></li>'
                        for c in data["context"])
    glossary = "\n".join(f'<div><dt>{esc(g["term"])}</dt><dd>{esc(" ".join(g["definition"].split()))}</dd></div>'
                         for g in data["glossary"])
    def kind(q):
        return f'<span class="q-kind">{KIND_NAMES[q["kind"]]}</span> ' if q.get("kind") else ""
    questions = "\n".join(f'<li id="q-{i}"><span class="q-n">{i}</span><p>{kind(q)}{esc(" ".join(q["question"].split()))}</p></li>'
                          for i, q in enumerate(data["questions"], 1))
    answers = "\n".join(
        f'<li id="a-{i}"><span class="q-n">{i}</span><div><p class="a-q">{esc(" ".join(q["question"].split()))}</p>'
        f'<p>{esc(" ".join(q["answer"].split()))}{cites(q.get("sources"), numbers)}</p></div></li>'
        for i, q in enumerate(data["questions"], 1))
    act = data.get("activity")
    activity = ""
    if act:
        dur = f' <span class="act-dur">{minutes(act["duration"])}</span>' if act.get("duration") else ""
        activity = (f'<section class="teach-sec teach-act" aria-labelledby="t-activity">\n'
                    f'<h2 id="t-activity">Activity</h2>\n<h3>{esc(act["title"])}{dur}</h3>\n'
                    f'<p>{esc(" ".join(act["instructions"].split()))}{cites(act.get("sources"), numbers)}</p>\n</section>\n')
    wall = ("Since it prints from A3, its body text is at least 8 pt there, readable from up close."
            if m["min_print"] == "A3" else
            f"At A3 its body text is under 8 pt, to be read from very close; it prints for reading from "
            f"{m['min_print']}.")
    a_pdf = pdf_url(p.paper, "A", p.light)
    main = substitute((WEB / "teach.html").read_text(), {
        "SLUG": p.slug, "CATEGORY": p.category, "CATEGORY_TITLE": esc(CATEGORIES[p.category]), "TITLE": esc(m["title"]),
        "TITLE_H1": title(m["title"]), "LANG": m.get("lang", "en"), "YEAR": esc(year_text(m["year"])),
        "AUTHORS": esc(", ".join(m["authors"])), "SUBJECT": esc(data["subject"]),
        "FACTS": "\n".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts), "PREREQ": prereq,
        "WALL": (f'For the classroom wall, the <a href="{a_pdf}" type="application/pdf" '
                 f'{download_event(p.slug, "A", p.light)}>A PDF of the poster</a> '
                 f'prints at A3 (29.7 × 42 cm). {wall} '
                 f'<a href="{root}print/?poster={p.slug}">How to have it printed</a>.'),
        "BY": f'Written for {NAME}{written_by(data)}; license: {license_html(data["license"])}. '
              'Numbers in brackets refer to the references at the end.',
        "CONTEXT": context, "GLOSSARY": glossary, "QUESTIONS": questions, "ACTIVITY": activity,
        "ANSWERS": answers, "REFS": "\n".join(reference_item(numbers[k], r) for k, r in refs.items()),
        "PICTURE": picture(previews, p, root, "(min-width: 1200px) 300px, (min-width: 900px) 26vw, 60vw"),
        "COUNT": f"{len(data['questions'])} questions"})
    return Page(f"{p.slug}/teach/index.html", f"{esc(m['title'])}, teaching kit · {NAME}",
                esc(f"A teaching kit for “{m['title']}” ({authors_short(m)}, {year_text(m['year'])}): context, "
                    f"glossary, {len(data['questions'])} questions with answers for the teacher, and an activity, "
                    "printable on A4."),
                main, f"previews/{p.slug}-share.jpg", "", esc(alt(p)))
